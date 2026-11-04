"""Outbox sự kiện và delivery từng handler (03 mục 1.3, 1.4; ADR 0007).

Không kế thừa `BaseModel`: 03 không có `created_at`/`updated_at` cho hai bảng này. Khoá chính
vẫn là UUID v7 qua `UUIDv7Model` (ADR 0008).
"""

import enum
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Self
from uuid import UUID

from django.db import models
from django.db.models import Q

from common.events.registry import HANDLER_NAME_MAX_LENGTH, Handler
from common.models import UUIDv7Model

# Chờ trước mỗi lần thử lại sau lần đầu; hết lịch thì delivery `failed` (07 mục 1.3)
RETRY_DELAYS: tuple[timedelta, ...] = (
    timedelta(seconds=10),
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(minutes=30),
)

# Số lần chạy dở liên tiếp tối đa; lần giao kế tiếp chuyển delivery `failed` (07 mục 1.3)
MAX_INTERRUPTED_RUNS = 3
# `last_error` khi chuyển `failed` vì chạy dở, cùng dạng tên class của `describe_error`
INTERRUPTED_ERROR = "HandlerInterrupted"

_LAST_ERROR_MAX_LENGTH = 500


def describe_error(exc: BaseException) -> str:
    """Tên class và `code` nếu có, không kèm message để không lọt PII (03 mục 1.4)."""
    code = getattr(exc, "code", None)
    text = type(exc).__name__ if code is None else f"{type(exc).__name__}({code})"
    return text[:_LAST_ERROR_MAX_LENGTH]


class OutboxEventQuerySet(models.QuerySet["OutboxEvent"]):
    """Vị từ đặt cạnh `Meta.indexes` để thấy query nào khớp partial index nào."""

    def unlisted(self) -> Self:
        """Sự kiện relay chưa lập danh sách delivery; khớp `outbox_event_undelivered_idx`."""
        return self.filter(deliveries_created_at__isnull=True)

    def listed(self) -> Self:
        return self.filter(deliveries_created_at__isnull=False)


class OutboxEvent(UUIDv7Model):
    # `id` (UUIDv7Model) chính là `event_id` trong `DomainEvent`
    event_type = models.CharField(max_length=100)
    schema_version = models.SmallIntegerField()
    payload = models.JSONField()
    occurred_at = models.DateTimeField()
    # NULL = relay chưa lập danh sách delivery; không có nghĩa handler đã chạy (07 mục 1.1.1)
    deliveries_created_at = models.DateTimeField(null=True, blank=True)

    objects = OutboxEventQuerySet.as_manager()

    class Meta:
        db_table = "common_outbox_event"
        constraints = (
            models.CheckConstraint(
                condition=Q(schema_version__gte=1),
                name="common_outbox_event_schema_version_gte_1",
            ),
        )
        indexes = (
            models.Index(
                fields=["occurred_at"],
                condition=Q(deliveries_created_at__isnull=True),
                name="outbox_event_undelivered_idx",
            ),
        )

    def __str__(self) -> str:
        return f"{self.event_type} v{self.schema_version} {self.id}"


class DeliveryStatus(models.TextChoices):
    PENDING = "pending"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


# Delivery đã kết thúc và có `completed_at`
_FINISHED = [DeliveryStatus.COMPLETED, DeliveryStatus.REJECTED]


class RunStart(enum.Enum):
    """Kết quả `EventDelivery.start_run`."""

    STARTED = enum.auto()
    FAILED_INTERRUPTED = enum.auto()


class RetryOutcome(enum.Enum):
    """Kết quả `EventDelivery.retry_or_fail`."""

    SCHEDULED = enum.auto()
    FAILED = enum.auto()


