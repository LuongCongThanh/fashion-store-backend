# Gom vòng đời Event delivery và vị từ outbox vào model

Status: resolved

**PR:** #62

Spec: [spec.md](../../spec.md)

Tách từ review của ticket [10](../10-shared-events-outbox/spec.md) ngày 30/10/2026 (finding T5, T6, T8, T9, T11) và review ticket [18](../18-outbox-operations/spec.md) (T6, T7, B10). Ngày 03/11/2026 thu hẹp lại sau review kiến trúc `backend/shared/events` (ứng viên 1 và 2). Phần test helper, trait factory và abstract model UUID v7 chuyển sang ticket [29](../29-outbox-test-helpers/spec.md). Không đổi hành vi.

## Bối cảnh

Mỗi chuyển trạng thái của `EventDelivery` hiện nằm ở một chỗ khác nhau:

- `completed` ghi inline trong `process_delivery`.
- `rejected` ở `_reject`; retry hoặc hết retry ở `_schedule_retry`; `failed` ở `_mark_failed`/`_fail_now`. Tăng `interrupted_runs` ghi inline. Tất cả ở `shared/events/consumer.py`.
- Mở lại delivery là một `.update(...)` riêng trong `retry_failed_events` (`operations.py`).
- Đánh dấu đã giao là một `.update(...)` riêng trong `relay.dispatch_due`.

Helper trả list tên cột để bên gọi tự ghép `update_fields`. Bất biến `completed_at`/`failed_at` chỉ có CheckConstraint giữ.

Các vị từ "tới hạn", "đã lập danh sách", "chưa kết thúc" cũng bị viết lại ở nhiều nơi:

- "Tới hạn" có 3 bản: `_is_due` trong consumer, `relay.dispatch_due`, `selectors.delivery_lag`.
- "Đã lập danh sách" có 4 bản, ở relay, purge, replay và selectors.
- "Chưa kết thúc" (`operations.py`) là phần bù của `_FINISHED` (`models.py`) nhưng viết riêng.

Vì vị từ nằm tách khỏi partial index, query purge không khớp index nào mà không ai thấy (B5 của ticket [28](../28-outbox-operations-hardening/spec.md)).

## Việc cần làm

- Mọi chuyển trạng thái của `EventDelivery` thành method trên model:
  - Từng delivery: method instance, ví dụ `start_run`, `complete`, `reject`, `retry_or_fail`, `fail`.
  - Hàng loạt: `@classmethod` nhận danh sách id, ví dụ `reopen`, `mark_dispatched`.
- Mỗi method tự `save(update_fields=…)` với đúng các cột nó đổi, gồm cả việc đặt `interrupted_runs = 0` khi lưu kết quả. Bên gọi không còn biết tên cột.
- Method nhận `now` từ bên gọi.
- Method không log. Method trả kết quả để bên gọi log, ví dụ `retry_or_fail` trả "đã hẹn retry" hoặc "đã `failed`". Bên gọi (consumer, `retry_failed_events`) giữ nguyên tên và trường của mọi event log.
- Chuyển `RETRY_DELAYS`, `MAX_INTERRUPTED_RUNS`, `INTERRUPTED_ERROR` và `describe_error` sang `shared/events/models.py`; method nhận thẳng exception. `_invalid_fields` ở lại consumer (context của log). Test chỉ sửa đường import các hằng này.
- Thêm `OutboxEventQuerySet` với `unlisted()` và `listed()`.
- Thêm `EventDeliveryQuerySet` với:
  - `attempt_due(now)`: `pending` và `next_attempt_at <= now`.
  - `dispatch_due(now)`: `attempt_due` cộng thêm `next_dispatch_at <= now`.
  - `unfinished()`.
- Thêm instance method `is_due(now)` thay cho `_is_due`.
- Đặt cả hai QuerySet cùng file với `Meta.indexes`. Relay, consumer, selectors, purge và replay gọi các primitive này. `delivery_lag` dùng `attempt_due`, vì hàm này cố ý không xét `next_dispatch_at`.
- Custom QuerySet chỉ chứa query primitive compose được, không có side effect ([13](../../../../docs/architecture/13-python-django-coding-style.md) mục 7.1). Vì vậy thao tác hàng loạt là classmethod của model, không phải QuerySet method.
- Thêm test trực tiếp cho method và vị từ mới:
  - lịch retry, hết retry
  - ngưỡng và việc đặt lại `interrupted_runs`
  - `reopen`, `mark_dispatched`
  - từng vị từ QuerySet

  Không xoá hay sửa test hành vi cũ; việc rút gọn test trùng thuộc ticket 29.

Ngoài phạm vi: index cho purge (B5) và chính sách cho handler mồ côi (B3) ở ticket [28](../28-outbox-operations-hardening/spec.md).

## Quyết định

Chốt khi grilling ngày 03/11/2026.

