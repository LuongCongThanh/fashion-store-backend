import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import time_machine
from django.db import DatabaseError, connection
from pydantic import model_validator
from structlog.testing import capture_logs

from shared.events import handles
from shared.events.base import DomainEvent
from shared.events.consumer import process_delivery
from shared.events.models import (
    INTERRUPTED_ERROR,
    MAX_INTERRUPTED_RUNS,
    RETRY_DELAYS,
    DeliveryStatus,
)
from shared.events.tasks import dispatch_event
from shared.events.tests.conftest import HandlerEffect, SampleHappenedV1
from shared.exceptions import DomainError, RetryLater
from shared.testing.factories import EventDeliveryFactory, OutboxEventFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 10, 30, 8, 0, tzinfo=UTC)
ORDER_CODE = "FS2610-7K3QZD"


class TransitionNotYetValid(RetryLater):
    code = "TRANSITION_NOT_YET_VALID"


class InvalidTransition(DomainError):
    code = "INVALID_TRANSITION"


class Boom(Exception):
    pass


class WorkerKilled(BaseException):
    """Giả lập worker bị kill giữa lúc handler chạy (quá time limit, hết bộ nhớ).

    Không phải `Exception` nên consumer không bắt được để lưu lỗi: transaction chạy handler
    rollback như khi process chết.
    """


def _record(effects: type[HandlerEffect], handler: str, event: SampleHappenedV1) -> None:
    effects.objects.create(handler=handler, order_code=event.order_code)


@time_machine.travel(NOW, tick=False)
def test_success_commits_effect_and_completed(
    handler_effect_table: type[HandlerEffect],
) -> None:
    received: list[SampleHappenedV1] = []

    @handles("shared.sample-happened", name="shared.record_effect")
    def record_effect(event: SampleHappenedV1) -> None:
        received.append(event)
        _record(handler_effect_table, "shared.record_effect", event)

    event_row = OutboxEventFactory.create()
    delivery = EventDeliveryFactory.create(event=event_row, handler="shared.record_effect")

    # Đi qua task Celery thật (eager trong test) như relay giao
    dispatch_event.apply_async(args=(str(event_row.id), "shared.record_effect"), queue="events")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.COMPLETED
    assert delivery.completed_at == NOW
    assert delivery.attempts == 0
    assert handler_effect_table.objects.filter(handler="shared.record_effect").count() == 1
    assert received == [
        SampleHappenedV1(
            event_id=event_row.id,
            occurred_at=NOW,
            correlation_id=None,
            order_code=ORDER_CODE,
            amount=250000,
        )
    ]


@time_machine.travel(NOW, tick=False)
def test_retry_later_keeps_pending_with_schedule(
    handler_effect_table: type[HandlerEffect],
) -> None:
    @handles("shared.sample-happened", name="shared.wait_for_source")
    def wait_for_source(event: SampleHappenedV1) -> None:
        _record(handler_effect_table, "shared.wait_for_source", event)
        raise TransitionNotYetValid

    delivery = EventDeliveryFactory.create(handler="shared.wait_for_source", attempts=2)

    process_delivery(delivery.event_id, "shared.wait_for_source")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.PENDING
    assert delivery.attempts == 3
    assert delivery.next_attempt_at == NOW + timedelta(minutes=5)
    assert delivery.next_dispatch_at == NOW + timedelta(minutes=5)
    assert delivery.last_error == "TransitionNotYetValid(TRANSITION_NOT_YET_VALID)"
    assert delivery.completed_at is None
    assert not handler_effect_table.objects.exists()


@time_machine.travel(NOW, tick=False)
def test_exception_rolls_back_handler_and_schedules_retry(
    handler_effect_table: type[HandlerEffect],
) -> None:
    @handles("shared.sample-happened", name="shared.crash")
    def crash(event: SampleHappenedV1) -> None:
        _record(handler_effect_table, "shared.crash", event)
        raise Boom("khach@example.com")

    delivery = EventDeliveryFactory.create(handler="shared.crash")

    with capture_logs() as logs:
        process_delivery(delivery.event_id, "shared.crash")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.PENDING
    assert delivery.attempts == 1
    assert delivery.next_attempt_at == NOW + RETRY_DELAYS[0]
    assert delivery.next_dispatch_at == NOW + timedelta(seconds=10)
    # Chỉ tên class, message có thể chứa PII
    assert delivery.last_error == "Boom"
    assert not handler_effect_table.objects.exists()
    assert {"event": "event_handler_error", "log_level": "error"}.items() <= logs[0].items()


