import signal
import threading
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest import mock

import pytest
import time_machine
from django.core.management import call_command
from django.db import DatabaseError, connection, transaction
from kombu.exceptions import OperationalError
from structlog.testing import capture_logs

from shared.events import handles, publish, relay
from shared.events.consumer import MAX_INTERRUPTED_RUNS
from shared.events.models import DeliveryStatus, EventDelivery, OutboxEvent
from shared.events.tasks import dispatch_event
from shared.events.tests.conftest import HandlerEffect, SampleHappenedV1
from shared.management.commands import run_outbox_relay
from shared.testing.factories import EventDeliveryFactory, OutboxEventFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 10, 30, 8, 0, tzinfo=UTC)
ORDER_CODE = "FS2610-7K3QZD"


class Rollback(Exception):
    pass


def _register_recorder(effects: type[HandlerEffect], name: str) -> None:
    @handles("shared.sample-happened", name=name)
    def record(event: SampleHappenedV1) -> None:
        effects.objects.create(handler=name, order_code=event.order_code)


def test_rolled_back_publish_creates_no_delivery() -> None:
    @handles("shared.sample-happened", name="shared.record_call")
    def record_call(event: SampleHappenedV1) -> None:
        pass

    def place_and_fail() -> None:
        with transaction.atomic():
            publish(SampleHappenedV1(order_code=ORDER_CODE, amount=250000))
            raise Rollback

    with pytest.raises(Rollback):
        place_and_fail()

    assert relay.create_deliveries() == 0
    assert not OutboxEvent.objects.exists()
    assert not EventDelivery.objects.exists()


@time_machine.travel(NOW, tick=False)
def test_create_deliveries_one_per_handler_with_marker() -> None:
    @handles("shared.sample-happened", name="shared.first")
    def first(event: SampleHappenedV1) -> None:
        pass

    @handles("shared.sample-happened", name="shared.second")
    def second(event: SampleHappenedV1) -> None:
        pass

    # Handler của bản schema khác không nhận sự kiện v1
    @handles("shared.sample-happened", version=2, name="shared.v2_only")
    def v2_only(event: SampleHappenedV1) -> None:
        pass

    event_row = OutboxEventFactory.create()

    assert relay.create_deliveries() == 1

    event_row.refresh_from_db()
    assert event_row.deliveries_created_at == NOW
    deliveries = EventDelivery.objects.filter(event=event_row).order_by("handler")
    assert [
        (d.handler, d.status, d.attempts, d.next_attempt_at, d.next_dispatch_at) for d in deliveries
    ] == [
        ("shared.first", DeliveryStatus.PENDING, 0, NOW, NOW),
        ("shared.second", DeliveryStatus.PENDING, 0, NOW, NOW),
    ]
    # Sự kiện đã có marker không bị lập danh sách lại
    assert relay.create_deliveries() == 0
    assert EventDelivery.objects.count() == 2


@time_machine.travel(NOW, tick=False)
def test_event_without_handlers_gets_marker() -> None:
    event_row = OutboxEventFactory.create()

    with capture_logs() as logs:
        assert relay.create_deliveries() == 1

    event_row.refresh_from_db()
    assert event_row.deliveries_created_at == NOW
    assert not EventDelivery.objects.exists()
    assert {
        "event": "outbox_event_no_handlers",
        "event_id": str(event_row.id),
        "event_type": "shared.sample-happened",
        "schema_version": 1,
    }.items() <= logs[0].items()


@pytest.mark.django_db(transaction=True)
def test_two_relays_concurrently_create_no_duplicates() -> None:
    for name in ("shared.first", "shared.second"):
        handles("shared.sample-happened", name=name)(lambda event: None)
    events = OutboxEventFactory.create_batch(30)
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def run() -> None:
        try:
            barrier.wait()
            # Batch nhỏ để hai relay cùng quét nhiều vòng trên cùng tập sự kiện
            while relay.create_deliveries(batch=5):
                pass
        except BaseException as exc:
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert not OutboxEvent.objects.filter(deliveries_created_at__isnull=True).exists()
    assert EventDelivery.objects.count() == len(events) * 2
    pairs = set(EventDelivery.objects.values_list("event_id", "handler"))
    assert pairs == {
        (event.id, name) for event in events for name in ("shared.first", "shared.second")
    }


