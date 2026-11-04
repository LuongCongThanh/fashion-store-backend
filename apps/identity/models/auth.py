"""Persistence cho vòng đời refresh token (03 mục 2.4-2.5)."""

from django.conf import settings
from django.db import models

from common.models import BaseModel


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

    class Meta:
        db_table = "identity_refresh_replay"
