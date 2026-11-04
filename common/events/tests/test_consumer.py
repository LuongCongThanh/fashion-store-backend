import time
from datetime import timedelta
from typing import Any

import pytest
import time_machine
from django.db import DatabaseError, connection
from pydantic import model_validator
from structlog.testing import capture_logs

from common.events import handles
from common.events.base import DomainEvent
from common.events.consumer import process_delivery
from common.events.models import (
    INTERRUPTED_ERROR,
    MAX_INTERRUPTED_RUNS,
    RETRY_DELAYS,
    DeliveryStatus,
)
from common.events.tasks import dispatch_event
from common.events.tests._helpers import (
    NOW,
    ORDER_CODE,
    Boom,
    NotYet,
    Refused,
    WorkerKilled,
    record_effect,
    run_concurrently,
)
from common.events.tests.conftest import HandlerEffect, SampleHappenedV1
from common.tests.factories import EventDeliveryFactory, OutboxEventFactory

pytestmark = pytest.mark.django_db


@time_machine.travel(NOW, tick=False)
def test_success_commits_effect_and_completed(
    handler_effect_table: type[HandlerEffect],
) -> None:
    received: list[SampleHappenedV1] = []

    @handles("common.sample-happened", name="common.record_effect")
    def record(event: SampleHappenedV1) -> None:
        received.append(event)
        record_effect(handler_effect_table, "common.record_effect", event)

    event_row = OutboxEventFactory.create(sample=True)
    delivery = EventDeliveryFactory.create(event=event_row, handler="common.record_effect")

    # Đi qua task Celery thật (eager trong test) như relay giao
    dispatch_event.apply_async(args=(str(event_row.id), "common.record_effect"), queue="events")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.COMPLETED
    assert delivery.completed_at == NOW
    assert delivery.attempts == 0
    assert handler_effect_table.objects.filter(handler="common.record_effect").count() == 1
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
def test_retry_later_rolls_back_and_keeps_pending(
    handler_effect_table: type[HandlerEffect],
) -> None:
    @handles("common.sample-happened", name="common.wait_for_source")
    def wait_for_source(event: SampleHappenedV1) -> None:
        record_effect(handler_effect_table, "common.wait_for_source", event)
        raise NotYet

    delivery = EventDeliveryFactory.create(
        event__sample=True, handler="common.wait_for_source", attempts=2
    )

    process_delivery(delivery.event_id, "common.wait_for_source")

    delivery.refresh_from_db()
    # Lịch retry theo `attempts`: test_models.py::test_retry_or_fail_schedules_next_retry
    assert delivery.status == DeliveryStatus.PENDING
    assert delivery.last_error == "NotYet(NOT_YET)"
    assert delivery.completed_at is None
    assert not handler_effect_table.objects.exists()


@time_machine.travel(NOW, tick=False)
def test_exception_rolls_back_handler_and_keeps_pending(
    handler_effect_table: type[HandlerEffect],
) -> None:
    @handles("common.sample-happened", name="common.crash")
    def crash(event: SampleHappenedV1) -> None:
        record_effect(handler_effect_table, "common.crash", event)
        raise Boom("khach@example.com")

    delivery = EventDeliveryFactory.create(event__sample=True, handler="common.crash")

    with capture_logs() as logs:
        process_delivery(delivery.event_id, "common.crash")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.PENDING
    # Chỉ tên class, message có thể chứa PII
    assert delivery.last_error == "Boom"
    assert not handler_effect_table.objects.exists()
    assert {"event": "event_handler_error", "log_level": "error"}.items() <= logs[0].items()


@time_machine.travel(NOW, tick=False)
def test_exhausted_retries_mark_failed() -> None:
    @handles("common.sample-happened", name="common.never_ready")
    def never_ready(event: SampleHappenedV1) -> None:
        raise NotYet

    delivery = EventDeliveryFactory.create(
        event__sample=True, handler="common.never_ready", attempts=len(RETRY_DELAYS)
    )

    with capture_logs() as logs:
        process_delivery(delivery.event_id, "common.never_ready")

    delivery.refresh_from_db()
    # Cột ghi khi hết lượt: test_models.py::test_retry_or_fail_fails_after_last_retry
    assert delivery.status == DeliveryStatus.FAILED
    failed = [log for log in logs if log["event"] == "event_delivery_failed"]
    assert failed[0]["log_level"] == "error"
    assert failed[0]["handler"] == "common.never_ready"


