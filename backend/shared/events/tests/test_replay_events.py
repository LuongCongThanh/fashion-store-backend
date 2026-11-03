import threading
from datetime import timedelta
from typing import Any

import pytest
import time_machine
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.utils import timezone
from structlog.testing import capture_logs

from shared.events import handles, operations
from shared.events.models import DeliveryStatus, EventDelivery, OutboxEvent
from shared.events.tests._helpers import NOW, register_noop_handlers
from shared.events.tests.conftest import SampleHappenedV1
from shared.testing.factories import EventDeliveryFactory, OutboxEventFactory

pytestmark = pytest.mark.django_db

SINCE = NOW - timedelta(hours=1)
# Relay đã lập danh sách delivery sau mốc `since`
LISTED_AT = SINCE + timedelta(minutes=5)


def _handlers_of(event: OutboxEvent) -> list[str]:
    return sorted(EventDelivery.objects.filter(event=event).values_list("handler", flat=True))


@time_machine.travel(NOW, tick=False)
def test_replay_adds_delivery_for_new_handler() -> None:
    register_noop_handlers("shared.old_handler", "shared.new_handler", "shared.other_new_handler")
    event_row = OutboxEventFactory.create(sample=True, listed=True, occurred_at=LISTED_AT)
    EventDeliveryFactory.create(
        event=event_row,
        handler="shared.old_handler",
        status=DeliveryStatus.COMPLETED,
        completed_at=SINCE,
    )
    before_since = OutboxEventFactory.create(
        sample=True,
        occurred_at=SINCE - timedelta(seconds=2),
        deliveries_created_at=SINCE - timedelta(seconds=1),
    )
    other_type = OutboxEventFactory.create(
        sample=True, listed=True, occurred_at=LISTED_AT, event_type="shared.other-happened"
    )

    call_command(
        "replay_events",
        "--type",
        "shared.sample-happened",
        "--since",
        SINCE.isoformat(),
        "--handler",
        "shared.new_handler",
    )

    added = EventDelivery.objects.get(event=event_row, handler="shared.new_handler")
    assert (added.status, added.attempts, added.next_attempt_at, added.next_dispatch_at) == (
        DeliveryStatus.PENDING,
        0,
        NOW,
        NOW,
    )
    # Chỉ handler được chọn, chỉ sự kiện đúng loại và từ mốc `since`
    assert _handlers_of(event_row) == ["shared.new_handler", "shared.old_handler"]
    assert _handlers_of(before_since) == []
    assert _handlers_of(other_type) == []


@time_machine.travel(NOW, tick=False)
def test_replay_keeps_existing_deliveries(monkeypatch: pytest.MonkeyPatch) -> None:
    register_noop_handlers("shared.failed_handler", "shared.done_handler", "shared.new_handler")
    # Mỗi lô một sự kiện để kiểm cả việc đi qua nhiều lô
    monkeypatch.setattr(operations, "REPLAY_BATCH", 1)
    event_row = OutboxEventFactory.create(sample=True, listed=True, occurred_at=LISTED_AT)
    failed = EventDeliveryFactory.create(
        event=event_row,
        handler="shared.failed_handler",
        status=DeliveryStatus.FAILED,
        attempts=6,
        next_attempt_at=SINCE,
        failed_at=SINCE,
        last_error="Boom",
    )
    done = EventDeliveryFactory.create(
        event=event_row,
        handler="shared.done_handler",
        status=DeliveryStatus.COMPLETED,
        completed_at=SINCE,
    )
    second_event = OutboxEventFactory.create(sample=True, listed=True, occurred_at=LISTED_AT)

    with capture_logs() as logs:
        call_command(
            "replay_events", "--type", "shared.sample-happened", "--since", SINCE.isoformat()
        )

    failed.refresh_from_db()
    done.refresh_from_db()
    assert (failed.status, failed.attempts, failed.failed_at, failed.retried_at) == (
        DeliveryStatus.FAILED,
        6,
        SINCE,
        None,
    )
    assert (done.status, done.completed_at) == (DeliveryStatus.COMPLETED, SINCE)
    all_handlers = ["shared.done_handler", "shared.failed_handler", "shared.new_handler"]
    assert _handlers_of(event_row) == all_handlers
    assert _handlers_of(second_event) == all_handlers
    # Hai sự kiện đã xét; 1 delivery thêm cho `event_row`, 3 cho `second_event`
    replayed = [log for log in logs if log["event"] == "outbox_events_replayed"]
    assert [(log["examined"], log["created"]) for log in replayed] == [(2, 4)]