@time_machine.travel(NOW, tick=False)
def test_exhausted_retries_mark_failed() -> None:
    @handles("shared.sample-happened", name="shared.never_ready")
    def never_ready(event: SampleHappenedV1) -> None:
        raise TransitionNotYetValid

    delivery = EventDeliveryFactory.create(handler="shared.never_ready", attempts=len(RETRY_DELAYS))

    with capture_logs() as logs:
        process_delivery(delivery.event_id, "shared.never_ready")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.attempts == 6
    assert delivery.failed_at == NOW
    assert delivery.last_error == "TransitionNotYetValid(TRANSITION_NOT_YET_VALID)"
    assert delivery.completed_at is None
    failed = [log for log in logs if log["event"] == "event_delivery_failed"]
    assert failed[0]["log_level"] == "error"
    assert failed[0]["handler"] == "shared.never_ready"


@time_machine.travel(NOW, tick=False)
def test_invalid_payload_fails_without_calling_handler() -> None:
    calls: list[SampleHappenedV1] = []

    @handles("shared.sample-happened", name="shared.never_called")
    def never_called(event: SampleHappenedV1) -> None:
        calls.append(event)

    # Payload cũ không còn khớp class: thiếu `amount`, `order_code` sai kiểu
    event = OutboxEventFactory.create(payload={"order_code": ["khach@example.com"]})
    delivery = EventDeliveryFactory.create(event=event, handler="shared.never_called")

    with capture_logs() as logs:
        process_delivery(delivery.event_id, "shared.never_called")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.failed_at == NOW
    assert delivery.last_error == "ValidationError"
    # Handler không chạy: không tiêu lượt retry, không tính là lần chạy dở
    counters = (delivery.attempts, delivery.interrupted_runs)
    assert counters == (0, 0)
    assert calls == []
    # Đúng một log ERROR để Sentry cảnh báo một lần cho delivery này
    errors = [log for log in logs if log["log_level"] == "error"]
    assert len(errors) == 1
    failed = [log for log in logs if log["event"] == "event_delivery_failed"]
    assert len(failed) == 1
    assert failed[0]["handler"] == "shared.never_called"
    # Chỉ tên field đã khai báo và loại lỗi, không mang input (có thể là PII)
    assert failed[0]["invalid_fields"] == [
        {"field": "order_code", "type": "string_type"},
        {"field": "amount", "type": "missing"},
    ]
    assert "exc_info" not in failed[0]
    assert "khach@example.com" not in repr(logs)


@time_machine.travel(NOW, tick=False)
def test_invalid_payload_fails_before_interrupted_runs_check() -> None:
    calls: list[SampleHappenedV1] = []

    @handles("shared.sample-happened", name="shared.never_called")
    def never_called(event: SampleHappenedV1) -> None:
        calls.append(event)

    # Đã chạm ngưỡng chạy dở, nhưng nguyên nhân gốc là payload không parse được
    event = OutboxEventFactory.create(payload={"order_code": ORDER_CODE})
    delivery = EventDeliveryFactory.create(
        event=event,
        handler="shared.never_called",
        attempts=2,
        interrupted_runs=MAX_INTERRUPTED_RUNS,
    )

    process_delivery(delivery.event_id, "shared.never_called")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.last_error == "ValidationError"
    counters = (delivery.attempts, delivery.interrupted_runs)
    assert counters == (2, MAX_INTERRUPTED_RUNS)
    assert calls == []


@pytest.mark.parametrize(
    ("event_type", "payload", "error"),
    [
        ("shared.broken-parse", {"order_code": ORDER_CODE}, "KeyError"),
        ("shared.sample-happened", ["khach@example.com"], "TypeError"),
    ],
    ids=["validator_raises", "payload_not_dict"],
)
@time_machine.travel(NOW, tick=False)
def test_non_validation_parse_error_fails_with_traceback(
    event_type: str, payload: Any, error: str
) -> None:
    class BrokenParseV1(DomainEvent):
        event_type = "shared.broken-parse"
        schema_version = 1

        order_code: str

        @model_validator(mode="before")
        @classmethod
        def _read_legacy_code(cls, data: Any) -> Any:
            # Lỗi code của class sự kiện: đọc key mà payload không có
            return {**data, "order_code": data["legacy_code"]}

    calls: list[DomainEvent] = []

    @handles(event_type, name="shared.never_called")
    def never_called(event: DomainEvent) -> None:
        calls.append(event)

    event = OutboxEventFactory.create(event_type=event_type, payload=payload)
    delivery = EventDeliveryFactory.create(event=event, handler="shared.never_called")

    with capture_logs() as logs:
        process_delivery(delivery.event_id, "shared.never_called")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.failed_at == NOW
    assert delivery.last_error == error
    # Parse là hàm thuần nên retry vô ích; handler không chạy nên bộ đếm giữ nguyên
    counters = (delivery.attempts, delivery.interrupted_runs)
    assert counters == (0, 0)
    assert calls == []
    errors = [log for log in logs if log["log_level"] == "error"]
    assert len(errors) == 1
    assert errors[0]["event"] == "event_delivery_failed"
    # Lỗi code của class sự kiện: cần traceback để sửa
    assert errors[0]["exc_info"] is True
    assert "invalid_fields" not in errors[0]