| Chủ đề | Quyết định |
| --- | --- |
| Tài liệu chi phối | `docs/architecture/13-python-django-coding-style.md::7.1` (model giữ invariant cục bộ; QuerySet chỉ chứa primitive không side effect), `docs/architecture/13-python-django-coding-style.md::7`, `docs/architecture/13-python-django-coding-style.md::9` (test), `docs/architecture/13-python-django-coding-style.md::10` (log giữ nguyên ở bên gọi), `docs/architecture/07-async-events-jobs.md::1.1.1` (relay, purge, replay, `delivery_lag`), `docs/architecture/07-async-events-jobs.md::1.3` (lịch retry, chạy dở, `retry_failed_events`), `docs/architecture/12-testing-strategy.md::2.3`, `docs/adr/0007-events-outbox-celery-no-kafka.md` |
| Interface / seam: tạo delivery | `EventDelivery.new(*, event, handler, now)` là classmethod trả instance chưa lưu, tới hạn ngay (`next_attempt_at = next_dispatch_at = now`). `relay.build_deliveries` gọi nó, nên `bulk_create` của relay và `replay_events` vẫn dùng được. Lịch ban đầu là quy tắc vòng đời, nên đặt cùng chỗ với các chuyển trạng thái. |
| Interface / seam: chạy handler | `start_run(now) -> RunStart` gom cả ngưỡng `MAX_INTERRUPTED_RUNS`: dưới ngưỡng thì tăng `interrupted_runs` và trả `RunStart.STARTED`; chạm ngưỡng thì chuyển `failed` với `last_error = INTERRUPTED_ERROR`, giữ bộ đếm ở ngưỡng và trả `RunStart.FAILED_INTERRUPTED`. Consumer không còn so sánh với ngưỡng, chỉ log `event_delivery_failed` kèm `interrupted_runs` như cũ. |
| Interface / seam: lưu kết quả | `complete(now)`: `completed`, `interrupted_runs = 0`. `reject(exc, now)`: `rejected`, `last_error`, `interrupted_runs = 0`. `retry_or_fail(exc, now) -> RetryOutcome`: tăng `attempts`, ghi `last_error`; còn lượt thì đặt `next_attempt_at = next_dispatch_at` theo `RETRY_DELAYS` (`RetryOutcome.SCHEDULED`), hết lượt thì `failed` (`RetryOutcome.FAILED`); cả hai đặt `interrupted_runs = 0`. `fail(exc, now)` cho lỗi parse: `failed`, `last_error`, giữ nguyên `attempts` và `interrupted_runs` (07 mục 1.3). Bên gọi đọc `delivery.attempts`, `delivery.next_attempt_at` để log; helper của consumer là `_record_handler_error` (đổi tên ở review, S6). |
| Interface / seam: hàng loạt | `EventDelivery.reopen(ids, *, now)` cho `retry_failed_events`. `EventDelivery.mark_dispatched(ids, *, now, next_dispatch_at)` cho relay; `REDISPATCH_AFTER` ở lại `relay.py` vì gắn với `CELERY_TASK_TIME_LIMIT`. Model quyết cột nào được ghi, relay quyết bao lâu thì giao lại. |
| Interface / seam: vị từ | `OutboxEventQuerySet.unlisted()` / `listed()`; `EventDeliveryQuerySet.attempt_due(now)`, `dispatch_due(now)`, `unfinished()` (phần bù của `_FINISHED`); `EventDelivery.is_due(now)`. Gắn qua `objects = <QuerySet>.as_manager()` theo mẫu `shared.models.BaseQuerySet`; manager không `use_in_migrations` nên không sinh migration. |
| Thứ tự log | `event_delivery_failed` và `event_retry_scheduled` chạy sau `save` thay vì trước, trong cùng transaction. Tên log, trường log và kết quả DB không đổi. |
| Phạm vi `listed` | `replay_events` dùng `.listed().filter(deliveries_created_at__gte=since)`; mốc `since` là điều kiện use case. Ghi marker `deliveries_created_at` trong `create_deliveries` (`mark_listed`) không thuộc ticket này, đã ghi vào `.scratch/backlog.md`. `filter(status=FAILED)` của `retry_failed_events` không phải một trong ba vị từ, nên giữ nguyên. |
| Test | Test trực tiếp ở `backend/shared/events/tests/test_models.py`, chạy trên PostgreSQL thật, dựng dữ liệu bằng `EventDeliveryFactory` / `OutboxEventFactory` (`shared/testing/factories.py`), cố định giờ bằng `now` truyền vào. Kịch bản lấy từ 07 mục 1.3 và 5. Để test red là `NotImplementedError` chứ không phải `AttributeError`, S1 khai chữ ký method trước rồi mới viết thân. Test hành vi cũ ở `shared/events/tests/` chỉ đổi đường import hằng. |

## Acceptance criteria

- [x] Ngoài `shared/events/models.py`, không chỗ nào gán `status`, `completed_at`, `failed_at`, `attempts`, `interrupted_runs`, `next_attempt_at`, `next_dispatch_at` hay `last_dispatched_at` của `EventDelivery`, hay truyền `update_fields` cho `EventDelivery`. Factory và test dựng dữ liệu không tính.
- [x] Ngoài `models.py`, không chỗ nào tự viết lại điều kiện tới hạn, đã lập danh sách hay chưa kết thúc. Có test trực tiếp cho từng method chuyển trạng thái và từng vị từ.
- [x] `make lint` và `make test` xanh. Test hành vi cũ chỉ đổi đường import, không đổi assert.
