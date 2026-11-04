from datetime import timedelta

import pytest
import time_machine
from django.core.management import call_command
from django.core.management.base import CommandError
from structlog.testing import capture_logs

from common.events import handles
from common.events.consumer import process_delivery
from common.events.models import (
    INTERRUPTED_ERROR,
    MAX_INTERRUPTED_RUNS,
    DeliveryStatus,
    EventDelivery,
)
from common.events.tests._helpers import NOW, register_noop_handlers
from common.events.tests.conftest import SampleHappenedV1
from common.tests.factories import EventDeliveryFactory, OutboxEventFactory

pytestmark = pytest.mark.django_db

FAILED_AT = NOW - timedelta(hours=2)


@time_machine.travel(NOW, tick=False)
def test_reopens_failed_and_next_run_succeeds() -> None:
    received: list[SampleHappenedV1] = []

    # Handler đã được sửa sau khi delivery hết lượt retry
    @handles("common.sample-happened", name="common.fixed_handler")
    def fixed_handler(event: SampleHappenedV1) -> None:
        received.append(event)

    delivery = EventDeliveryFactory.create(
        event__sample=True,
        failed=True,
        handler="common.fixed_handler",
        attempts=6,
        failed_at=FAILED_AT,
    )

    call_command("retry_failed_events", "--event-id", str(delivery.event_id))
    process_delivery(delivery.event_id, "common.fixed_handler")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.COMPLETED
    assert delivery.completed_at == NOW
    assert len(received) == 1


@time_machine.travel(NOW, tick=False)
def test_reopens_interrupted_delivery_with_counter_reset() -> None:
    received: list[SampleHappenedV1] = []

    # Handler đã được sửa sau khi liên tục làm worker chết (quá time limit, hết bộ nhớ)
    @handles("common.sample-happened", name="common.fixed_handler")
    def fixed_handler(event: SampleHappenedV1) -> None:
        received.append(event)

    delivery = EventDeliveryFactory.create(
        event__sample=True,
        failed=True,
        handler="common.fixed_handler",
        interrupted_runs=MAX_INTERRUPTED_RUNS,
        failed_at=FAILED_AT,
        last_error=INTERRUPTED_ERROR,
    )

    call_command("retry_failed_events", "--event-id", str(delivery.event_id))

    delivery.refresh_from_db()
    reopened = (delivery.status, delivery.interrupted_runs)
    assert reopened == (DeliveryStatus.PENDING, 0)

    # Nếu không đặt lại bộ đếm thì lần giao này chuyển `failed` ngay mà không gọi handler
    process_delivery(delivery.event_id, "common.fixed_handler")

    delivery.refresh_from_db()
    processed = (delivery.status, delivery.interrupted_runs, len(received))
    assert processed == (DeliveryStatus.COMPLETED, 0, 1)


@time_machine.travel(NOW, tick=False)
def test_reopens_failed_and_logs_each_delivery() -> None:
    # Cột được đặt lại khi mở: test_models.py::test_reopen_resets_failed_delivery
    register_noop_handlers("common.broken")
    delivery = EventDeliveryFactory.create(event__sample=True, failed=True, handler="common.broken")

    with capture_logs() as logs:
        call_command("retry_failed_events", "--handler", "common.broken")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.PENDING
    assert [(log["event"], log.get("handler"), log.get("count")) for log in logs] == [
        ("event_delivery_retried", "common.broken", None),
        ("failed_deliveries_retried", None, 1),
    ]


@time_machine.travel(NOW, tick=False)
def test_does_not_reopen_completed_or_rejected() -> None:
    finished = [
        EventDeliveryFactory.create(
            event__sample=True, status=status, completed_at=FAILED_AT, last_error="Boom"
        )
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
    register_noop_handlers("common.broken", "common.other_handler")
    failed = [
        EventDeliveryFactory.create(event__sample=True, failed=True, handler="common.broken"),
        EventDeliveryFactory.create(
            event__sample=True, failed=True, handler="common.other_handler"
        ),
    ]

    call_command("retry_failed_events", "--all")

    for delivery in failed:
        delivery.refresh_from_db()
        assert (delivery.status, delivery.retried_at) == (DeliveryStatus.PENDING, NOW)


@time_machine.travel(NOW, tick=False)
def test_skips_failed_delivery_of_unregistered_handler() -> None:
    register_noop_handlers("common.broken")
    reopened = EventDeliveryFactory.create(event__sample=True, failed=True, handler="common.broken")
    # Handler đã bị gỡ khỏi code: mở lại sẽ kẹt `pending` mãi
    removed = EventDeliveryFactory.create(
        event__sample=True, failed=True, handler="common.removed_handler", attempts=6
    )

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
            "common.removed_handler",
            None,
        ),
        ("failed_deliveries_retried", "info", None, None, 1),
    ]


def test_unknown_handler_errors() -> None:
    register_noop_handlers("common.broken")
    delivery = EventDeliveryFactory.create(
        event__sample=True, failed=True, handler="common.typo_handler"
    )

    with pytest.raises(CommandError):
        call_command("retry_failed_events", "--handler", "common.typo_handler")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.FAILED


@time_machine.travel(NOW, tick=False)
def test_filters_select_only_matching_pairs() -> None:
    register_noop_handlers("common.broken", "common.other_handler")
    event_row = OutboxEventFactory.create(sample=True)
    other_type = OutboxEventFactory.create(event_type="common.other-happened")
    target = EventDeliveryFactory.create(failed=True, event=event_row, handler="common.broken")
    untouched = [
        EventDeliveryFactory.create(failed=True, event=event_row, handler="common.other_handler"),
        EventDeliveryFactory.create(event__sample=True, failed=True, handler="common.broken"),
        EventDeliveryFactory.create(failed=True, event=other_type, handler="common.broken"),
    ]

    call_command(
        "retry_failed_events",
        "--event-id",
        str(event_row.id),
        "--handler",
        "common.broken",
        "--type",
        "common.sample-happened",
    )

    target.refresh_from_db()
    assert target.status == DeliveryStatus.PENDING
    for delivery in untouched:
        delivery.refresh_from_db()
        assert delivery.status == DeliveryStatus.FAILED

    call_command("retry_failed_events", "--type", "common.other-happened")

    untouched[2].refresh_from_db()
    assert untouched[2].status == DeliveryStatus.PENDING
    still_failed = EventDelivery.objects.filter(status=DeliveryStatus.FAILED).count()
    assert still_failed == 2


def test_requires_a_filter() -> None:
    delivery = EventDeliveryFactory.create(event__sample=True, failed=True)

    with pytest.raises(CommandError):
        call_command("retry_failed_events")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.FAILED