def test_lost_task_redispatched_after_deadline(
    handler_effect_table: type[HandlerEffect],
) -> None:
    _register_recorder(handler_effect_table, "shared.record_effect")
    with time_machine.travel(NOW, tick=False) as traveller:
        publish(SampleHappenedV1(order_code=ORDER_CODE, amount=250000))
        relay.create_deliveries()
        # Delivery đã thử lỗi hai lần trước đó: giao lại không được reset bộ đếm
        EventDelivery.objects.update(attempts=2)

        # Broker nhận task rồi mất: lần giao đầu không tới worker
        with mock.patch.object(dispatch_event, "apply_async") as lost:
            assert relay.dispatch_due() == 1
            lost.assert_called_once()
            delivery = EventDelivery.objects.get()
            assert delivery.next_dispatch_at == NOW + relay.REDISPATCH_AFTER
            assert delivery.last_dispatched_at == NOW
            assert delivery.status == DeliveryStatus.PENDING

            # Chưa tới hạn giao lại thì relay không giao trùng
            traveller.shift(timedelta(minutes=2))
            assert relay.dispatch_due() == 0
            lost.assert_called_once()

        traveller.shift(timedelta(minutes=1, seconds=1))
        assert relay.dispatch_due() == 1

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.COMPLETED
    # Task mất không tiêu lượt retry và không reset lượt đã tiêu
    assert delivery.attempts == 2
    assert handler_effect_table.objects.count() == 1


def test_lost_tasks_do_not_count_as_interrupted_runs(
    handler_effect_table: type[HandlerEffect],
) -> None:
    _register_recorder(handler_effect_table, "shared.record_effect")
    with time_machine.travel(NOW, tick=False) as traveller:
        delivery = EventDeliveryFactory.create(handler="shared.record_effect", attempts=2)

        # Redis mất task nhiều lần hơn ngưỡng chạy dở: không task nào tới consumer
        with mock.patch.object(dispatch_event, "apply_async") as lost:
            for _ in range(MAX_INTERRUPTED_RUNS + 1):
                assert relay.dispatch_due() == 1
                traveller.shift(relay.REDISPATCH_AFTER)
        assert lost.call_count == MAX_INTERRUPTED_RUNS + 1

        delivery.refresh_from_db()
        after_lost = (delivery.status, delivery.attempts, delivery.interrupted_runs)
        assert after_lost == (DeliveryStatus.PENDING, 2, 0)

        # Task tới được worker thì handler vẫn chạy, không bị chuyển `failed`
        assert relay.dispatch_due() == 1

    delivery.refresh_from_db()
    after_run = (delivery.status, delivery.attempts, delivery.interrupted_runs)
    assert after_run == (DeliveryStatus.COMPLETED, 2, 0)
    assert handler_effect_table.objects.count() == 1


@time_machine.travel(NOW, tick=False)
def test_broker_error_keeps_delivery_for_later() -> None:
    deliveries = [EventDeliveryFactory.create(handler=f"shared.record_{n}") for n in range(3)]

    with (
        mock.patch.object(
            dispatch_event, "apply_async", side_effect=OperationalError("broker down")
        ) as apply_async,
        capture_logs() as logs,
    ):
        assert relay.dispatch_due() == 3

    # Broker lỗi thì dừng lô: các delivery còn lại đã có hạn giao lại
    apply_async.assert_called_once()
    (args,) = apply_async.call_args.kwargs.values()
    first = next(d for d in deliveries if (str(d.event_id), d.handler) == args)
    for delivery in deliveries:
        delivery.refresh_from_db()
        assert delivery.status == DeliveryStatus.PENDING
        assert delivery.attempts == 0
        assert delivery.last_error == ""
        # Hạn giao lại đã commit trước khi gọi broker: relay thử lại sau hạn
        assert delivery.next_dispatch_at == NOW + relay.REDISPATCH_AFTER
    failed = [log for log in logs if log["event"] == "outbox_dispatch_failed"]
    assert len(failed) == 1
    assert failed[0]["log_level"] == "warning"
    assert failed[0]["handler"] == first.handler
    assert failed[0]["event_id"] == str(first.event_id)
    assert failed[0]["deferred"] == 3