@time_machine.travel(NOW, tick=False)
def test_validation_error_inside_handler_schedules_retry() -> None:
    # Payload sự kiện hợp lệ; handler tự parse dữ liệu khác và lỗi
    @handles("shared.sample-happened", name="shared.parse_external")
    def parse_external(event: SampleHappenedV1) -> None:
        SampleHappenedV1.model_validate({"order_code": event.order_code})

    delivery = EventDeliveryFactory.create(handler="shared.parse_external")

    process_delivery(delivery.event_id, "shared.parse_external")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.PENDING
    assert delivery.attempts == 1
    assert delivery.next_attempt_at == NOW + RETRY_DELAYS[0]
    assert delivery.last_error == "ValidationError"
    assert delivery.failed_at is None


@time_machine.travel(NOW, tick=False)
def test_domain_error_rejects_without_retry(
    handler_effect_table: type[HandlerEffect],
) -> None:
    @handles("shared.sample-happened", name="shared.reject")
    def reject(event: SampleHappenedV1) -> None:
        _record(handler_effect_table, "shared.reject", event)
        raise InvalidTransition

    delivery = EventDeliveryFactory.create(handler="shared.reject")

    with capture_logs() as logs:
        process_delivery(delivery.event_id, "shared.reject")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.REJECTED
    assert delivery.completed_at == NOW
    assert delivery.attempts == 0
    assert delivery.last_error == "InvalidTransition(INVALID_TRANSITION)"
    assert not handler_effect_table.objects.exists()
    assert logs == [
        {
            "event": "event_rejected",
            "log_level": "warning",
            "event_id": str(delivery.event_id),
            "event_type": "shared.sample-happened",
            "handler": "shared.reject",
            "code": "INVALID_TRANSITION",
        }
    ]


def test_failing_handler_does_not_affect_other_handler(
    handler_effect_table: type[HandlerEffect],
) -> None:
    @handles("shared.sample-happened", name="shared.record_effect")
    def record_effect(event: SampleHappenedV1) -> None:
        _record(handler_effect_table, "shared.record_effect", event)

    @handles("shared.sample-happened", name="shared.crash")
    def crash(event: SampleHappenedV1) -> None:
        _record(handler_effect_table, "shared.crash", event)
        raise Boom

    event_row = OutboxEventFactory.create()
    ok = EventDeliveryFactory.create(event=event_row, handler="shared.record_effect")
    failing = EventDeliveryFactory.create(event=event_row, handler="shared.crash")

    # Mỗi cặp sự kiện-handler là một task riêng; thứ tự lỗi trước không ảnh hưởng
    dispatch_event.delay(str(event_row.id), "shared.crash")
    dispatch_event.delay(str(event_row.id), "shared.record_effect")

    ok.refresh_from_db()
    failing.refresh_from_db()
    assert ok.status == DeliveryStatus.COMPLETED
    assert failing.status == DeliveryStatus.PENDING
    assert failing.attempts == 1
    assert list(handler_effect_table.objects.values_list("handler", flat=True)) == [
        "shared.record_effect"
    ]


@pytest.mark.parametrize(
    "fields",
    [
        {"status": DeliveryStatus.COMPLETED, "completed_at": NOW},
        {"status": DeliveryStatus.REJECTED, "completed_at": NOW},
        {"status": DeliveryStatus.FAILED, "failed_at": NOW, "attempts": 6},
    ],
    ids=["completed", "rejected", "failed"],
)
def test_skips_finished_delivery(fields: dict[str, Any]) -> None:
    calls: list[SampleHappenedV1] = []

    @handles("shared.sample-happened", name="shared.record_call")
    def record_call(event: SampleHappenedV1) -> None:
        calls.append(event)

    delivery = EventDeliveryFactory.create(handler="shared.record_call", **fields)

    process_delivery(delivery.event_id, "shared.record_call")

    assert calls == []
    delivery.refresh_from_db()
    assert {name: getattr(delivery, name) for name in fields} == fields


