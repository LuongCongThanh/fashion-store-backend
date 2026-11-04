"""Persistence cho vòng đời refresh token (03 mục 2.4-2.5)."""

import uuid
from datetime import datetime
from typing import ClassVar, Self

from django.conf import settings
from django.db import models

from common.models import BaseModel, BaseQuerySet


class RefreshTokenQuerySet(BaseQuerySet["RefreshToken"]):
    def unrevoked(self) -> Self:
        return self.filter(revoked_at__isnull=True)


# Gán tên ở cấp module để plugin django-stubs suy được kiểu của manager sinh động
RefreshTokenManager = models.Manager.from_queryset(RefreshTokenQuerySet)


class RefreshToken(BaseModel):
    jti = models.UUIDField(unique=True)
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="refresh_tokens"
    )
    family_id = models.UUIDField()
    token_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    successor = models.OneToOneField(
        "self",
        to_field="jti",
        db_column="successor_jti",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="predecessor",
    )
    revoked_at = models.DateTimeField(null=True, blank=True)

    # Cùng gốc BaseQuerySet với manager của BaseModel; stub coi hai lớp manager sinh từ
    # from_queryset là khác kiểu
    objects: ClassVar[RefreshTokenManager] = RefreshTokenManager()  # type: ignore[assignment]

    class Meta:
        db_table = "identity_refresh_token"
        constraints = (
            models.CheckConstraint(
                condition=models.Q(successor__isnull=True) | models.Q(used_at__isnull=False),
                name="identity_refresh_successor_requires_used",
            ),
        )
        indexes = (
            models.Index(fields=["account"], name="identity_refresh_account_idx"),
            models.Index(fields=["family_id"], name="identity_refresh_family_idx"),
        )

    @classmethod
    def revoke_family(cls, family_id: uuid.UUID, *, now: datetime) -> int:
        """Thu hồi mọi token chưa thu hồi của family; bên gọi đã khoá Account (05 mục 2.1).

        Token đã thu hồi giữ `revoked_at` cũ để còn dấu vết lần thu hồi đầu.
        """
        return cls.objects.filter(family_id=family_id).unrevoked().update(revoked_at=now)

    def mark_used(self, *, successor: RefreshToken, now: datetime) -> None:
        """Đánh dấu đã đổi lấy `successor`; UNIQUE(successor_jti) chặn successor thứ hai."""
        self.used_at = now
        self.successor = successor
        self.save(update_fields=["used_at", "successor", "updated_at"])


class RefreshReplayQuerySet(BaseQuerySet["RefreshReplay"]):
    def expired(self, now: datetime) -> Self:
        return self.filter(expires_at__lte=now)


RefreshReplayManager = models.Manager.from_queryset(RefreshReplayQuerySet)


class RefreshReplay(BaseModel):
    parent = models.OneToOneField(
        RefreshToken,
        to_field="jti",
        db_column="parent_jti",
        on_delete=models.CASCADE,
        related_name="replay",
    )
    encryption_key_id = models.CharField(max_length=32)
    nonce = models.BinaryField()
    response_ciphertext = models.BinaryField()
    expires_at = models.DateTimeField()

    objects: ClassVar[RefreshReplayManager] = RefreshReplayManager()  # type: ignore[assignment]

    class Meta:
        db_table = "identity_refresh_replay"
