from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any
from unittest import mock

import pytest
from django.db import transaction
from kombu.exceptions import OperationalError
from structlog.testing import capture_logs

from config.celery import app
from shared.tasks import enqueue_on_commit

pytestmark = pytest.mark.django_db

CaptureOnCommit = Callable[..., AbstractContextManager[list[Callable[[], Any]]]]

# Task có sẵn trong registry của app; apply_async bị patch nên không chạy thật
TASK_NAME = "shared.dispatch_event"


class Rollback(Exception):
    pass


def test_enqueue_on_commit_runs_after_commit(
    django_capture_on_commit_callbacks: CaptureOnCommit,
) -> None:
    with (
        mock.patch.object(app.tasks[TASK_NAME], "apply_async") as apply_async,
        django_capture_on_commit_callbacks(execute=True),
        transaction.atomic(),
    ):
        enqueue_on_commit(TASK_NAME, event_id="e-1", handler_name="shared.h")
        # Chưa commit thì chưa đẩy lên broker
        apply_async.assert_not_called()

    apply_async.assert_called_once_with(kwargs={"event_id": "e-1", "handler_name": "shared.h"})


def test_enqueue_on_commit_skipped_on_rollback(
    django_capture_on_commit_callbacks: CaptureOnCommit,
) -> None:
    def write_and_fail() -> None:
        with transaction.atomic():
            enqueue_on_commit(TASK_NAME, event_id="e-1", handler_name="shared.h")
            raise Rollback

    with (
        mock.patch.object(app.tasks[TASK_NAME], "apply_async") as apply_async,
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(Rollback),
    ):
        write_and_fail()

    assert callbacks == []
    apply_async.assert_not_called()


def test_enqueue_on_commit_broker_error_is_logged(
    django_capture_on_commit_callbacks: CaptureOnCommit,
) -> None:
    with (
        mock.patch.object(
            app.tasks[TASK_NAME], "apply_async", side_effect=OperationalError("broker down")
        ),
        capture_logs() as logs,
        django_capture_on_commit_callbacks(execute=True),
        transaction.atomic(),
    ):
        # Lỗi broker không làm request đã commit trả lỗi
        enqueue_on_commit(TASK_NAME, event_id="e-1", handler_name="shared.h")

    failed = [log for log in logs if log["event"] == "enqueue_failed"]
    assert len(failed) == 1
    assert failed[0]["log_level"] == "error"
    assert failed[0]["task_name"] == TASK_NAME
    # Không ghi kwargs vào log để không lọt PII
    assert "kwargs" not in failed[0]


def test_enqueue_on_commit_unknown_task_raises_immediately(
    django_capture_on_commit_callbacks: CaptureOnCommit,
) -> None:
    # Tên task sai là lỗi lập trình: lộ ngay lúc gọi, không nuốt trong on_commit
    with django_capture_on_commit_callbacks() as callbacks, pytest.raises(KeyError):
        enqueue_on_commit("shared.no_such_task", order_id="o-1")

    assert callbacks == []