@time_machine.travel(NOW, tick=False)
def test_skips_before_next_attempt_at() -> None:
    calls: list[SampleHappenedV1] = []

    @handles("shared.sample-happened", name="shared.record_call")
    def record_call(event: SampleHappenedV1) -> None:
        calls.append(event)

    retry_at = NOW + timedelta(seconds=10)
    # Task tới sớm (giao trùng hoặc relay cũ) trước hạn retry đã lưu
    delivery = EventDeliveryFactory.create(
        handler="shared.record_call",
        attempts=1,
        next_attempt_at=retry_at,
        next_dispatch_at=NOW,
    )

    process_delivery(delivery.event_id, "shared.record_call")

    assert calls == []
    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.PENDING
    assert delivery.attempts == 1
    assert delivery.next_attempt_at == retry_at


@time_machine.travel(NOW, tick=False)
def test_missing_handler_keeps_pending_without_attempt() -> None:
    delivery = EventDeliveryFactory.create(handler="shared.removed_handler")

    with capture_logs() as logs:
        process_delivery(delivery.event_id, "shared.removed_handler")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.PENDING
    assert delivery.attempts == 0
    # Handler chưa chạy nên không tính là lần chạy dở
    assert delivery.interrupted_runs == 0
    assert delivery.next_attempt_at == NOW
    assert logs[0]["event"] == "event_handler_missing"
    assert logs[0]["log_level"] == "error"


# Transaction thật thay vì savepoint: chứng minh bộ đếm đã commit trước khi worker bị kill
@pytest.mark.django_db(transaction=True)
@time_machine.travel(NOW, tick=False)
def test_interrupted_handler_fails_after_max_interrupted_runs(
    handler_effect_table: type[HandlerEffect],
) -> None:
    calls: list[SampleHappenedV1] = []

    @handles("shared.sample-happened", name="shared.killed")
    def killed(event: SampleHappenedV1) -> None:
        calls.append(event)
        _record(handler_effect_table, "shared.killed", event)
        raise WorkerKilled

    delivery = EventDeliveryFactory.create(handler="shared.killed")

    for run in range(1, MAX_INTERRUPTED_RUNS + 1):
        with pytest.raises(WorkerKilled):
            process_delivery(delivery.event_id, "shared.killed")
        delivery.refresh_from_db()
        # Bộ đếm commit trước khi handler chạy nên còn lại sau khi worker bị kill
        after_run = (delivery.status, delivery.interrupted_runs)
        assert after_run == (DeliveryStatus.PENDING, run)

    with capture_logs() as logs:
        process_delivery(delivery.event_id, "shared.killed")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.failed_at == NOW
    assert delivery.last_error == INTERRUPTED_ERROR
    assert delivery.interrupted_runs == MAX_INTERRUPTED_RUNS
    # Lần chạy dở không tiêu lượt retry: `attempts` chỉ đếm lỗi handler đã lưu được
    assert delivery.attempts == 0
    assert len(calls) == MAX_INTERRUPTED_RUNS
    assert not handler_effect_table.objects.exists()
    failed = [log for log in logs if log["event"] == "event_delivery_failed"]
    assert len(failed) == 1
    assert failed[0]["log_level"] == "error"
    assert failed[0]["handler"] == "shared.killed"
    assert failed[0]["interrupted_runs"] == MAX_INTERRUPTED_RUNS


