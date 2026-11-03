from datetime import UTC, datetime, timedelta

import pytest
import time_machine
from django.core.management import call_command
from django.core.management.base import CommandError
from structlog.testing import capture_logs

from shared.events import handles
from shared.events.consumer import process_delivery
from shared.events.models import (
    INTERRUPTED_ERROR,
    MAX_INTERRUPTED_RUNS,
    DeliveryStatus,
    EventDelivery,
)
from shared.events.tests.conftest import SampleHappenedV1
from shared.testing.factories import EventDeliveryFactory, OutboxEventFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 10, 30, 8, 0, tzinfo=UTC)
FAILED_AT = NOW - timedelta(hours=2)


def _register(*names: str) -> None:
    for name in names:

        @handles("shared.sample-happened", name=name)
        def handler(event: SampleHappenedV1) -> None:
            pass


@time_machine.travel(NOW, tick=False)
def test_reopens_failed_and_next_run_succeeds() -> None:
    received: list[SampleHappenedV1] = []

    # Handler đã được sửa sau khi delivery hết lượt retry
    @handles("shared.sample-happened", name="shared.fixed_handler")
    def fixed_handler(event: SampleHappenedV1) -> None:
        received.append(event)

    delivery = EventDeliveryFactory.create(
        handler="shared.fixed_handler",
        status=DeliveryStatus.FAILED,
        attempts=6,
        next_attempt_at=FAILED_AT,
        failed_at=FAILED_AT,
        last_error="Boom",
    )

    call_command("retry_failed_events", "--event-id", str(delivery.event_id))
    process_delivery(delivery.event_id, "shared.fixed_handler")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.COMPLETED
    assert delivery.completed_at == NOW
    assert len(received) == 1


@time_machine.travel(NOW, tick=False)
def test_reopens_interrupted_delivery_with_counter_reset() -> None:
    received: list[SampleHappenedV1] = []

    # Handler đã được sửa sau khi liên tục làm worker chết (quá time limit, hết bộ nhớ)
    @handles("shared.sample-happened", name="shared.fixed_handler")
    def fixed_handler(event: SampleHappenedV1) -> None:
        received.append(event)

    delivery = EventDeliveryFactory.create(
        handler="shared.fixed_handler",
        status=DeliveryStatus.FAILED,
        interrupted_runs=MAX_INTERRUPTED_RUNS,
        next_attempt_at=FAILED_AT,
        failed_at=FAILED_AT,
        last_error=INTERRUPTED_ERROR,
    )

    call_command("retry_failed_events", "--event-id", str(delivery.event_id))

    delivery.refresh_from_db()
    reopened = (delivery.status, delivery.interrupted_runs)
    assert reopened == (DeliveryStatus.PENDING, 0)

    # Nếu không đặt lại bộ đếm thì lần giao này chuyển `failed` ngay mà không gọi handler
    process_delivery(delivery.event_id, "shared.fixed_handler")

    delivery.refresh_from_db()
    processed = (delivery.status, delivery.interrupted_runs, len(received))
    assert processed == (DeliveryStatus.COMPLETED, 0, 1)


def _failed(**kwargs: object) -> EventDelivery:
    return EventDeliveryFactory.create(
        status=DeliveryStatus.FAILED,
        attempts=6,
        next_attempt_at=FAILED_AT,
        next_dispatch_at=FAILED_AT + timedelta(minutes=3),
        failed_at=FAILED_AT,
        last_error="Boom",
        **kwargs,
    )


@time_machine.travel(NOW, tick=False)
def test_resets_schedule_and_counter_and_sets_retried_at() -> None:
    _register("shared.broken")
    delivery = _failed(handler="shared.broken")

    with capture_logs() as logs:
        call_command("retry_failed_events", "--handler", "shared.broken")

    delivery.refresh_from_db()
    assert (
        delivery.status,
        delivery.attempts,
        delivery.next_attempt_at,
        delivery.next_dispatch_at,
        delivery.retried_at,
    ) == (DeliveryStatus.PENDING, 0, NOW, NOW, NOW)
    # Dấu vết lần lỗi cũ giữ tới khi lần xử lý sau ghi đè
    assert (delivery.failed_at, delivery.last_error) == (FAILED_AT, "Boom")
    assert [(log["event"], log.get("handler"), log.get("count")) for log in logs] == [
        ("event_delivery_retried", "shared.broken", None),
        ("failed_deliveries_retried", None, 1),
    ]