@time_machine.travel(NOW, tick=False)
def test_dispatch_programming_error_not_swallowed() -> None:
    EventDeliveryFactory.create()

    with (
        mock.patch.object(dispatch_event, "apply_async", side_effect=TypeError("bad args")),
        pytest.raises(TypeError),
    ):
        relay.dispatch_due()


def test_dispatch_event_routed_to_events_queue() -> None:
    # Relay không truyền queue: decorator của task định tuyến vào queue `events` (07 mục 3.1)
    assert dispatch_event.queue == "events"  # type: ignore[attr-defined]  # celery-types thiếu Task.queue


@time_machine.travel(NOW, tick=False)
def test_dispatch_skips_retry_not_due() -> None:
    later = NOW + timedelta(seconds=10)
    due = EventDeliveryFactory.create()
    skipped = [
        EventDeliveryFactory.create(attempts=1, next_attempt_at=later, next_dispatch_at=NOW),
        EventDeliveryFactory.create(next_attempt_at=NOW, next_dispatch_at=later),
        EventDeliveryFactory.create(status=DeliveryStatus.COMPLETED, completed_at=NOW),
        EventDeliveryFactory.create(status=DeliveryStatus.FAILED, failed_at=NOW, attempts=6),
    ]

    with mock.patch.object(dispatch_event, "apply_async") as apply_async:
        assert relay.dispatch_due() == 1

    apply_async.assert_called_once_with(args=(str(due.event_id), due.handler))
    # Delivery chưa tới hạn hoặc đã kết thúc giữ nguyên hạn giao
    for delivery in skipped:
        before = delivery.next_dispatch_at
        delivery.refresh_from_db()
        assert delivery.next_dispatch_at == before
        assert delivery.last_dispatched_at is None


@time_machine.travel(NOW, tick=False)
def test_run_outbox_relay_once(handler_effect_table: type[HandlerEffect]) -> None:
    _register_recorder(handler_effect_table, "shared.first")
    _register_recorder(handler_effect_table, "shared.second")
    publish(SampleHappenedV1(order_code=ORDER_CODE, amount=250000))

    call_command("run_outbox_relay", "--once")

    assert set(EventDelivery.objects.values_list("handler", "status")) == {
        ("shared.first", DeliveryStatus.COMPLETED),
        ("shared.second", DeliveryStatus.COMPLETED),
    }
    assert sorted(handler_effect_table.objects.values_list("handler", flat=True)) == [
        "shared.first",
        "shared.second",
    ]


@pytest.mark.django_db(transaction=True)
def test_run_outbox_relay_survives_iteration_error() -> None:
    # transaction=True: kết nối ở autocommit như tiến trình relay thật, nên việc dọn kết nối
    # sau lỗi không đóng transaction của test
    handled: list[str] = []

    @handles("shared.sample-happened", name="shared.record_call")
    def record_call(event: SampleHappenedV1) -> None:
        handled.append(event.order_code)

    with transaction.atomic():
        publish(SampleHappenedV1(order_code=ORDER_CODE, amount=250000))

    real_create = relay.create_deliveries
    real_dispatch = relay.dispatch_due
    create_calls = 0
    dispatch_calls = 0
    signal_handlers: dict[int, Callable[..., Any]] = {}

    def create_fails_first(batch: int = 100) -> int:
        nonlocal create_calls
        create_calls += 1
        if create_calls == 1:
            raise DatabaseError("db down")
        return real_create(batch)

    def dispatch_then_stop(batch: int = 100) -> int:
        nonlocal dispatch_calls
        dispatch_calls += 1
        result = real_dispatch(batch)
        if dispatch_calls == 2:
            # Như Ctrl+C sau vòng thứ hai
            signal_handlers[signal.SIGINT](signal.SIGINT, None)
        return result

    def capture_signal(signum: int, handler: Callable[..., Any]) -> None:
        signal_handlers[signum] = handler

    with (
        mock.patch.object(relay, "create_deliveries", side_effect=create_fails_first),
        mock.patch.object(relay, "dispatch_due", side_effect=dispatch_then_stop),
        mock.patch.object(run_outbox_relay, "INTERVAL_SECONDS", 0),
        mock.patch.object(run_outbox_relay.signal, "signal", side_effect=capture_signal),
        capture_logs() as logs,
    ):
        call_command("run_outbox_relay")

    # Vòng 1: lập danh sách lỗi nhưng bước giao vẫn chạy; vòng 2: lập danh sách rồi giao được
    assert (create_calls, dispatch_calls) == (2, 2)
    assert handled == [ORDER_CODE]
    assert EventDelivery.objects.get().status == DeliveryStatus.COMPLETED
    failed = [log for log in logs if log["event"] == "outbox_relay_iteration_failed"]
    assert len(failed) == 1
    assert failed[0]["log_level"] == "error"
    assert failed[0]["step"] == "create_deliveries"


