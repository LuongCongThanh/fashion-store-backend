"""Vòng đời Event delivery và vị từ outbox trên model (07 mục 1.1.1, 1.3)."""

from datetime import UTC, datetime, timedelta

import pytest

from shared.events.models import (
    INTERRUPTED_ERROR,
    MAX_INTERRUPTED_RUNS,
    RETRY_DELAYS,
    DeliveryStatus,
    EventDelivery,
    OutboxEvent,
    RetryOutcome,
    RunStart,
)
from shared.exceptions import DomainError
from shared.testing.factories import EventDeliveryFactory, OutboxEventFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 3, 8, 0, tzinfo=UTC)
EARLIER = NOW - timedelta(minutes=5)
LATER = NOW + timedelta(minutes=5)


class _HandlerCrashed(Exception):
    pass


class _Refused(DomainError):
    code = "REFUSED"


def _reloaded(delivery: EventDelivery) -> EventDelivery:
    return EventDelivery.objects.get(pk=delivery.pk)


def test_new_delivery_is_due_immediately() -> None:
    event = OutboxEventFactory.create()

    delivery = EventDelivery.new(event=event, handler="shared.on_sample", now=NOW)

    actual = (delivery.status, delivery.next_attempt_at, delivery.next_dispatch_at)
    assert actual == (DeliveryStatus.PENDING, NOW, NOW)


def test_is_due_requires_pending_and_attempt_time() -> None:
    due = EventDeliveryFactory.build(next_attempt_at=NOW, next_dispatch_at=LATER)
    waiting = EventDeliveryFactory.build(next_attempt_at=LATER)
    finished = EventDeliveryFactory.build(
        status=DeliveryStatus.COMPLETED, next_attempt_at=EARLIER, completed_at=EARLIER
    )

    actual = [delivery.is_due(now=NOW) for delivery in (due, waiting, finished)]
    assert actual == [True, False, False]


def test_start_run_counts_interrupted_run() -> None:
    delivery = EventDeliveryFactory.create(interrupted_runs=MAX_INTERRUPTED_RUNS - 1)

    outcome = delivery.start_run(now=NOW)

    reloaded = _reloaded(delivery)
    actual = (outcome, reloaded.status, reloaded.interrupted_runs)
    assert actual == (RunStart.STARTED, DeliveryStatus.PENDING, MAX_INTERRUPTED_RUNS)


def test_start_run_fails_at_interrupted_threshold() -> None:
    delivery = EventDeliveryFactory.create(interrupted_runs=MAX_INTERRUPTED_RUNS, attempts=2)

    outcome = delivery.start_run(now=NOW)

    reloaded = _reloaded(delivery)
    actual = (
        outcome,
        reloaded.status,
        reloaded.failed_at,
        reloaded.last_error,
        reloaded.interrupted_runs,
        reloaded.attempts,
    )
    expected = (
        RunStart.FAILED_INTERRUPTED,
        DeliveryStatus.FAILED,
        NOW,
        INTERRUPTED_ERROR,
        MAX_INTERRUPTED_RUNS,
        2,
    )
    assert actual == expected


def test_complete_resets_interrupted_runs() -> None:
    delivery = EventDeliveryFactory.create(interrupted_runs=1)

    delivery.complete(now=NOW)

    reloaded = _reloaded(delivery)
    actual = (reloaded.status, reloaded.completed_at, reloaded.interrupted_runs)
    assert actual == (DeliveryStatus.COMPLETED, NOW, 0)


def test_reject_records_error_and_resets_interrupted_runs() -> None:
    delivery = EventDeliveryFactory.create(interrupted_runs=1)

    delivery.reject(_Refused(), now=NOW)

    reloaded = _reloaded(delivery)
    actual = (
        reloaded.status,
        reloaded.completed_at,
        reloaded.last_error,
        reloaded.interrupted_runs,
    )
    expected = (DeliveryStatus.REJECTED, NOW, "_Refused(REFUSED)", 0)
    assert actual == expected


def test_retry_or_fail_schedules_next_retry() -> None:
    delivery = EventDeliveryFactory.create(attempts=1, interrupted_runs=1)

    outcome = delivery.retry_or_fail(_HandlerCrashed(), now=NOW)

    reloaded = _reloaded(delivery)
    retry_at = NOW + RETRY_DELAYS[1]
    actual = (
        outcome,
        reloaded.status,
        reloaded.attempts,
        reloaded.last_error,
        reloaded.next_attempt_at,
        reloaded.next_dispatch_at,
        reloaded.interrupted_runs,
    )
    expected = (
        RetryOutcome.SCHEDULED,
        DeliveryStatus.PENDING,
        2,
        "_HandlerCrashed",
        retry_at,
        retry_at,
        0,
    )
    assert actual == expected


