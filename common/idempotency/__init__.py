"""Lõi chống tạo trùng bằng `Idempotency-Key` (03 mục 1.5), không phụ thuộc HTTP.

`claim(scope, key, request_hash)` giành key bằng transaction ngắn hoặc trả kết quả của lần gửi
trước. Service nhận `Claim` gọi `claim.complete(...)` bên trong `transaction.atomic` của tác
động nghiệp vụ, để kết quả idempotency commit cùng tác động. Lớp HTTP (đọc header, dựng scope,
tính hash, dựng `Response`) ở `common.idempotency.http`;
model ở `models.py`, job purge ở `tasks.py`.
"""

import uuid
from dataclasses import dataclass
from datetime import timedelta
from types import TracebackType
from typing import Any, Self, cast

import structlog
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.exceptions import DomainError
from common.idempotency.models import IdempotencyKey, IdempotencyStatus
from common.models import uuid7

# Thời gian một worker giữ key đang xử lý trước khi worker khác được giành lại
LEASE = timedelta(seconds=60)
RETRY_AFTER_SECONDS = 3
# Key `completed` giữ để replay trong khoảng này rồi job purge xoá (07 mục 3.2)
RETENTION = timedelta(hours=24)
PURGE_BATCH = 1000

logger = structlog.get_logger(__name__)


class IdempotencyConflict(DomainError):
    code = "IDEMPOTENCY_CONFLICT"
    http_status = 409
    message = _("Idempotency-Key đã được dùng cho một yêu cầu có nội dung khác.")


class LeaseLost(Exception):
    """Lease của `Claim` đã bị worker khác giành lại; tác động nghiệp vụ phải rollback."""


@dataclass(frozen=True)
class Replay:
    """Key đã `completed`: trả nguyên status và body đã lưu."""

    status: int
    body: Any


@dataclass(frozen=True)
class Pending:
    """Lần gửi trước với cùng key còn đang xử lý; gửi lại sau `retry_after` giây."""

    retry_after: int = RETRY_AFTER_SECONDS


@dataclass(frozen=True)
class Claim:
    """Request này giữ key; tác động nghiệp vụ chạy đúng một lần dưới `operation_id`.

    Dùng làm context manager bọc ngoài `transaction.atomic` của tác động: exception thoát ra
    thì nhả key để gửi lại cùng key chạy lại từ đầu.
    """

    key_id: uuid.UUID
    operation_id: uuid.UUID
    lease_token: uuid.UUID

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is None:
            return
        # Chỉ xoá khi lease còn của mình; có `resource_id` thì giữ dòng cho luồng khôi phục
        with transaction.atomic():
            IdempotencyKey.objects.filter(
                pk=self.key_id, lease_token=self.lease_token, resource_id__isnull=True
            ).delete()

    def complete(self, status: int, body: Any, resource_id: uuid.UUID | None = None) -> None:
        """Lưu kết quả để replay; gọi bên trong `transaction.atomic` của tác động nghiệp vụ.

        Không truyền `resource_id` thì giữ giá trị đã gắn trước đó.

        Raises:
            LeaseLost: Worker khác đã giành lại key, hoặc dòng key không còn.
        """
        fields: dict[str, Any] = {
            "status": IdempotencyStatus.COMPLETED,
            "completed_at": timezone.now(),
            "response_status": status,
            "response_body": body,
            "lease_token": None,
            "lease_expires_at": None,
        }
        if resource_id is not None:
            fields["resource_id"] = resource_id
        # `BaseQuerySet.update` tự ghi `updated_at`
        updated = IdempotencyKey.objects.filter(
            pk=self.key_id, lease_token=self.lease_token
        ).update(**fields)
        if not updated:
            raise LeaseLost


def claim(scope: str, key: uuid.UUID, request_hash: str) -> Claim | Replay | Pending:
    """Giành key bằng transaction ngắn, hoặc trả kết quả của lần gửi trước.

    Raises:
        IdempotencyConflict: Cùng key nhưng `request_hash` khác lần gửi trước.
        RuntimeError: Gọi bên trong một `transaction.atomic` khác.
    """
    lease_token = uuid7()
    now = timezone.now()

    # Transaction ngắn: trả về hoặc raise ở đây đều nhả khoá dòng ngay. `durable` từ chối
    # transaction ngoài (nó giữ khoá dòng tới khi commit và nuốt việc nhả key), nhưng bỏ qua
    # transaction bọc test của `django.test.TestCase`
    with transaction.atomic(durable=True):
        row, created = IdempotencyKey.objects.select_for_update().get_or_create(
            scope=scope,
            key=key,
            defaults={
                "request_hash": request_hash,
                "lease_token": lease_token,
                "lease_expires_at": now + LEASE,
            },
        )
        if created:
            return Claim(key_id=row.pk, operation_id=row.operation_id, lease_token=lease_token)
        if row.request_hash != request_hash:
            raise IdempotencyConflict
        if row.status == IdempotencyStatus.COMPLETED:
            # CHECK `completed_has_response` bảo đảm `response_status` có giá trị
            return Replay(status=cast(int, row.response_status), body=row.response_body)
        if row.lease_expires_at and row.lease_expires_at > now:
            return Pending()
        # Lease đã hết: giành lại key, giữ `operation_id`; worker cũ sẽ hỏng ở `complete`
        row.lease_token = lease_token
        row.lease_expires_at = now + LEASE
        row.save(update_fields=["lease_token", "lease_expires_at", "updated_at"])
        return Claim(key_id=row.pk, operation_id=row.operation_id, lease_token=lease_token)


def purge_idempotency_keys() -> int:
    """Xoá key `completed` quá `RETENTION`; key `in_progress` chưa rõ kết quả nên luôn giữ.

    Mỗi lô `PURGE_BATCH` key một transaction, lặp tới khi hết. Trả số key đã xoá.
    """
    cutoff = timezone.now() - RETENTION
    purgeable = IdempotencyKey.objects.filter(
        status=IdempotencyStatus.COMPLETED, completed_at__lt=cutoff
    )
    purged = 0
    while True:
        with transaction.atomic():
            ids = list(
                purgeable.select_for_update()
                .order_by("id")
                .values_list("id", flat=True)[:PURGE_BATCH]
            )
            if not ids:
                break
            deleted, _ = IdempotencyKey.objects.filter(id__in=ids).delete()
        purged += deleted
    logger.info("idempotency_keys_purged", count=purged)
    return purged
