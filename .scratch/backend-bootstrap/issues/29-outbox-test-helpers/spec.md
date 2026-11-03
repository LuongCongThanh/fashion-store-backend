# Gom helper test outbox, trait factory và rút gọn test trùng

Status: ready-for-agent

Blocked by: 26

Spec: [spec.md](../../spec.md)

Tách từ ticket [26](../26-outbox-refactor-smells/spec.md) ngày 03/11/2026, sau review kiến trúc `backend/shared/events`. Nguồn gốc: finding T5, T6, T8, T9, T11 của review ticket [10](../10-shared-events-outbox/spec.md) và T6, T7, B10 của review ticket [18](../18-outbox-operations/spec.md). Không đổi hành vi.

## Việc cần làm

- Gom vào `shared/events/tests/conftest.py`: `NOW`, `ORDER_CODE`, exception giả, helper ghi tác động và khung thread + `Barrier`.
- `OutboxEventFactory` không mặc định trỏ tới sự kiện mẫu chỉ khai báo trong test (`shared.sample-happened`).
- Đổi helper `_listed_event` (lặp ở `test_purge.py`, `test_replay_events.py`, `test_selectors.py`) và `_failed` (`test_retry_failed_events.py`) thành trait của factory, ví dụ `OutboxEventFactory(listed=True)`.
- Cân nhắc abstract model chung cho `id` UUID v7: `BaseModel`, `OutboxEvent` và `EventDelivery` đang khai báo lặp.
- Rút gọn test ở `test_consumer.py`, `test_relay.py`, `test_selectors.py` nếu chúng chỉ kiểm lại điều mà test trực tiếp của ticket 26 đã kiểm (lịch retry, ngưỡng `interrupted_runs`, vị từ tới hạn). Chỉ thay test, không thêm lớp test mới. `test_consumer.py` giữ phần điều phối: khoá, hai transaction, savepoint, giao trùng, log.

## Quyết định

Chốt khi grilling ngày 03/11/2026.

| Chủ đề | Quyết định |
| --- | --- |
| Tài liệu chi phối | `docs/architecture/12-testing-strategy.md::4` (dữ liệu test, factory), `docs/architecture/12-testing-strategy.md::2.2` (concurrency: `transaction=True`, marker `concurrency`, `Barrier`), `docs/architecture/13-python-django-coding-style.md::9` (test), `docs/architecture/13-python-django-coding-style.md::7.1` (model), `docs/adr/0008-uuid-v7-primary-keys.md` |
| Nơi đặt helper | Khác *Việc cần làm*: hằng và helper cần import (`NOW`, `ORDER_CODE`, exception giả, `record_effect`, `run_concurrently`) đặt ở `shared/events/tests/_helpers.py`, theo tiền lệ `shared/tests/_helpers.py`; pytest không khuyên import từ `conftest.py`. `conftest.py` chỉ giữ fixture, `SampleHappenedV1` và `HandlerEffect`. Mỗi vai exception giả một tên: lỗi handler (`Exception`), `RetryLater`, `DomainError`, `BaseException` (worker bị kill). `NOW` thống nhất một mốc cho mọi file, kể cả `test_models.py`. |
| Factory | `OutboxEventFactory` mặc định trung tính: `event_type="shared.test-event"`, `payload={}`. Trait `sample=True` lấy `event_type` và payload hợp lệ của `SampleHappenedV1` (`order_code`, `amount`); `listed=True` đặt `deliveries_created_at`. `EventDeliveryFactory` có trait `failed=True` (`status=FAILED`, `failed_at`, `last_error`). Giá trị riêng từng file (mốc `occurred_at`, `attempts`) truyền qua kwargs. Thay `_listed_event` (3 bản) và `_failed`. Mẫu trait: `IdempotencyKeyFactory.Params`. |
| Interface / seam: UUID v7 | Abstract `UUIDv7Model` ở `shared/models.py`, chỉ có `id = UUIDField(primary_key=True, default=uuid7, editable=False)`. `BaseModel`, `OutboxEvent`, `EventDelivery` kế thừa; quy tắc khoá chính của ADR 0008 nằm một chỗ. Outbox vẫn không kế thừa `BaseModel` (không có `created_at`/`updated_at`). Field không đổi nên không sinh migration (`makemigrations --check`). |
| Rút gọn test trùng | Test model giữ quy tắc tính toán (lịch retry, bộ đếm, cột reset). Test điều phối (consumer, relay, `retry_failed_events`, drain) chỉ giữ trạng thái cuối, log, rollback, Celery, khoá; bỏ assert lặp giá trị đã tính. Cụ thể: xoá `test_saved_outcome_resets_interrupted_runs`; bỏ assert `next_attempt_at == NOW + RETRY_DELAYS[…]` ở `test_retry_later_keeps_pending_with_schedule`, `test_validation_error_inside_handler_schedules_retry`, `test_drain_does_not_wait_for_future_retry`; `test_exhausted_retries_mark_failed` chỉ giữ status `failed` và log `event_delivery_failed`; test của `retry_failed_events` giữ log và lọc `failed`, bỏ assert từng cột đã reset. |
| Marker `concurrency` | Theo yêu cầu người dùng: gắn `@pytest.mark.concurrency` cho test nhiều thread còn thiếu (`test_consumer.py::test_concurrent_duplicate_dispatch_commits_once`, hai test `Barrier` của `test_relay.py`, test thread của `test_replay_events.py`), theo 12 mục 2.2. |
| Test | Test trực tiếp mới: `shared/tests/test_models.py::test_outbox_models_share_uuid7_primary_key`; `shared/events/tests/test_factories.py` cho mặc định trung tính và các trait. Test red bằng `AssertionError`: khai `UUIDv7Model` rỗng trước. Còn lại verify toàn bộ test `shared/events` và `shared/tests/test_models.py`, `test_migrations.py`. |

## Acceptance criteria

- [ ] Không còn hằng hay helper test nào bị khai báo lặp giữa các file test của `shared/events`. `OutboxEventFactory` mặc định không cần sự kiện mẫu của test.
- [ ] Mỗi quy tắc vòng đời Event delivery chỉ được kiểm ở một chỗ: test trực tiếp trên model, hoặc test điều phối của consumer.
- [ ] `make lint` và `make test` xanh. Cổng branch coverage của nhóm `shared` vẫn đạt.
