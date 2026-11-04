from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
import time_machine
from celery.schedules import crontab
from structlog.testing import capture_logs

from common import idempotency
from common.idempotency.models import IdempotencyKey
from common.idempotency.tasks import purge_idempotency_keys
from common.tests.factories import IdempotencyKeyFactory
from config.celery import app

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 10, 30, 8, 0, tzinfo=UTC)
# Vừa quá hạn giữ 24 giờ
OLD = NOW - timedelta(hours=24, seconds=1)


def _ids() -> list[UUID]:
    return sorted(IdempotencyKey.objects.values_list("id", flat=True))


@time_machine.travel(NOW, tick=False)
def test_purge_keeps_in_progress_keys() -> None:
    # Lease còn hoặc đã hết, tạo từ lâu: chưa rõ kết quả nên không xoá
    alive = IdempotencyKeyFactory.create()
    expired = IdempotencyKeyFactory.create(lease_expires_at=OLD)
    IdempotencyKey.objects.filter(pk=expired.pk).update(created_at=OLD)

    purge_idempotency_keys()

    assert _ids() == sorted([alive.id, expired.id])


@time_machine.travel(NOW, tick=False)
def test_purge_deletes_completed_older_than_24h() -> None:
    old = IdempotencyKeyFactory.create(completed=True, completed_at=OLD)
    recent = IdempotencyKeyFactory.create(completed=True, completed_at=NOW - timedelta(hours=1))

    with capture_logs() as logs:
        purged = idempotency.purge_idempotency_keys()

    assert purged == 1
    assert _ids() == [recent.id]
    assert not IdempotencyKey.objects.filter(pk=old.pk).exists()
    done = [log for log in logs if log["event"] == "idempotency_keys_purged"]
    assert [(log["log_level"], log["count"]) for log in done] == [("info", 1)]


@time_machine.travel(NOW, tick=False)
def test_purge_keeps_completed_at_exact_24h() -> None:
    at_boundary = IdempotencyKeyFactory.create(
        completed=True, completed_at=NOW - timedelta(hours=24)
    )

    purged = idempotency.purge_idempotency_keys()

    assert purged == 0
    assert _ids() == [at_boundary.id]


@time_machine.travel(NOW, tick=False)
def test_purge_runs_in_batches(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mỗi lô một key để kiểm việc đi qua nhiều lô
    monkeypatch.setattr(idempotency, "PURGE_BATCH", 1)
    IdempotencyKeyFactory.create_batch(3, completed=True, completed_at=OLD)
    kept = IdempotencyKeyFactory.create()

    with capture_logs() as logs:
        purged = idempotency.purge_idempotency_keys()

    assert purged == 3
    assert _ids() == [kept.id]
    done = [log for log in logs if log["event"] == "idempotency_keys_purged"]
    assert [log["count"] for log in done] == [3]


def test_purge_scheduled_daily_0345() -> None:
    entry = app.conf.beat_schedule["common.purge_idempotency_keys"]

    # Giờ theo CELERY_TIMEZONE (Asia/Ho_Chi_Minh)
    assert entry["schedule"] == crontab(hour=3, minute=45)
    assert entry["task"] == purge_idempotency_keys.name
    assert app.tasks[entry["task"]].queue == "default"  # type: ignore[attr-defined]  # celery-types thiếu Task.queue
