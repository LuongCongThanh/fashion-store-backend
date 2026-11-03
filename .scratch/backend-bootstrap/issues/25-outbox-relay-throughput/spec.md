# Relay xả tồn đọng nhanh hơn 100 delivery mỗi giây

Status: ready-for-agent

Spec: [spec.md](../../spec.md)

Tách từ review của ticket [10](../10-shared-events-outbox/spec.md) ngày 30/10/2026 (finding B6).

## Bối cảnh

`run_outbox_relay` mỗi giây gọi `create_deliveries(batch=100)` và `dispatch_due(batch=100)` một lần, nên thông lượng tối đa khoảng 100 sự kiện và 100 delivery mỗi giây. Sau khi Redis ngừng lâu (ví dụ 30 phút ở 50 sự kiện/giây, 3 handler), tồn đọng khoảng 270 nghìn delivery cần khoảng 45 phút để xả, trong lúc `delivery_lag()` (ticket [18](../18-outbox-operations/spec.md)) giữ job T4 bỏ lượt.

## Việc cần làm

- Trong một vòng, lặp lại từng bước khi bước trước trả đủ `batch`, có giới hạn thời gian mỗi vòng để vẫn dừng kịp khi nhận SIGTERM.
- Đo trên staging cùng mục tiêu ở `docs/architecture/10-nfr.md` mục 1.

Gợi ý thiết kế từ review kiến trúc `backend/shared/events` ngày 03/11/2026:

- Đặt vòng xả tồn đọng trong module `relay`, ví dụ `relay.run_round(stop, budget)`: gồm batch, time budget, điểm dừng, và trả số liệu.
- `run_outbox_relay` chỉ đăng ký signal và ngủ giữa các vòng.
- `shared.testing.events.drain_events` dùng lại cùng hàm đó.
- Như vậy acceptance criteria test được bằng cách gọi thẳng hàm với clock giả, không cần dựng management command.

## Acceptance criteria

- [ ] Tồn đọng lớn hơn `batch` được xả trong một vòng tới khi hết hoặc hết thời gian vòng.
- [ ] Relay vẫn dừng trong vài giây khi nhận SIGTERM giữa lúc xả tồn đọng.