def test_retry_or_fail_fails_after_last_retry() -> None:
    delivery = EventDeliveryFactory.create(
        attempts=len(RETRY_DELAYS), interrupted_runs=1, next_attempt_at=EARLIER
    )

    outcome = delivery.retry_or_fail(_HandlerCrashed(), now=NOW)

    reloaded = _reloaded(delivery)
    actual = (
        outcome,
        reloaded.status,
        reloaded.failed_at,
        reloaded.attempts,
        reloaded.last_error,
        reloaded.next_attempt_at,
        reloaded.interrupted_runs,
    )
    expected = (
        RetryOutcome.FAILED,
        DeliveryStatus.FAILED,
        NOW,
        len(RETRY_DELAYS) + 1,
        "_HandlerCrashed",
        EARLIER,
        0,
    )
    assert actual == expected


def test_fail_keeps_attempts_and_interrupted_runs() -> None:
    delivery = EventDeliveryFactory.create(attempts=2, interrupted_runs=1)

    delivery.fail(ValueError(), now=NOW)

    reloaded = _reloaded(delivery)
    actual = (
        reloaded.status,
        reloaded.failed_at,
        reloaded.last_error,
        reloaded.attempts,
        reloaded.interrupted_runs,
    )
    assert actual == (DeliveryStatus.FAILED, NOW, "ValueError", 2, 1)


def test_reopen_resets_failed_delivery() -> None:
    failed = EventDeliveryFactory.create(
        status=DeliveryStatus.FAILED,
        attempts=len(RETRY_DELAYS) + 1,
        interrupted_runs=MAX_INTERRUPTED_RUNS,
        next_attempt_at=EARLIER,
        failed_at=EARLIER,
        last_error="_HandlerCrashed",
    )
    untouched = EventDeliveryFactory.create(
        status=DeliveryStatus.FAILED, next_attempt_at=EARLIER, failed_at=EARLIER
    )

    reopened = EventDelivery.reopen([failed.id], now=NOW)

    reloaded = _reloaded(failed)
    actual = (
        reopened,
        reloaded.status,
        reloaded.attempts,
        reloaded.interrupted_runs,
        reloaded.next_attempt_at,
        reloaded.next_dispatch_at,
        reloaded.retried_at,
        reloaded.failed_at,
        reloaded.last_error,
        _reloaded(untouched).status,
    )
    expected = (
        1,
        DeliveryStatus.PENDING,
        0,
        0,
        NOW,
        NOW,
        NOW,
        EARLIER,
        "_HandlerCrashed",
        DeliveryStatus.FAILED,
    )
    assert actual == expected


def test_mark_dispatched_sets_dispatch_deadline() -> None:
    delivery = EventDeliveryFactory.create(next_attempt_at=EARLIER)

    marked = EventDelivery.mark_dispatched([delivery.id], now=NOW, next_dispatch_at=LATER)

    reloaded = _reloaded(delivery)
    actual = (
        marked,
        reloaded.next_dispatch_at,
        reloaded.last_dispatched_at,
        reloaded.next_attempt_at,
    )
    assert actual == (1, LATER, NOW, EARLIER)


def test_attempt_due_ignores_dispatch_deadline() -> None:
    due = EventDeliveryFactory.create(next_attempt_at=NOW, next_dispatch_at=LATER)
    EventDeliveryFactory.create(next_attempt_at=LATER)
    EventDeliveryFactory.create(
        status=DeliveryStatus.FAILED, next_attempt_at=EARLIER, failed_at=EARLIER
    )

    actual = list(EventDelivery.objects.attempt_due(NOW))
    assert actual == [due]


def test_dispatch_due_requires_dispatch_deadline() -> None:
    due = EventDeliveryFactory.create(next_attempt_at=EARLIER, next_dispatch_at=NOW)
    EventDeliveryFactory.create(next_attempt_at=EARLIER, next_dispatch_at=LATER)
    EventDeliveryFactory.create(next_attempt_at=LATER, next_dispatch_at=EARLIER)

    actual = list(EventDelivery.objects.dispatch_due(NOW))
    assert actual == [due]


def test_unfinished_excludes_completed_and_rejected() -> None:
    pending = EventDeliveryFactory.create()
    failed = EventDeliveryFactory.create(status=DeliveryStatus.FAILED, failed_at=NOW)
    for finished in (DeliveryStatus.COMPLETED, DeliveryStatus.REJECTED):
        EventDeliveryFactory.create(status=finished, completed_at=NOW)

    actual = set(EventDelivery.objects.unfinished())
    assert actual == {pending, failed}


def test_listed_and_unlisted_split_on_marker() -> None:
    unlisted = OutboxEventFactory.create()
    listed = OutboxEventFactory.create(deliveries_created_at=NOW)

    actual = (list(OutboxEvent.objects.unlisted()), list(OutboxEvent.objects.listed()))
    assert actual == ([unlisted], [listed])
