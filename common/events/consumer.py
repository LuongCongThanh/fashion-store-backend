"""Consumer: chạy một handler cho một sự kiện và ghi kết quả lên delivery (07 mục 1.1.1, 1.3).

Mỗi lần xử lý gồm hai transaction cùng khoá dòng delivery. Transaction đầu parse payload rồi
ghi nhận lần chạy (`interrupted_runs`) và commit, vì worker bị kill (quá time limit, hết bộ nhớ)
giữa lúc handler chạy thì không còn cơ hội ghi lỗi; không có bộ đếm này relay sẽ giao lại vô
hạn. Payload không parse được thì delivery `failed` ngay ở transaction này, handler không chạy.
Transaction sau chạy handler trong savepoint, nên tác động DB của handler và trạng thái
`completed`/`rejected` commit cùng nhau. Task giao trùng chờ khoá rồi thấy delivery đã kết thúc
thì bỏ qua.
"""

from uuid import UUID

import structlog
from django.db import transaction
from django.utils import timezone
from pydantic import ValidationError

from common.events.models import EventDelivery, RetryOutcome, RunStart
from common.events.registry import registry
from common.exceptions import DomainError, RetryLater

logger = structlog.get_logger(__name__)


def process_delivery(event_id: UUID | str, handler_name: str) -> None:
    """Xử lý delivery `(event_id, handler_name)` nếu còn `pending` và đã tới hạn retry.

    Hai transaction. Transaction 1 parse payload, ghi lần chạy (`EventDelivery.start_run`) rồi
    commit trước khi gọi handler; chuyển `failed` ngay khi payload không parse được hoặc bộ đếm
    chạy dở đã chạm ngưỡng. Transaction 2 khoá lại,
    chạy handler và lưu kết quả. Worker bị kill giữa transaction 2 hay `DatabaseError` ngoài
    savepoint của handler (kết nối hỏng) làm transaction 2 rollback nhưng bộ đếm đã commit vẫn
    còn; relay giao lại theo `next_dispatch_at` đã lưu.
    """
    # Task Celery truyền chuỗi; chuẩn hoá về UUID đúng kiểu của khoá ngoại
    event_uuid = event_id if isinstance(event_id, UUID) else UUID(event_id)
    with transaction.atomic():
        delivery = _lock_delivery(event_uuid, handler_name)
        if delivery is None:
            # Sự kiện đã bị purge hoặc task mang tham số sai: không còn việc để làm
            logger.warning("event_delivery_missing", event_id=str(event_id), handler=handler_name)
            return
        if not delivery.is_due(now=timezone.now()):
            return

        event_row = delivery.event
        log = logger.bind(
            event_id=str(event_row.id), event_type=event_row.event_type, handler=handler_name
        )
        handler = registry.get_handler(handler_name)
        event_class = registry.get_event_class(event_row.event_type, event_row.schema_version)
        if handler is None or event_class is None:
            # Lỗi cấu hình/deploy, không phải lỗi handler: giữ `pending`, không tiêu lượt retry
            # và không tính là lần chạy dở vì handler chưa chạy
            log.error("event_handler_missing", schema_version=event_row.schema_version)
            return
        # Parse là hàm thuần: lần nào cũng lỗi như nhau nên retry vô ích, và lỗi thoát khỏi
        # transaction này thì không bộ đếm nào được ghi, relay giao lại vô hạn. Handler chưa
        # chạy nên không tính lần chạy dở và không tiêu lượt retry
        try:
            event = event_class.model_validate(
                {
                    **event_row.payload,
                    "event_id": event_row.id,
                    "occurred_at": event_row.occurred_at,
                }
            )
        except ValidationError as exc:
            # Payload cũ không còn khớp class (trái quy tắc nâng version, 07 mục 2)
            delivery.fail(exc, now=timezone.now())
            _log_failed(log, delivery, invalid_fields=_invalid_fields(exc))
            return
        except Exception as exc:
            # Lỗi code của class sự kiện (validator ném lỗi) hoặc payload không phải dict:
            # traceback chỉ đi vào log
            delivery.fail(exc, now=timezone.now())
            _log_failed(log, delivery, exc_info=True)
            return
        # Commit trước khi gọi handler: process bị kill thì không còn cơ hội ghi gì nữa
        if delivery.start_run(now=timezone.now()) is RunStart.FAILED_INTERRUPTED:
            # Handler liên tục làm worker chết (quá time limit, hết bộ nhớ): dừng giao lại vô hạn
            _log_failed(log, delivery, interrupted_runs=delivery.interrupted_runs)
            return

    with transaction.atomic():
        # Khoá lại theo khoá chính; sự kiện không đổi nên dùng tiếp `handler` và `event` đã
        # parse ở transaction 1 thay vì join lại
        delivery = EventDelivery.objects.select_for_update().filter(pk=delivery.pk).first()
        # Task trùng có thể đã lưu kết quả trong lúc khoá được nhả giữa hai transaction
        if delivery is None or not delivery.is_due(now=timezone.now()):
            return
        try:
            with transaction.atomic():
                handler.func(event)
        # Mốc kết thúc và lịch retry tính từ lúc handler xong, không phải lúc khoá delivery
        except DomainError as exc:
            delivery.reject(exc, now=timezone.now())
            log.warning("event_rejected", code=exc.code)
        except RetryLater as exc:
            _record_handler_error(log, delivery, exc)
        except Exception as exc:
            # Traceback chỉ đi vào log; `last_error` không mang message (03 mục 1.4)
            log.exception("event_handler_error")
            _record_handler_error(log, delivery, exc)
        else:
            delivery.complete(now=timezone.now())


def _lock_delivery(event_uuid: UUID, handler_name: str) -> EventDelivery | None:
    return (
        EventDelivery.objects.select_for_update(of=("self",))
        .select_related("event")
        .filter(event_id=event_uuid, handler=handler_name)
        .first()
    )


def _record_handler_error(
    log: structlog.stdlib.BoundLogger, delivery: EventDelivery, exc: Exception
) -> None:
    if delivery.retry_or_fail(exc, now=timezone.now()) is RetryOutcome.FAILED:
        _log_failed(log, delivery, attempts=delivery.attempts)
        return
    log.info("event_retry_scheduled", attempts=delivery.attempts, retry_at=delivery.next_attempt_at)


def _log_failed(
    log: structlog.stdlib.BoundLogger, delivery: EventDelivery, **context: object
) -> None:
    """Sentry bắt log ERROR để cảnh báo delivery cần người vận hành (07 mục 1.3).

    `context` là thông tin dẫn tới `failed`: bộ đếm (`attempts`, `interrupted_runs`),
    `invalid_fields` hoặc `exc_info` (traceback của lỗi parse).
    """
    log.error("event_delivery_failed", **context, error=delivery.last_error)


def _invalid_fields(exc: ValidationError) -> list[dict[str, object]]:
    # Chỉ field gốc và loại lỗi: input và message có thể chứa PII của payload (03 mục 1.4).
    # `loc[0]` là tên field đã khai báo; phần sau có thể là key lấy từ dữ liệu (field kiểu
    # `dict`). Bỏ trùng để kích thước log có giới hạn theo số field của class
    entries: list[dict[str, object]] = [
        {"field": error["loc"][0] if error["loc"] else "__root__", "type": error["type"]}
        for error in exc.errors(include_input=False, include_url=False)
    ]
    return [entry for index, entry in enumerate(entries) if entry not in entries[:index]]