@time_machine.travel(NOW, tick=False)
def test_replay_selects_events_listed_since() -> None:
    register_noop_handlers("shared.new_handler")
    # Phát ngay trước mốc deploy nhưng relay cũ lập danh sách sau mốc: vẫn thiếu handler mới
    occurred_before_listed_after = OutboxEventFactory.create(
        sample=True,
        occurred_at=SINCE - timedelta(minutes=1),
        deliveries_created_at=SINCE + timedelta(seconds=1),
    )
    listed_at_since = OutboxEventFactory.create(
        sample=True, occurred_at=SINCE - timedelta(minutes=1), deliveries_created_at=SINCE
    )
    listed_before = OutboxEventFactory.create(
        sample=True,
        occurred_at=SINCE - timedelta(minutes=1),
        deliveries_created_at=SINCE - timedelta(seconds=1),
    )

    call_command("replay_events", "--type", "shared.sample-happened", "--since", SINCE.isoformat())

    assert _handlers_of(occurred_before_listed_after) == ["shared.new_handler"]
    # Mốc `since` tính cả mốc
    assert _handlers_of(listed_at_since) == ["shared.new_handler"]
    assert _handlers_of(listed_before) == []


@time_machine.travel(NOW, tick=False)
def test_replay_skips_event_not_yet_listed() -> None:
    register_noop_handlers("shared.new_handler")
    unlisted = OutboxEventFactory.create(sample=True, occurred_at=LISTED_AT)

    call_command("replay_events", "--type", "shared.sample-happened", "--since", SINCE.isoformat())

    # Relay sẽ lập danh sách cùng marker; replay không làm thay
    unlisted.refresh_from_db()
    assert unlisted.deliveries_created_at is None
    assert _handlers_of(unlisted) == []


def test_replay_unknown_handler_errors() -> None:
    register_noop_handlers("shared.new_handler")
    event_row = OutboxEventFactory.create(sample=True, listed=True, occurred_at=LISTED_AT)
    options = ("--type", "shared.sample-happened", "--since", SINCE.isoformat())

    with pytest.raises(CommandError):
        call_command("replay_events", *options, "--handler", "shared.typo_handler")

    assert _handlers_of(event_row) == []


def test_replay_handler_of_other_type_errors() -> None:
    register_noop_handlers("shared.new_handler")

    @handles("shared.other-happened", name="shared.other_type_handler")
    def other_type_handler(event: SampleHappenedV1) -> None:
        pass

    event_row = OutboxEventFactory.create(sample=True, listed=True, occurred_at=LISTED_AT)
    options = ("--type", "shared.sample-happened", "--since", SINCE.isoformat())

    with pytest.raises(CommandError):
        call_command("replay_events", *options, "--handler", "shared.other_type_handler")

    assert _handlers_of(event_row) == []


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
def test_replay_and_purge_concurrently_keep_new_delivery(monkeypatch: pytest.MonkeyPatch) -> None:
    register_noop_handlers("shared.old_handler", "shared.new_handler")
    listed_at = timezone.now() - operations.OUTBOX_RETENTION - timedelta(days=1)
    # Quá hạn giữ và mọi delivery đã xong: purge xoá được nếu replay không giữ khoá
    old_event = OutboxEventFactory.create(sample=True, listed=True, occurred_at=listed_at)
    EventDeliveryFactory.create(
        event=old_event,
        handler="shared.old_handler",
        status=DeliveryStatus.COMPLETED,
        completed_at=listed_at,
    )
    errors: list[BaseException] = []

    def purge() -> None:
        try:
            operations.purge_old_outbox_events()
        except BaseException as exc:
            errors.append(exc)
        finally:
            connection.close()

    purge_thread = threading.Thread(target=purge)
    real_build = operations.build_deliveries

    def build_while_purging(*args: Any) -> list[EventDelivery]:
        # Purge chạy giữa lúc replay đã đọc lô và lúc tạo delivery; có khoá thì purge phải chờ
        purge_thread.start()
        purge_thread.join(timeout=1)
        return real_build(*args)

    monkeypatch.setattr(operations, "build_deliveries", build_while_purging)

    operations.replay_events(event_type="shared.sample-happened", since=listed_at)
    purge_thread.join()

    assert errors == []
    assert _handlers_of(old_event) == ["shared.new_handler", "shared.old_handler"]
