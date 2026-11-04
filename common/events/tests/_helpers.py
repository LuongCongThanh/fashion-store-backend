"""Hằng số, exception giả và helper dùng chung cho test của `common.events`.

Fixture, sự kiện mẫu và model test-only ở `conftest.py`.
"""

import threading
from collections.abc import Callable
from datetime import UTC, datetime

from django.db import connection

from common.events import handles
from common.events.tests.conftest import HandlerEffect, SampleHappenedV1
from common.exceptions import DomainError, RetryLater

NOW = datetime(2026, 10, 30, 8, 0, tzinfo=UTC)
# Khớp payload của trait `OutboxEventFactory(sample=True)`
ORDER_CODE = "FS2610-7K3QZD"


class Boom(Exception):
    """Lỗi bất ngờ của handler: consumer hẹn retry."""


class NotYet(RetryLater):
    code = "NOT_YET"


class Refused(DomainError):
    code = "REFUSED"


class WorkerKilled(BaseException):
    """Giả lập worker bị kill giữa lúc handler chạy (quá time limit, hết bộ nhớ).

    Không phải `Exception` nên consumer không bắt được để lưu lỗi: transaction chạy handler
    rollback như khi process chết.
    """


def register_noop_handlers(*names: str) -> None:
    """Đăng ký handler không làm gì cho sự kiện mẫu, để relay/replay lập delivery cho chúng."""
    for name in names:

        @handles(SampleHappenedV1.event_type, name=name)
        def handler(event: SampleHappenedV1) -> None:
            pass


def record_effect(effects: type[HandlerEffect], handler: str, event: SampleHappenedV1) -> None:
    effects.objects.create(handler=handler, order_code=event.order_code)


def run_concurrently(work: Callable[[], object], *, threads: int = 2) -> list[BaseException]:
    """Chạy `work` trên nhiều thread cùng xuất phát qua `Barrier` (12 mục 2.2).

    Mỗi thread đóng kết nối DB của nó. Trả về lỗi các thread gặp, để test assert `== []`.
    """
    barrier = threading.Barrier(threads)
    errors: list[BaseException] = []

    def run() -> None:
        try:
            barrier.wait()
            work()
        except BaseException as exc:
            errors.append(exc)
        finally:
            connection.close()

    workers = [threading.Thread(target=run) for _ in range(threads)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    return errors
