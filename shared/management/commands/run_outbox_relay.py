"""Chạy outbox relay: mỗi giây lập danh sách delivery rồi giao delivery tới hạn (07 mục 1.1.1).

Lỗi DB hoặc broker trong một bước chỉ được log, bước còn lại và vòng sau vẫn chạy: tiến trình
không thoát, để container `relay` không khởi động lại liên tục khi PostgreSQL hay Redis tạm
ngừng. Dừng sạch sau vòng đang chạy khi nhận SIGTERM (`docker compose stop`) hoặc SIGINT
(Ctrl+C).
"""

import signal
import threading
from argparse import ArgumentParser
from types import FrameType

import structlog
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from shared.events import relay

logger = structlog.get_logger(__name__)

INTERVAL_SECONDS = 1.0


class Command(BaseCommand):
    help = "Chạy outbox relay: tạo EventDelivery và giao delivery tới hạn cho Celery."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--once", action="store_true", help="Chạy một vòng rồi thoát.")

    def handle(self, *args: object, **options: object) -> None:
        if options["once"]:
            _run_iteration()
            return

        stop = threading.Event()

        def request_stop(signum: int, frame: FrameType | None) -> None:
            logger.info("outbox_relay_stopping", signal=signal.Signals(signum).name)
            stop.set()

        # Windows không gửi SIGTERM cho tiến trình console; container Linux thì có
        for name in ("SIGINT", "SIGTERM"):
            signum = getattr(signal, name, None)
            if signum is not None:
                signal.signal(signum, request_stop)

        logger.info("outbox_relay_started", interval_seconds=INTERVAL_SECONDS)
        while not stop.is_set():
            _run_iteration()
            stop.wait(INTERVAL_SECONDS)
        logger.info("outbox_relay_stopped")


def _run_iteration() -> None:
    # Mỗi bước bắt lỗi riêng: lập danh sách lỗi không chặn việc giao delivery đã có
    for step in ("create_deliveries", "dispatch_due"):
        try:
            getattr(relay, step)()
        except Exception:
            logger.exception("outbox_relay_iteration_failed", step=step)
            # Bỏ kết nối DB đã hỏng để bước sau kết nối lại
            close_old_connections()
