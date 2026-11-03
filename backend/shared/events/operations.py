"""Thao tác vận hành outbox cho người vận hành và job theo lịch (07 mục 1.1.1, 1.3).

Management command và Celery task chỉ là lớp mỏng gọi vào các hàm ở đây.
"""

from datetime import datetime, timedelta
from uuid import UUID

import structlog
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone

from shared.events.models import DeliveryStatus, EventDelivery, OutboxEvent
from shared.events.registry import registry
from shared.events.relay import build_deliveries

logger = structlog.get_logger(__name__)

REPLAY_BATCH = 100
OUTBOX_RETENTION = timedelta(days=90)
PURGE_BATCH = 1000


def retry_failed_events(
    *,
    event_id: UUID | None = None,
    handler: str | None = None,
    event_type: str | None = None,
) -> int:
    """Mở lại delivery `failed` khớp mọi bộ lọc được truyền; relay sẽ giao lại.

    Đặt `pending`, `attempts = 0`, `interrupted_runs = 0` (delivery `failed` vì chạy dở được
    chạy lại thật), lịch retry và giao lại về hiện tại, ghi `retried_at`. Giữ `failed_at`,
    `last_error` làm dấu vết tới lần lỗi sau. Delivery `completed`/`rejected` không
    bao giờ được mở lại. Delivery của handler không còn trong registry không được mở lại (sẽ kẹt
    `pending` mãi) mà log `WARNING`. Không truyền bộ lọc nào nghĩa là mọi delivery `failed`. Trả
    số delivery đã mở lại.
    """
    deliveries = EventDelivery.objects.filter(status=DeliveryStatus.FAILED)
    if event_id is not None:
        deliveries = deliveries.filter(event_id=event_id)
    if handler is not None:
        deliveries = deliveries.filter(handler=handler)
    if event_type is not None:
        deliveries = deliveries.filter(event__event_type=event_type)

    with transaction.atomic():
        # Khoá rồi lọc lại `failed`: dòng vừa được mở lại ở nơi khác không bị đặt lại lần nữa
        locked = list(
            deliveries.select_for_update(of=("self",)).values_list("id", "event_id", "handler")
        )
        reopened = [row for row in locked if registry.get_handler(row[2]) is not None]
        skipped = [row for row in locked if registry.get_handler(row[2]) is None]
        now = timezone.now()
        EventDelivery.reopen([delivery_id for delivery_id, _, _ in reopened], now=now)
    for _, reopened_event_id, reopened_handler in reopened:
        logger.info(
            "event_delivery_retried", event_id=str(reopened_event_id), handler=reopened_handler
        )
    for _, skipped_event_id, skipped_handler in skipped:
        logger.warning(
            "event_delivery_retry_skipped", event_id=str(skipped_event_id), handler=skipped_handler
        )
    logger.info("failed_deliveries_retried", count=len(reopened))
    return len(reopened)


def replay_events(*, event_type: str, since: datetime, handler: str | None = None) -> int:
    """Tạo delivery còn thiếu cho sự kiện `event_type` được lập danh sách từ `since`.

    Chọn theo `deliveries_created_at` (lúc relay lập danh sách), không theo `occurred_at`: sự
    kiện phát trước mốc deploy nhưng được lập danh sách sau mốc vẫn thiếu handler mới. Chỉ tạo
    delivery còn thiếu; delivery đã có giữ nguyên, kể cả `failed`, `completed`. Không truyền
    `handler` nghĩa là mọi handler đăng ký cho `(event_type, schema_version)` của từng sự kiện.
    Sự kiện relay chưa lập danh sách được bỏ qua. Mỗi lô `REPLAY_BATCH` sự kiện một transaction,
    khoá sự kiện theo thứ tự `id` để purge chạy đồng thời không xoá sự kiện giữa chừng. Log số
    sự kiện đã xét và số delivery tạo mới. Trả số delivery tạo mới.
    """
    events = (
        OutboxEvent.objects.listed()
        .filter(event_type=event_type, deliveries_created_at__gte=since)
        .order_by("id")
    )
    examined = 0
    created = 0
    last_id: UUID | None = None
    while True:
        page = events if last_id is None else events.filter(id__gt=last_id)
        with transaction.atomic():
            # Sự kiện purge vừa xoá không còn trong lô; sự kiện đã khoá thì purge phải chờ
            batch = list(page.select_for_update()[:REPLAY_BATCH])
            if not batch:
                break
            batch_deliveries = EventDelivery.objects.filter(
                event_id__in=[event.id for event in batch]
            )
            before = batch_deliveries.count()
            now = timezone.now()
            deliveries: list[EventDelivery] = []
            for event in batch:
                handlers = registry.handlers_for(event.event_type, event.schema_version)
                if handler is not None:
                    handlers = [found for found in handlers if found.name == handler]
                deliveries.extend(build_deliveries(event, handlers, now))
            # Cặp đã có bị UNIQUE(event_id, handler) bỏ qua, không bị ghi đè
            EventDelivery.objects.bulk_create(deliveries, ignore_conflicts=True)
            created += batch_deliveries.count() - before
        examined += len(batch)
        last_id = batch[-1].id
    logger.info(
        "outbox_events_replayed",
        event_type=event_type,
        handler=handler,
        examined=examined,
        created=created,
    )
    return created


def purge_old_outbox_events() -> int:
    """Xoá sự kiện quá `OUTBOX_RETENTION` mà mọi delivery đã kết thúc, kèm delivery của nó.

    Giữ sự kiện còn delivery `pending`/`failed` để relay hoặc `retry_failed_events` khôi phục.
    Sự kiện có marker mà không có delivery nào cũng bị xoá. Mỗi lô `PURGE_BATCH` sự kiện một
    transaction, lặp tới khi hết. Còn sự kiện quá hạn bị giữ thì log `WARNING`. Trả số sự kiện
    đã xoá.
    """
    cutoff = timezone.now() - OUTBOX_RETENTION
    old = OutboxEvent.objects.filter(occurred_at__lt=cutoff)
    unfinished = EventDelivery.objects.filter(event=OuterRef("pk")).unfinished()
    purgeable = old.listed().exclude(Exists(unfinished))
    purged = 0
    while True:
        with transaction.atomic():
            # Khoá sự kiện chặn delivery mới trỏ tới nó (khoá của FK) tới khi commit; lọc lại
            # sau khi khoá để bỏ sự kiện vừa được replay thêm delivery `pending`. Khoá theo thứ
            # tự `id` như replay để hai bên không deadlock
            ids = list(
                purgeable.select_for_update()
                .order_by("id")
                .values_list("id", flat=True)[:PURGE_BATCH]
            )
            if not ids:
                break
            _, deleted = purgeable.filter(id__in=ids).delete()
        purged += deleted.get(OutboxEvent._meta.label, 0)
    kept = old.count()
    if kept:
        logger.warning("outbox_purge_kept_unfinished", count=kept)
    logger.info("outbox_events_purged", count=purged)
    return purged
