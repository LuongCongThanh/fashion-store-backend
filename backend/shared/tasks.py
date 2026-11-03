"""Đẩy Celery task sau khi transaction commit (13 mục 4, 07 mục 1.3) và job theo lịch của
`shared` (07 mục 3.2)."""

from typing import Any

import structlog
from celery import shared_task
from django.db import transaction
from kombu.exceptions import OperationalError

from config.celery import app
from shared import idempotency
from shared.events import operations

logger = structlog.get_logger(__name__)


def enqueue_on_commit(task_name: str, **kwargs: Any) -> None:
    """Đẩy task `task_name` với `kwargs` khi transaction hiện tại commit.

    Rollback thì task không được đẩy. Lấy task trong registry của app (không `send_task`) để
    tên sai ném `KeyError` ngay lúc gọi và `CELERY_TASK_ALWAYS_EAGER` của test có hiệu lực.
    Lỗi kết nối broker chỉ ghi log `enqueue_failed` mức ERROR, không làm request đã commit trả
    lỗi; việc bắt buộc phải xảy ra có bản ghi DB và job quét lại. Lỗi khác (lập trình, dữ liệu)
    vẫn được Django log qua `robust=True`.
    """
    task = app.tasks[task_name]

    def send() -> None:
        try:
            task.apply_async(kwargs=kwargs)
        except OperationalError:
            # Không ghi kwargs: có thể chứa dữ liệu cá nhân
            logger.exception("enqueue_failed", task_name=task_name)

    transaction.on_commit(send, robust=True)


@shared_task(name="shared.purge_old_outbox_events", queue="default")
def purge_old_outbox_events() -> None:
    operations.purge_old_outbox_events()


@shared_task(name="shared.purge_idempotency_keys", queue="default")
def purge_idempotency_keys() -> None:
    idempotency.purge_idempotency_keys()
