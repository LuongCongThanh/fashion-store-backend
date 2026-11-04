"""Outbox relay: lập danh sách delivery và giao delivery tới hạn cho Celery (07 mục 1.1.1).

Hai bước chạy độc lập, mỗi bước một transaction ngắn và khoá bằng `SKIP LOCKED`, nên nhiều
relay chạy cùng lúc không tạo trùng hay giao trùng trong cùng một hạn. Relay không phụ thuộc
Celery Beat; `run_outbox_relay` gọi hai hàm này mỗi giây.
"""

from datetime import timedelta

import structlog
from django.db import transaction
from django.utils import timezone
from kombu.exceptions import OperationalError

from shared.events.models import EventDelivery, OutboxEvent, build_deliveries
from shared.events.registry import registry
from shared.events.tasks import dispatch_event

logger = structlog.get_logger(__name__)

# Hạn giao lại phải dài hơn `CELERY_TASK_TIME_LIMIT` 120 giây (07 mục 1.1.1, 3.3)
REDISPATCH_AFTER = timedelta(minutes=3)


def create_deliveries(batch: int = 100) -> int:
    """Tạo delivery cho mọi handler của tối đa `batch` sự kiện chưa lập danh sách.

    Delivery và marker `deliveries_created_at` ghi cùng transaction. Trả số sự kiện đã xử lý.
    """
    with transaction.atomic():
        events = list(
            OutboxEvent.objects.select_for_update(skip_locked=True)
            .unlisted()
            .order_by("occurred_at")[:batch]
        )
        if not events:
            return 0
        now = timezone.now()
        deliveries: list[EventDelivery] = []
        for event in events:
            handlers = registry.handlers_for(event.event_type, event.schema_version)
            if not handlers:
                # Vẫn ghi marker để không quét mãi sự kiện này
                logger.info(
                    "outbox_event_no_handlers",
                    event_id=str(event.id),
                    event_type=event.event_type,
                    schema_version=event.schema_version,
                )
            deliveries.extend(build_deliveries(event, handlers, now))
        # UNIQUE(event_id, handler) là lưới an toàn cuối khi khoá dòng không đủ
        EventDelivery.objects.bulk_create(deliveries, ignore_conflicts=True)
        OutboxEvent.objects.filter(id__in=[event.id for event in events]).update(
            deliveries_created_at=now
        )
    return len(events)


def dispatch_due(batch: int = 100) -> int:
    """Giao tối đa `batch` delivery `pending` đã tới hạn retry và hạn giao lại.

    Hạn giao lại được commit trước khi gọi broker: relay chết trước enqueue, broker mất task hay
    worker chết trước commit đều khiến delivery được giao lại sau `REDISPATCH_AFTER`. Lỗi kết
    nối broker dừng lô và log một lần mức WARNING; các delivery còn lại giữ hạn đã lưu, không
    tính là handler thất bại. Lỗi khác (lập trình) ném ra (07 mục 1.3). Trả số delivery đã chọn.
    """
    with transaction.atomic():
        now = timezone.now()
        due = list(
            EventDelivery.objects.select_for_update(skip_locked=True)
            .dispatch_due(now)
            .order_by("next_dispatch_at")
            .values_list("id", "event_id", "handler")[:batch]
        )
        if not due:
            return 0
        EventDelivery.mark_dispatched(
            [delivery_id for delivery_id, _, _ in due],
            now=now,
            next_dispatch_at=now + REDISPATCH_AFTER,
        )

    # Không giữ transaction DB khi gọi broker; queue `events` do decorator của task định tuyến
    for index, (_, event_id, handler) in enumerate(due):
        try:
            dispatch_event.apply_async(args=(str(event_id), handler))
        except OperationalError:
            # Broker không nhận thì các lần gọi sau cũng lỗi: dừng lô, chờ hạn giao lại
            logger.warning(
                "outbox_dispatch_failed",
                event_id=str(event_id),
                handler=handler,
                deferred=len(due) - index,
                exc_info=True,
            )
            break
    return len(due)
