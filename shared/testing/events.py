"""Chạy sự kiện tới handler trong test (12 mục 2.7)."""

from collections.abc import Callable
from typing import Any, cast

import structlog
from django.db import connection

from shared.events import relay

logger = structlog.get_logger(__name__)

MAX_ROUNDS = 100


def drain_events() -> None:
    """Chạy callback `on_commit` đang chờ, relay và handler tới khi không còn việc tới hạn.

    Test chạy trong transaction không commit nên callback `on_commit` và relay không tự chạy.
    Celery eager trong test nên handler chạy ngay trong `dispatch_due`. Không chờ retry tương
    lai: test retry dùng time-machine tiến tới hạn rồi gọi lại. Quá `MAX_ROUNDS` vòng thì ném
    lỗi thay vì lặp vô hạn (ví dụ handler phát sự kiện mới mãi).
    """
    for _ in range(MAX_ROUNDS):
        callbacks = _run_on_commit_callbacks()
        events = relay.create_deliveries()
        deliveries = relay.dispatch_due()
        if callbacks == events == deliveries == 0:
            return
    raise RuntimeError(f"drain_events: còn việc sau {MAX_ROUNDS} vòng, có thể đang lặp vô hạn")


def _run_on_commit_callbacks() -> int:
    """Chạy và gỡ callback `on_commit` đang chờ, kể cả callback chúng thêm vào.

    Gỡ khỏi danh sách để lần drain sau không chạy lại. Callback `robust` lỗi thì log rồi chạy
    tiếp, như Django khi commit thật.
    """
    count = 0
    while connection.run_on_commit:
        # django-stubs khai báo phần tử 2 giá trị; Django 5 lưu (savepoint_ids, callback, robust)
        pending = cast(list[tuple[Any, Callable[[], object], bool]], list(connection.run_on_commit))
        connection.run_on_commit.clear()
        for _, callback, robust in pending:
            count += 1
            if not robust:
                callback()
                continue
            try:
                callback()
            except Exception:
                logger.exception("on_commit_callback_failed", callback=callback.__qualname__)
    return count
