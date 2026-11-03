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

## Acceptance criteria

- [ ] Không còn hằng hay helper test nào bị khai báo lặp giữa các file test của `shared/events`. `OutboxEventFactory` mặc định không cần sự kiện mẫu của test.
- [ ] Mỗi quy tắc vòng đời Event delivery chỉ được kiểm ở một chỗ: test trực tiếp trên model, hoặc test điều phối của consumer.
- [ ] `make lint` và `make test` xanh. Cổng branch coverage của nhóm `shared` vẫn đạt.
