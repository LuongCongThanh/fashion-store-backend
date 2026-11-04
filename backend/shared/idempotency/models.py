"""Model của `Idempotency-Key` (03 mục 1.5)."""

from django.db import models

from shared.models import BaseModel, uuid7


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
