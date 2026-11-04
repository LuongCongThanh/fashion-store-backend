from datetime import timedelta

import pytest
import time_machine
from django.db import transaction

from common.events import handles, publish
from common.events.models import RETRY_DELAYS, DeliveryStatus, EventDelivery
from common.events.tasks import dispatch_event
from common.events.testing import drain_events
from common.tests.conftest import HandlerEffect, SampleHappenedV1
from common.tests.events._helpers import NOW, ORDER_CODE, NotYet, record_effect

pytestmark = pytest.mark.django_db


def test_two_handlers_each_run_once_on_duplicate_dispatch(
    handler_effect_table: type[HandlerEffect],
) -> None:
    names = ("common.first_effect", "common.second_effect")
    for name in names:

        @handles("common.sample-happened", name=name)
        def record(event: SampleHappenedV1, _name: str = name) -> None:
            record_effect(handler_effect_table, _name, event)

    with transaction.atomic():
        event = SampleHappenedV1(order_code=ORDER_CODE, amount=250000)
        publish(event)

    drain_events()

    # Task bị giao lặp (broker giao lại, relay giao lại sau hạn) không chạy handler lần nữa
    for name in names:
        dispatch_event.apply_async(args=(str(event.event_id), name), queue="events")

    assert sorted(handler_effect_table.objects.values_list("handler", flat=True)) == sorted(names)
    assert set(EventDelivery.objects.values_list("status", flat=True)) == {DeliveryStatus.COMPLETED}


def test_drain_does_not_wait_for_future_retry(
    handler_effect_table: type[HandlerEffect],
) -> None:
    handler_runs = 0

    @handles("common.sample-happened", name="common.not_yet_then_ok")
    def not_yet_then_ok(event: SampleHappenedV1) -> None:
        nonlocal handler_runs
        handler_runs += 1
        if handler_runs == 1:
            raise NotYet
        record_effect(handler_effect_table, "ok", event)

    with time_machine.travel(NOW, tick=False) as traveller:
        publish(SampleHappenedV1(order_code=ORDER_CODE, amount=250000))

        # Retry chưa tới hạn: drain trả về ngay, delivery vẫn chờ
        drain_events()
        delivery = EventDelivery.objects.get()
        assert delivery.status == DeliveryStatus.PENDING
        assert handler_runs == 1

        # Tiến tới hạn retry rồi drain tiếp
        traveller.shift(RETRY_DELAYS[0] + timedelta(seconds=1))
        drain_events()

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.COMPLETED
    assert handler_effect_table.objects.count() == 1


def test_drain_runs_pending_on_commit_callbacks() -> None:
    ran: list[str] = []

    with transaction.atomic():
        transaction.on_commit(lambda: ran.append("first"))

    drain_events()
    assert ran == ["first"]

    # Callback đã chạy không chạy lại ở lần drain sau
    drain_events()
    assert ran == ["first"]


def test_drain_raises_after_max_rounds() -> None:
    # Handler tạo sự kiện mới mãi: drain phải dừng thay vì lặp vô hạn
    @handles("common.sample-happened", name="common.republish")
    def republish(event: SampleHappenedV1) -> None:
        publish(SampleHappenedV1(order_code=event.order_code, amount=event.amount))

    publish(SampleHappenedV1(order_code=ORDER_CODE, amount=250000))

    with pytest.raises(RuntimeError, match="drain_events"):
        drain_events()
