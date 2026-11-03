from datetime import timedelta

import pytest
import time_machine

from shared.events import delivery_lag, get_delivery_outcomes
from shared.events.models import DeliveryStatus
from shared.events.tests._helpers import NOW
from shared.testing.factories import EventDeliveryFactory, OutboxEventFactory

pytestmark = pytest.mark.django_db


@time_machine.travel(NOW, tick=False)
def test_delivery_lag_zero_without_backlog() -> None:
    assert delivery_lag() == timedelta(0)


@time_machine.travel(NOW, tick=False)
def test_delivery_lag_counts_unlisted_event_and_due_pending() -> None:
    OutboxEventFactory.create(occurred_at=NOW - timedelta(minutes=5))

    assert delivery_lag() == timedelta(minutes=5)

    EventDeliveryFactory.create(
        event=OutboxEventFactory.create(listed=True), next_attempt_at=NOW - timedelta(minutes=12)
    )

    assert delivery_lag() == timedelta(minutes=12)


@time_machine.travel(NOW, tick=False)
def test_delivery_lag_ignores_failed_finished_and_future_retry() -> None:
    overdue = NOW - timedelta(minutes=40)
    EventDeliveryFactory.create(
        event=OutboxEventFactory.create(listed=True),
        failed=True,
        next_attempt_at=overdue,
        failed_at=overdue,
    )
    for finished in (DeliveryStatus.COMPLETED, DeliveryStatus.REJECTED):
        EventDeliveryFactory.create(
            event=OutboxEventFactory.create(listed=True),
            status=finished,
            next_attempt_at=overdue,
            completed_at=overdue,
        )
    # Handler lỗi đã tự dời lượt retry; giao lại quá hạn không làm nó thành tồn đọng
    EventDeliveryFactory.create(
        event=OutboxEventFactory.create(listed=True),
        next_attempt_at=NOW + timedelta(minutes=30),
        next_dispatch_at=overdue,
    )

    assert delivery_lag() == timedelta(0)


@time_machine.travel(NOW, tick=False)
def test_get_delivery_outcomes_reports_each_requested_handler() -> None:
    event_row = OutboxEventFactory.create(listed=True)
    EventDeliveryFactory.create(event=event_row, handler="shared.waiting")
    EventDeliveryFactory.create(
        event=event_row, handler="shared.done", status=DeliveryStatus.COMPLETED, completed_at=NOW
    )
    EventDeliveryFactory.create(
        event=event_row, handler="shared.refused", status=DeliveryStatus.REJECTED, completed_at=NOW
    )
    EventDeliveryFactory.create(
        event=event_row, handler="shared.broken", failed=True, failed_at=NOW
    )
    # Cùng tên handler ở sự kiện khác không được lẫn vào kết quả
    EventDeliveryFactory.create(
        event=OutboxEventFactory.create(listed=True),
        handler="shared.absent",
        status=DeliveryStatus.COMPLETED,
        completed_at=NOW,
    )

    outcomes = get_delivery_outcomes(
        event_row.id,
        ["shared.waiting", "shared.done", "shared.refused", "shared.broken", "shared.absent"],
    )

    assert outcomes == {
        "shared.waiting": DeliveryStatus.PENDING,
        "shared.done": DeliveryStatus.COMPLETED,
        "shared.refused": DeliveryStatus.REJECTED,
        "shared.broken": DeliveryStatus.FAILED,
        "shared.absent": None,
    }