@time_machine.travel(NOW, tick=False)
def test_invalid_payload_fails_without_calling_handler() -> None:
    calls: list[SampleHappenedV1] = []

    @handles("common.sample-happened", name="common.never_called")
    def never_called(event: SampleHappenedV1) -> None:
        calls.append(event)

    # Payload cũ không còn khớp class: thiếu `amount`, `order_code` sai kiểu
    event = OutboxEventFactory.create(sample=True, payload={"order_code": ["khach@example.com"]})
    delivery = EventDeliveryFactory.create(event=event, handler="common.never_called")

    with capture_logs() as logs:
        process_delivery(delivery.event_id, "common.never_called")

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
    assert failed[0]["handler"] == "common.never_called"
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

    @handles("common.sample-happened", name="common.never_called")
    def never_called(event: SampleHappenedV1) -> None:
        calls.append(event)

    # Đã chạm ngưỡng chạy dở, nhưng nguyên nhân gốc là payload không parse được
    event = OutboxEventFactory.create(sample=True, payload={"order_code": ORDER_CODE})
    delivery = EventDeliveryFactory.create(
        event=event,
        handler="common.never_called",
        attempts=2,
        interrupted_runs=MAX_INTERRUPTED_RUNS,
    )

    process_delivery(delivery.event_id, "common.never_called")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.last_error == "ValidationError"
    counters = (delivery.attempts, delivery.interrupted_runs)
    assert counters == (2, MAX_INTERRUPTED_RUNS)
    assert calls == []


@pytest.mark.parametrize(
    ("event_type", "payload", "error"),
    [
        ("common.broken-parse", {"order_code": ORDER_CODE}, "KeyError"),
        ("common.sample-happened", ["khach@example.com"], "TypeError"),
    ],
    ids=["validator_raises", "payload_not_dict"],
)
@time_machine.travel(NOW, tick=False)
def test_non_validation_parse_error_fails_with_traceback(
    event_type: str, payload: Any, error: str
) -> None:
    class BrokenParseV1(DomainEvent):
        event_type = "common.broken-parse"
        schema_version = 1

        order_code: str

        @model_validator(mode="before")
        @classmethod
        def _read_legacy_code(cls, data: Any) -> Any:
            # Lỗi code của class sự kiện: đọc key mà payload không có
            return {**data, "order_code": data["legacy_code"]}

    calls: list[DomainEvent] = []

    @handles(event_type, name="common.never_called")
    def never_called(event: DomainEvent) -> None:
        calls.append(event)

    event = OutboxEventFactory.create(event_type=event_type, payload=payload)
    delivery = EventDeliveryFactory.create(event=event, handler="common.never_called")

    with capture_logs() as logs:
        process_delivery(delivery.event_id, "common.never_called")

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
    @handles("common.sample-happened", name="common.parse_external")
    def parse_external(event: SampleHappenedV1) -> None:
        SampleHappenedV1.model_validate({"order_code": event.order_code})

    delivery = EventDeliveryFactory.create(event__sample=True, handler="common.parse_external")

    process_delivery(delivery.event_id, "common.parse_external")

    delivery.refresh_from_db()
    # Lỗi trong handler đi đường retry, không phải lỗi parse payload
    assert delivery.status == DeliveryStatus.PENDING
    assert delivery.last_error == "ValidationError"
    assert delivery.failed_at is None


@time_machine.travel(NOW, tick=False)
def test_domain_error_rejects_without_retry(
    handler_effect_table: type[HandlerEffect],
) -> None:
    @handles("common.sample-happened", name="common.reject")
    def reject(event: SampleHappenedV1) -> None:
        record_effect(handler_effect_table, "common.reject", event)
        raise Refused

    delivery = EventDeliveryFactory.create(event__sample=True, handler="common.reject")

    with capture_logs() as logs:
        process_delivery(delivery.event_id, "common.reject")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.REJECTED
    assert delivery.completed_at == NOW
    assert delivery.attempts == 0
    assert delivery.last_error == "Refused(REFUSED)"
    assert not handler_effect_table.objects.exists()
    assert logs == [
        {
            "event": "event_rejected",
            "log_level": "warning",
            "event_id": str(delivery.event_id),
            "event_type": "common.sample-happened",
            "handler": "common.reject",
            "code": "REFUSED",
        }
    ]


