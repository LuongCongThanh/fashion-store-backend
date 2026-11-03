"""Model cơ sở cho các bảng do dự án định nghĩa (03 mục 0.1, ADR 0008)."""

import uuid
from typing import Any

from django.db import models
from django.utils import timezone


def uuid7() -> uuid.UUID:
    # Migration ghi đường dẫn hàm này, không ghi `uuid.uuid7`: đổi cách sinh UUID chỉ cần sửa
    # thân hàm (ADR 0008)
    return uuid.uuid7()


class BaseQuerySet[M: models.Model](models.QuerySet[M]):
    """Giữ `updated_at` đúng cho các đường ghi bulk, nơi `auto_now` không chạy."""

    def update(self, **kwargs: Any) -> int:
        kwargs.setdefault("updated_at", timezone.now())
        return super().update(**kwargs)

    def bulk_update(self, objs: Any, fields: Any, batch_size: int | None = None) -> int:
        # `fields` có thể là generator: đổi sang list trước khi kiểm tra để không dùng hết nó.
        # Bên gọi có `updated_at` trong `fields` thì giữ giá trị riêng của từng object
        objs, fields = list(objs), list(fields)
        if "updated_at" not in fields:
            now = timezone.now()
            for obj in objs:
                obj.updated_at = now
            fields.append("updated_at")
        return super().bulk_update(objs, fields, batch_size=batch_size)


class UUIDv7Model(models.Model):
    """Khoá chính UUID v7 (ADR 0008), dùng chung cho mọi bảng do dự án định nghĩa."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    class Meta:
        abstract = True


class BaseModel(UUIDv7Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BaseQuerySet.as_manager()

    class Meta:
        abstract = True


class IdempotencyStatus(models.TextChoices):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class IdempotencyKey(BaseModel):
    """Khoá chống tạo trùng của header `Idempotency-Key` (03 mục 1.5, 04 mục 1)."""

    scope = models.CharField(max_length=255)
    key = models.UUIDField()
    operation_id = models.UUIDField(unique=True, default=uuid7, editable=False)
    request_hash = models.CharField(max_length=64)
    status = models.CharField(
        max_length=32, choices=IdempotencyStatus.choices, default=IdempotencyStatus.IN_PROGRESS
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    # Không FK: trỏ tới Payment hoặc Order và bị purge
    resource_id = models.UUIDField(null=True, blank=True)
    lease_token = models.UUIDField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    response_status = models.SmallIntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "shared_idempotency_key"
        constraints = (
            models.UniqueConstraint(
                fields=["scope", "key"], name="shared_idempotency_key_scope_key_uniq"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=IdempotencyStatus.values),
                name="shared_idempotency_key_status_valid",
            ),
            # (status = 'completed') = (completed_at IS NOT NULL)
            models.CheckConstraint(
                condition=(
                    models.Q(status=IdempotencyStatus.COMPLETED, completed_at__isnull=False)
                    | (
                        ~models.Q(status=IdempotencyStatus.COMPLETED)
                        & models.Q(completed_at__isnull=True)
                    )
                ),
                name="shared_idempotency_key_completed_at_matches_status",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(status=IdempotencyStatus.COMPLETED)
                    | models.Q(response_status__isnull=False)
                ),
                name="shared_idempotency_key_completed_has_response",
            ),
        )
        indexes = (
            models.Index(
                fields=["completed_at"],
                condition=models.Q(status=IdempotencyStatus.COMPLETED),
                name="idempotency_key_completed_idx",
            ),
        )

    def __str__(self) -> str:
        return f"{self.scope} {self.key} {self.status}"


# Django chỉ nhận model qua `<app>/models.py` (02 mục 4). Import ở cuối file vì
# `shared.events.models` cần `uuid7` ở trên
from shared.events.models import EventDelivery, OutboxEvent  # noqa: E402, F401
from shared.geo.models import Province, Ward  # noqa: E402, F401