@pytest.mark.parametrize(
    ("raised", "attempts", "status"),
    [
        (None, 0, DeliveryStatus.COMPLETED),
        (InvalidTransition, 0, DeliveryStatus.REJECTED),
        (Boom, 0, DeliveryStatus.PENDING),
        (Boom, len(RETRY_DELAYS), DeliveryStatus.FAILED),
    ],
    ids=["completed", "rejected", "retry", "failed"],
)
@time_machine.travel(NOW, tick=False)
def test_saved_outcome_resets_interrupted_runs(
    raised: type[Exception] | None, attempts: int, status: DeliveryStatus
) -> None:
    @handles("shared.sample-happened", name="shared.recovered")
    def recovered(event: SampleHappenedV1) -> None:
        if raised is not None:
            raise raised

    # Đã chạy dở sát ngưỡng; lần này handler chạy tới cùng nên consumer lưu được kết quả
    delivery = EventDeliveryFactory.create(
        handler="shared.recovered",
        attempts=attempts,
        interrupted_runs=MAX_INTERRUPTED_RUNS - 1,
    )

    process_delivery(delivery.event_id, "shared.recovered")

    delivery.refresh_from_db()
    outcome = (delivery.status, delivery.interrupted_runs)
    assert outcome == (status, 0)


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_dispatch_commits_once(
    handler_effect_table: type[HandlerEffect],
) -> None:
    calls: list[SampleHappenedV1] = []

    @handles("shared.sample-happened", name="shared.record_effect")
    def record_effect(event: SampleHappenedV1) -> None:
        calls.append(event)
        _record(handler_effect_table, "shared.record_effect", event)
        # Giữ khoá delivery đủ lâu để task trùng phải chờ tới khi commit
        time.sleep(0.2)

    delivery = EventDeliveryFactory.create(handler="shared.record_effect")
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def run() -> None:
        try:
            barrier.wait()
            process_delivery(delivery.event_id, "shared.record_effect")
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
    assert len(calls) == 1
    assert handler_effect_table.objects.count() == 1
    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.COMPLETED
    # Task trùng chen vào giữa hai transaction có thể tăng bộ đếm, nhưng kết quả lưu sau cùng
    # đặt về 0
    assert delivery.interrupted_runs == 0


HANDLER_DURATION = timedelta(seconds=30)


@pytest.mark.parametrize(
    ("raised", "expected"),
    [
        (None, {"status": DeliveryStatus.COMPLETED, "completed_at": "done"}),
        (
            InvalidTransition,
            {"status": DeliveryStatus.REJECTED, "completed_at": "done"},
        ),
        (
            Boom,
            {
                "status": DeliveryStatus.PENDING,
                "next_attempt_at": "retry",
                "next_dispatch_at": "retry",
            },
        ),
    ],
    ids=["completed", "rejected", "retry"],
)
def test_outcome_times_taken_after_handler_runs(
    raised: type[Exception] | None, expected: dict[str, Any]
) -> None:
    done = NOW + HANDLER_DURATION
    times = {"done": done, "retry": done + RETRY_DELAYS[0]}

    with time_machine.travel(NOW, tick=False) as traveller:

        @handles("shared.sample-happened", name="shared.slow")
        def slow(event: SampleHappenedV1) -> None:
            # Handler chạy lâu: mốc kết thúc và lịch retry tính từ lúc handler xong
            traveller.shift(HANDLER_DURATION)
            if raised is not None:
                raise raised

        delivery = EventDeliveryFactory.create(handler="shared.slow")
        process_delivery(delivery.event_id, "shared.slow")

    delivery.refresh_from_db()
    assert {name: getattr(delivery, name) for name in expected} == {
        name: times.get(value, value) if isinstance(value, str) else value
        for name, value in expected.items()
    }


def test_failed_at_taken_after_handler_runs() -> None:
    with time_machine.travel(NOW, tick=False) as traveller:

        @handles("shared.sample-happened", name="shared.slow")
        def slow(event: SampleHappenedV1) -> None:
            traveller.shift(HANDLER_DURATION)
            raise Boom

        delivery = EventDeliveryFactory.create(handler="shared.slow", attempts=len(RETRY_DELAYS))
        process_delivery(delivery.event_id, "shared.slow")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.failed_at == NOW + HANDLER_DURATION


@pytest.mark.django_db(transaction=True)
def test_handler_breaking_connection_rolls_back_whole_transaction() -> None:
    @handles("shared.sample-happened", name="shared.kill_connection")
    def kill_connection(event: SampleHappenedV1) -> None:
        # PostgreSQL cắt kết nối giữa lúc handler chạy: lỗi nằm ngoài savepoint của handler
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_terminate_backend(pg_backend_pid())")

    delivery = EventDeliveryFactory.create(handler="shared.kill_connection")

    try:
        with pytest.raises(DatabaseError):
            process_delivery(delivery.event_id, "shared.kill_connection")
    finally:
        # Bỏ kết nối đã chết; truy vấn sau mở kết nối mới
        connection.close()

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.PENDING
    assert delivery.attempts == 0
    assert delivery.last_error == ""
    # Bộ đếm đã commit ở transaction trước khi gọi handler nên không rollback theo
    assert delivery.interrupted_runs == 1