class EventDeliveryQuerySet(models.QuerySet["EventDelivery"]):
    """Vị từ đặt cạnh `Meta.indexes` để thấy query nào khớp partial index nào."""

    def attempt_due(self, now: datetime) -> Self:
        """`pending` đã tới lượt retry, chưa xét hạn giao lại (`delivery_lag`, 07 mục 1.1.1)."""
        return self.filter(status=DeliveryStatus.PENDING, next_attempt_at__lte=now)

    def dispatch_due(self, now: datetime) -> Self:
        """Tới lượt retry và hết hạn giao lại; khớp `event_delivery_pending_idx`."""
        return self.attempt_due(now).filter(next_dispatch_at__lte=now)

    def unfinished(self) -> Self:
        """`pending` hoặc `failed`: còn việc phải làm, nên purge giữ sự kiện lại."""
        return self.exclude(status__in=_FINISHED)


class EventDelivery(UUIDv7Model):
    """Công việc của một handler với một sự kiện, đồng thời là dấu đã xử lý."""

    # UNIQUE(event_id, handler) đã có index bắt đầu bằng event_id, không cần index riêng của FK
    event = models.ForeignKey(
        OutboxEvent,
        on_delete=models.CASCADE,
        related_name="deliveries",
        db_column="event_id",
        db_index=False,
    )
    handler = models.CharField(max_length=HANDLER_NAME_MAX_LENGTH)
    status = models.CharField(
        max_length=32, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING
    )
    attempts = models.IntegerField(default=0)
    # Số lần liên tiếp handler đã bắt đầu chạy mà consumer không lưu được kết quả (07 mục 1.3).
    # Mặc định ở mức DB để relay bản cũ (chưa biết cột) vẫn INSERT được khi rolling deploy
    interrupted_runs = models.IntegerField(db_default=0)
    next_attempt_at = models.DateTimeField()
    next_dispatch_at = models.DateTimeField()
    last_dispatched_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(default="", blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    retried_at = models.DateTimeField(null=True, blank=True)

    objects = EventDeliveryQuerySet.as_manager()

    class Meta:
        db_table = "common_event_delivery"
        constraints = (
            models.UniqueConstraint(
                fields=["event", "handler"], name="common_event_delivery_event_handler_uniq"
            ),
            models.CheckConstraint(
                condition=Q(status__in=DeliveryStatus.values),
                name="common_event_delivery_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(attempts__gte=0), name="common_event_delivery_attempts_gte_0"
            ),
            models.CheckConstraint(
                condition=Q(interrupted_runs__gte=0),
                name="common_event_delivery_interrupted_runs_gte_0",
            ),
            # (status IN ('completed', 'rejected')) = (completed_at IS NOT NULL)
            models.CheckConstraint(
                condition=(
                    Q(status__in=_FINISHED, completed_at__isnull=False)
                    | (~Q(status__in=_FINISHED) & Q(completed_at__isnull=True))
                ),
                name="common_event_delivery_completed_at_matches_status",
            ),
            models.CheckConstraint(
                condition=~Q(status=DeliveryStatus.FAILED) | Q(failed_at__isnull=False),
                name="common_event_delivery_failed_has_failed_at",
            ),
        )
        indexes = (
            models.Index(
                fields=["next_dispatch_at", "next_attempt_at"],
                condition=Q(status=DeliveryStatus.PENDING),
                name="event_delivery_pending_idx",
            ),
            models.Index(
                fields=["failed_at"],
                condition=Q(status=DeliveryStatus.FAILED),
                name="event_delivery_failed_idx",
            ),
        )

    def __str__(self) -> str:
        return f"{self.handler} {self.status} {self.event_id}"

    # Mỗi method tự lưu đúng các cột nó đổi: bên gọi không cần biết tên cột.
    # Method không log; bên gọi log theo kết quả trả về

    @classmethod
    def new(cls, *, event: OutboxEvent, handler: str, now: datetime) -> Self:
        """Delivery chưa lưu, tới hạn ngay cả retry lẫn giao lại; bên gọi `bulk_create`."""
        return cls(event=event, handler=handler, next_attempt_at=now, next_dispatch_at=now)

    @classmethod
    def reopen(cls, ids: Sequence[UUID], *, now: datetime) -> int:
        """Mở lại delivery `failed` đã khoá: lịch và bộ đếm về đầu, giữ `failed_at`, `last_error`.

        `failed_at` và `last_error` là dấu vết tới lần lỗi sau (07 mục 1.3).
        """
        return cls.objects.filter(id__in=ids).update(
            status=DeliveryStatus.PENDING,
            attempts=0,
            interrupted_runs=0,
            next_attempt_at=now,
            next_dispatch_at=now,
            retried_at=now,
        )

    @classmethod
    def mark_dispatched(
        cls, ids: Sequence[UUID], *, now: datetime, next_dispatch_at: datetime
    ) -> int:
        """Ghi lần giao và hạn giao lại; relay quyết định hạn (07 mục 1.1.1)."""
        return cls.objects.filter(id__in=ids).update(
            next_dispatch_at=next_dispatch_at, last_dispatched_at=now
        )

    def is_due(self, *, now: datetime) -> bool:
        return self.status == DeliveryStatus.PENDING and self.next_attempt_at <= now

    def start_run(self, *, now: datetime) -> RunStart:
        """Ghi một lần chạy dở trước khi gọi handler, hoặc `failed` khi đã đủ ngưỡng.

        Bên gọi commit ngay: worker bị kill giữa lúc handler chạy thì không còn ghi được gì. Khi
        `failed`, giữ `interrupted_runs` ở ngưỡng để người vận hành thấy vì sao.
        """
        if self.interrupted_runs >= MAX_INTERRUPTED_RUNS:
            self._fail(INTERRUPTED_ERROR, now=now)
            return RunStart.FAILED_INTERRUPTED
        self.interrupted_runs += 1
        self.save(update_fields=["interrupted_runs"])
        return RunStart.STARTED

    def complete(self, *, now: datetime) -> None:
        self.status = DeliveryStatus.COMPLETED
        self.completed_at = now
        self._save_outcome(["status", "completed_at"])

    def reject(self, exc: BaseException, *, now: datetime) -> None:
        self.status = DeliveryStatus.REJECTED
        self.completed_at = now
        self.last_error = describe_error(exc)
        self._save_outcome(["status", "completed_at", "last_error"])

    def retry_or_fail(self, exc: BaseException, *, now: datetime) -> RetryOutcome:
        """Tính một lỗi handler: hẹn lần thử kế theo `RETRY_DELAYS`, hết lịch thì `failed`."""
        self.attempts += 1
        self.last_error = describe_error(exc)
        if self.attempts > len(RETRY_DELAYS):
            self._mark_failed(now=now)
            self._save_outcome(["attempts", "last_error", "status", "failed_at"])
            return RetryOutcome.FAILED
        retry_at = now + RETRY_DELAYS[self.attempts - 1]
        self.next_attempt_at = retry_at
        self.next_dispatch_at = retry_at
        self._save_outcome(["attempts", "last_error", "next_attempt_at", "next_dispatch_at"])
        return RetryOutcome.SCHEDULED

    def fail(self, exc: BaseException, *, now: datetime) -> None:
        """`failed` ngay, không qua lịch retry, khi handler chưa chạy (payload không parse được).

        Handler chưa chạy nên `attempts` và `interrupted_runs` giữ nguyên (07 mục 1.3).
        """
        self._fail(describe_error(exc), now=now)

    def _fail(self, last_error: str, *, now: datetime) -> None:
        self._mark_failed(now=now)
        self.last_error = last_error
        self.save(update_fields=["status", "failed_at", "last_error"])

    def _mark_failed(self, *, now: datetime) -> None:
        self.status = DeliveryStatus.FAILED
        self.failed_at = now

    def _save_outcome(self, fields: list[str]) -> None:
        # Kết quả đã lưu được nghĩa là lần chạy này không dở: chuỗi chạy dở liên tiếp bị ngắt
        self.interrupted_runs = 0
        self.save(update_fields=[*fields, "interrupted_runs"])


def build_deliveries(
    event: OutboxEvent, handlers: list[Handler], now: datetime
) -> list[EventDelivery]:
    """Dựng (chưa lưu) delivery `pending` tới hạn ngay cho từng handler của sự kiện."""
    return [EventDelivery.new(event=event, handler=handler.name, now=now) for handler in handlers]
