"""Job theo lịch của `Idempotency-Key` (07 mục 3.2)."""

from celery import shared_task

from shared import idempotency


@shared_task(name="shared.purge_idempotency_keys", queue="default")
def purge_idempotency_keys() -> None:
    idempotency.purge_idempotency_keys()
