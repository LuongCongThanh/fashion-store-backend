from datetime import timedelta

import pytest
import time_machine
from celery.schedules import crontab
from structlog.testing import capture_logs

from common.events import operations
from common.events.models import DeliveryStatus, EventDelivery, OutboxEvent
from common.events.tasks import purge_old_outbox_events
from common.events.tests._helpers import NOW
from common.tests.factories import EventDeliveryFactory, OutboxEventFactory
from config.celery import app

pytestmark = pytest.mark.django_db

# Vừa quá hạn giữ 90 ngày
OLD = NOW - timedelta(days=90, seconds=1)


def _finished(event: OutboxEvent, status: DeliveryStatus) -> EventDelivery:
    return EventDeliveryFactory.create(event=event, status=status, completed_at=OLD)


@time_machine.travel(NOW, tick=False)
def test_purge_deletes_old_finished_events_and_deliveries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Mỗi lô một sự kiện để kiểm cả việc đi qua nhiều lô
    monkeypatch.setattr(operations, "PURGE_BATCH", 1)
    finished = OutboxEventFactory.create(listed=True, occurred_at=OLD)
    _finished(finished, DeliveryStatus.COMPLETED)
    _finished(finished, DeliveryStatus.REJECTED)
    # Có marker mà không có handler nào đăng ký
    OutboxEventFactory.create(listed=True, occurred_at=OLD)
    recent = OutboxEventFactory.create(listed=True, occurred_at=NOW - timedelta(days=1))
    recent_delivery = _finished(recent, DeliveryStatus.COMPLETED)

    purge_old_outbox_events()

    assert list(OutboxEvent.objects.values_list("id", flat=True)) == [recent.id]
    assert list(EventDelivery.objects.values_list("id", flat=True)) == [recent_delivery.id]


@time_machine.travel(NOW, tick=False)
def test_purge_keeps_events_with_pending_or_failed() -> None:
    with_pending = OutboxEventFactory.create(listed=True, occurred_at=OLD)
    _finished(with_pending, DeliveryStatus.COMPLETED)
    EventDeliveryFactory.create(event=with_pending, next_attempt_at=OLD)
    with_failed = OutboxEventFactory.create(listed=True, occurred_at=OLD)
    _finished(with_failed, DeliveryStatus.REJECTED)
    EventDeliveryFactory.create(event=with_failed, failed=True, failed_at=OLD)
    deliveries_before = sorted(EventDelivery.objects.values_list("id", flat=True))

    with capture_logs() as logs:
        purge_old_outbox_events()

    # Giữ để retry_failed_events hoặc relay còn khôi phục được
    assert sorted(OutboxEvent.objects.values_list("id", flat=True)) == sorted(
        [with_pending.id, with_failed.id]
    )
    assert sorted(EventDelivery.objects.values_list("id", flat=True)) == deliveries_before
    kept = [log for log in logs if log["event"] == "outbox_purge_kept_unfinished"]
    assert [(log["log_level"], log["count"]) for log in kept] == [("warning", 2)]


@time_machine.travel(NOW, tick=False)
def test_purge_keeps_old_event_not_yet_listed() -> None:
    # Relay chưa lập danh sách delivery: chưa handler nào nhận sự kiện này
    unlisted = OutboxEventFactory.create(occurred_at=OLD)

    with capture_logs() as logs:
        purge_old_outbox_events()

    assert list(OutboxEvent.objects.values_list("id", flat=True)) == [unlisted.id]
    kept = [log for log in logs if log["event"] == "outbox_purge_kept_unfinished"]
    assert [(log["log_level"], log["count"]) for log in kept] == [("warning", 1)]


@time_machine.travel(NOW, tick=False)
def test_purge_respects_retention_boundary() -> None:
    at_boundary = OutboxEventFactory.create(
        listed=True, occurred_at=NOW - operations.OUTBOX_RETENTION
    )
    _finished(at_boundary, DeliveryStatus.COMPLETED)
    past_boundary = OutboxEventFactory.create(
        listed=True, occurred_at=NOW - operations.OUTBOX_RETENTION - timedelta(seconds=1)
    )
    _finished(past_boundary, DeliveryStatus.COMPLETED)

    purge_old_outbox_events()

    # Chỉ xoá sự kiện quá 90 ngày, đúng 90 ngày thì còn giữ
    retention = operations.OUTBOX_RETENTION
    assert retention == timedelta(days=90)
    assert list(OutboxEvent.objects.values_list("id", flat=True)) == [at_boundary.id]


@time_machine.travel(NOW, tick=False)
def test_purge_twice_same_result() -> None:
    finished = OutboxEventFactory.create(listed=True, occurred_at=OLD)
    _finished(finished, DeliveryStatus.COMPLETED)
    kept = OutboxEventFactory.create(listed=True, occurred_at=OLD)
    EventDeliveryFactory.create(event=kept, next_attempt_at=OLD)
    recent = OutboxEventFactory.create(listed=True, occurred_at=NOW - timedelta(days=1))

    purge_old_outbox_events()
    after_first = (
        sorted(OutboxEvent.objects.values_list("id", flat=True)),
        sorted(EventDelivery.objects.values_list("id", "status")),
    )
    purge_old_outbox_events()

    after_second = (
        sorted(OutboxEvent.objects.values_list("id", flat=True)),
        sorted(EventDelivery.objects.values_list("id", "status")),
    )
    assert after_first[0] == sorted([kept.id, recent.id])
    assert after_second == after_first


def test_purge_scheduled_daily_0330() -> None:
    entry = app.conf.beat_schedule["common.purge_old_outbox_events"]

    # Giờ theo CELERY_TIMEZONE (Asia/Ho_Chi_Minh)
    assert entry["schedule"] == crontab(hour=3, minute=30)
    assert entry["task"] == purge_old_outbox_events.name
    assert app.tasks[entry["task"]].queue == "default"  # type: ignore[attr-defined]  # celery-types thiếu Task.queue