@pytest.mark.django_db(transaction=True)
def test_run_outbox_relay_create_error_does_not_block_dispatch() -> None:
    EventDeliveryFactory.create()

    with (
        mock.patch.object(relay, "create_deliveries", side_effect=DatabaseError("db down")),
        mock.patch.object(dispatch_event, "apply_async") as apply_async,
        capture_logs(),
    ):
        call_command("run_outbox_relay", "--once")

    apply_async.assert_called_once()


@pytest.mark.django_db(transaction=True)
def test_deadline_committed_before_enqueue_and_redispatched_after_relay_crash() -> None:
    handled: list[str] = []

    @handles("shared.sample-happened", name="shared.record_call")
    def record_call(event: SampleHappenedV1) -> None:
        handled.append(event.order_code)

    with time_machine.travel(NOW, tick=False) as traveller:
        delivery = EventDeliveryFactory.create(handler="shared.record_call")
        seen: list[tuple[bool, datetime, datetime | None]] = []

        def crash_before_enqueue(*args: Any, **kwargs: Any) -> None:
            # Đọc trạng thái lúc gọi broker: transaction của relay đã đóng và đã commit
            stored = EventDelivery.objects.get(id=delivery.id)
            seen.append(
                (connection.in_atomic_block, stored.next_dispatch_at, stored.last_dispatched_at)
            )
            raise RuntimeError("relay killed")

        with (
            mock.patch.object(dispatch_event, "apply_async", side_effect=crash_before_enqueue),
            pytest.raises(RuntimeError),
        ):
            relay.dispatch_due()

        assert seen == [(False, NOW + relay.REDISPATCH_AFTER, NOW)]
        assert handled == []

        # Chưa tới hạn thì không giao; quá hạn thì relay giao lại
        traveller.shift(relay.REDISPATCH_AFTER - timedelta(seconds=1))
        assert relay.dispatch_due() == 0
        traveller.shift(timedelta(seconds=2))
        assert relay.dispatch_due() == 1

    assert handled == [ORDER_CODE]
    assert EventDelivery.objects.get(id=delivery.id).status == DeliveryStatus.COMPLETED


@pytest.mark.django_db(transaction=True)
def test_two_relays_concurrently_dispatch_each_delivery_once() -> None:
    deliveries = EventDeliveryFactory.create_batch(30)
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []
    lock = threading.Lock()
    dispatched: Counter[tuple[str, str]] = Counter()

    def record(*, args: tuple[str, str]) -> None:
        with lock:
            dispatched[args] += 1

    def run() -> None:
        try:
            barrier.wait()
            # Batch nhỏ để hai relay cùng quét nhiều vòng trên cùng tập delivery
            while relay.dispatch_due(batch=5):
                pass
        except BaseException as exc:
            errors.append(exc)
        finally:
            connection.close()

    with mock.patch.object(dispatch_event, "apply_async", side_effect=record):
        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert errors == []
    assert dispatched == Counter({(str(d.event_id), d.handler): 1 for d in deliveries})