def test_failing_handler_does_not_affect_other_handler(
    handler_effect_table: type[HandlerEffect],
) -> None:
    @handles("common.sample-happened", name="common.record_effect")
    def record(event: SampleHappenedV1) -> None:
        record_effect(handler_effect_table, "common.record_effect", event)

    @handles("common.sample-happened", name="common.crash")
    def crash(event: SampleHappenedV1) -> None:
        record_effect(handler_effect_table, "common.crash", event)
        raise Boom

    event_row = OutboxEventFactory.create(sample=True)
    ok = EventDeliveryFactory.create(event=event_row, handler="common.record_effect")
    failing = EventDeliveryFactory.create(event=event_row, handler="common.crash")

    # Mỗi cặp sự kiện-handler là một task riêng; thứ tự lỗi trước không ảnh hưởng
    dispatch_event.delay(str(event_row.id), "common.crash")
    dispatch_event.delay(str(event_row.id), "common.record_effect")

    ok.refresh_from_db()
    failing.refresh_from_db()
    assert ok.status == DeliveryStatus.COMPLETED
    assert failing.status == DeliveryStatus.PENDING
    assert failing.attempts == 1
    assert list(handler_effect_table.objects.values_list("handler", flat=True)) == [
        "common.record_effect"
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

    @handles("common.sample-happened", name="common.record_call")
    def record_call(event: SampleHappenedV1) -> None:
        calls.append(event)

    delivery = EventDeliveryFactory.create(
        event__sample=True, handler="common.record_call", **fields
    )

    process_delivery(delivery.event_id, "common.record_call")

    assert calls == []
    delivery.refresh_from_db()
    assert {name: getattr(delivery, name) for name in fields} == fields


@time_machine.travel(NOW, tick=False)
def test_skips_before_next_attempt_at() -> None:
    calls: list[SampleHappenedV1] = []

    @handles("common.sample-happened", name="common.record_call")
    def record_call(event: SampleHappenedV1) -> None:
        calls.append(event)

    retry_at = NOW + timedelta(seconds=10)
    # Task tới sớm (giao trùng hoặc relay cũ) trước hạn retry đã lưu
    delivery = EventDeliveryFactory.create(
        event__sample=True,
        handler="common.record_call",
        attempts=1,
        next_attempt_at=retry_at,
        next_dispatch_at=NOW,
    )

    process_delivery(delivery.event_id, "common.record_call")

    assert calls == []
    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.PENDING
    assert delivery.attempts == 1
    assert delivery.next_attempt_at == retry_at


@time_machine.travel(NOW, tick=False)
def test_missing_handler_keeps_pending_without_attempt() -> None:
    delivery = EventDeliveryFactory.create(event__sample=True, handler="common.removed_handler")

    with capture_logs() as logs:
        process_delivery(delivery.event_id, "common.removed_handler")

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

    @handles("common.sample-happened", name="common.killed")
    def killed(event: SampleHappenedV1) -> None:
        calls.append(event)
        record_effect(handler_effect_table, "common.killed", event)
        raise WorkerKilled

    delivery = EventDeliveryFactory.create(event__sample=True, handler="common.killed")

    for run in range(1, MAX_INTERRUPTED_RUNS + 1):
        with pytest.raises(WorkerKilled):
            process_delivery(delivery.event_id, "common.killed")
        delivery.refresh_from_db()
        # Bộ đếm commit trước khi handler chạy nên còn lại sau khi worker bị kill
        after_run = (delivery.status, delivery.interrupted_runs)
        assert after_run == (DeliveryStatus.PENDING, run)

    with capture_logs() as logs:
        process_delivery(delivery.event_id, "common.killed")

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
    assert failed[0]["handler"] == "common.killed"
    assert failed[0]["interrupted_runs"] == MAX_INTERRUPTED_RUNS


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_dispatch_commits_once(
    handler_effect_table: type[HandlerEffect],
) -> None:
    calls: list[SampleHappenedV1] = []

    @handles("common.sample-happened", name="common.record_effect")
    def record(event: SampleHappenedV1) -> None:
        calls.append(event)
        record_effect(handler_effect_table, "common.record_effect", event)
        # Giữ khoá delivery đủ lâu để task trùng phải chờ tới khi commit
        time.sleep(0.2)

    delivery = EventDeliveryFactory.create(event__sample=True, handler="common.record_effect")
    errors = run_concurrently(lambda: process_delivery(delivery.event_id, "common.record_effect"))

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
            Refused,
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

        @handles("common.sample-happened", name="common.slow")
        def slow(event: SampleHappenedV1) -> None:
            # Handler chạy lâu: mốc kết thúc và lịch retry tính từ lúc handler xong
            traveller.shift(HANDLER_DURATION)
            if raised is not None:
                raise raised

        delivery = EventDeliveryFactory.create(event__sample=True, handler="common.slow")
        process_delivery(delivery.event_id, "common.slow")

    delivery.refresh_from_db()
    assert {name: getattr(delivery, name) for name in expected} == {
        name: times.get(value, value) if isinstance(value, str) else value
        for name, value in expected.items()
    }


def test_failed_at_taken_after_handler_runs() -> None:
    with time_machine.travel(NOW, tick=False) as traveller:

        @handles("common.sample-happened", name="common.slow")
        def slow(event: SampleHappenedV1) -> None:
            traveller.shift(HANDLER_DURATION)
            raise Boom

        delivery = EventDeliveryFactory.create(
            event__sample=True, handler="common.slow", attempts=len(RETRY_DELAYS)
        )
        process_delivery(delivery.event_id, "common.slow")

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.FAILED
    assert delivery.failed_at == NOW + HANDLER_DURATION


@pytest.mark.django_db(transaction=True)
def test_handler_breaking_connection_rolls_back_whole_transaction() -> None:
    @handles("common.sample-happened", name="common.kill_connection")
    def kill_connection(event: SampleHappenedV1) -> None:
        # PostgreSQL cắt kết nối giữa lúc handler chạy: lỗi nằm ngoài savepoint của handler
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_terminate_backend(pg_backend_pid())")

    delivery = EventDeliveryFactory.create(event__sample=True, handler="common.kill_connection")

    try:
        with pytest.raises(DatabaseError):
            process_delivery(delivery.event_id, "common.kill_connection")
    finally:
        # Bỏ kết nối đã chết; truy vấn sau mở kết nối mới
        connection.close()

    delivery.refresh_from_db()
    assert delivery.status == DeliveryStatus.PENDING
    assert delivery.attempts == 0
    assert delivery.last_error == ""
    # Bộ đếm đã commit ở transaction trước khi gọi handler nên không rollback theo
    assert delivery.interrupted_runs == 1
