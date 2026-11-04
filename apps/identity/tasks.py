"""Job theo lịch của identity (07 mục 3.2)."""

import structlog
from celery import shared_task
from django.utils import timezone

from apps.identity.models import RefreshReplay

logger = structlog.get_logger(__name__)


@shared_task(name="identity.purge_refresh_replays", queue="default")
def purge_refresh_replays() -> None:
    """Xoá RefreshReplay có `expires_at <= now` (03 mục 2.5).

    Chỉ dọn ciphertext: endpoint refresh vẫn tự kiểm hạn trước decrypt dù job chưa chạy. Một câu
    DELETE vì mỗi replay chỉ sống 10 giây nên số dòng hết hạn mỗi phút nhỏ.
    """
    deleted, _ = RefreshReplay.objects.expired(timezone.now()).delete()
    logger.info("refresh_replays_purged", count=deleted)