@time_machine.travel(NOW, tick=False)
def test_does_not_reopen_completed_or_rejected() -> None:
    finished = [
        EventDeliveryFactory.create(status=status, completed_at=FAILED_AT, last_error="Boom")
        for status in (DeliveryStatus.COMPLETED, DeliveryStatus.REJECTED)
    ]

    call_command("retry_failed_events", "--all")

    for delivery in finished:
        before = (delivery.status, delivery.completed_at, delivery.retried_at)
        delivery.refresh_from_db()
        after = (delivery.status, delivery.completed_at, delivery.retried_at)
        assert after == before


@time_machine.travel(NOW, tick=False)
def test_all_reopens_every_failed_delivery() -> None:
    _register("shared.broken", "shared.other_handler")
    failed = [_failed(handler="shared.broken"), _failed(handler="shared.other_handler")]

    call_command("retry_failed_events", "--all")

    for delivery in failed:
        delivery.refresh_from_db()
        assert (delivery.status, delivery.retried_at) == (DeliveryStatus.PENDING, NOW)


@time_machine.travel(NOW, tick=False)
def test_skips_failed_delivery_of_unregistered_handler() -> None:
    _register("shared.broken")
    reopened = _failed(handler="shared.broken")
    # Handler đã bị gỡ khỏi code: mở lại sẽ kẹt `pending` mãi
    removed = _failed(handler="shared.removed_handler")

    with capture_logs() as logs:
        call_command("retry_failed_events", "--all")

    reopened.refresh_from_db()
    removed.refresh_from_db()
    assert reopened.status == DeliveryStatus.PENDING
    assert (removed.status, removed.attempts, removed.retried_at) == (
        DeliveryStatus.FAILED,
        6,
        None,
    )
    assert [
        (log["event"], log["log_level"], log.get("event_id"), log.get("handler"), log.get("count"))
        for log in logs
        if log["event"] != "event_delivery_retried"
    ] == [
        (
            "event_delivery_retry_skipped",
            "warning",
            str(removed.event_id),
            "shared.removed_handler",
            None,
        ),
        ("failed_deliveries_retried", "info", None, None, 1),
    ]


def test_unknown_handler_errors() -> None:
    _register("shared.broken")
    delivery = _failed(handler="shared.typo_handler")

    with pytest.raises(CommandError):
        call_command("retry_failed_events", "--handler", "shared.typo_handler")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.FAILED


@time_machine.travel(NOW, tick=False)
def test_filters_select_only_matching_pairs() -> None:
    _register("shared.broken", "shared.other_handler")
    event_row = OutboxEventFactory.create()
    other_type = OutboxEventFactory.create(event_type="shared.other-happened")
    target = _failed(event=event_row, handler="shared.broken")
    untouched = [
        _failed(event=event_row, handler="shared.other_handler"),
        _failed(handler="shared.broken"),
        _failed(event=other_type, handler="shared.broken"),
    ]

    call_command(
        "retry_failed_events",
        "--event-id",
        str(event_row.id),
        "--handler",
        "shared.broken",
        "--type",
        "shared.sample-happened",
    )

    target.refresh_from_db()
    assert target.status == DeliveryStatus.PENDING
    for delivery in untouched:
        delivery.refresh_from_db()
        assert delivery.status == DeliveryStatus.FAILED

    call_command("retry_failed_events", "--type", "shared.other-happened")

    untouched[2].refresh_from_db()
    assert untouched[2].status == DeliveryStatus.PENDING
    still_failed = EventDelivery.objects.filter(status=DeliveryStatus.FAILED).count()
    assert still_failed == 2


def test_requires_a_filter() -> None:
    delivery = _failed()

    with pytest.raises(CommandError):
        call_command("retry_failed_events")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.FAILED
