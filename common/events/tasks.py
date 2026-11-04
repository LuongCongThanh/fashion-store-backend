"""Celery task của outbox: giao delivery cho consumer (07 mục 1.1.1, 3.1) và job purge (07 mục
3.2)."""

from celery import shared_task

from common.events import operations
from common.events.consumer import process_delivery


@shared_task(name="common.dispatch_event", queue="events")
def dispatch_event(event_id: str, handler_name: str) -> None:
    # Trạng thái và lịch retry nằm trên delivery trong PostgreSQL, không dùng retry của Celery
    process_delivery(event_id, handler_name)


@shared_task(name="common.purge_old_outbox_events", queue="default")
def purge_old_outbox_events() -> None:
    operations.purge_old_outbox_events()
