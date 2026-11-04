# 25 – Relay xả tồn đọng nhanh hơn 100 delivery mỗi giây

Status: ready-for-agent · Ưu tiên: 19 · Blocked by: — · **PR:**

Spec: [spec.md](../../spec.md)

## Mục tiêu
Sau khi Redis ngừng lâu, relay xả tồn đọng nhanh để `delivery_lag()` (ticket [18](../18-outbox-operations/spec.md)) không giữ job T4 bỏ lượt quá lâu. Tách từ review ticket [10](../10-shared-events-outbox/spec.md) ngày 30/10/2026 (finding B6).

Hiện tại `run_outbox_relay` mỗi giây gọi `create_deliveries(batch=100)` và `dispatch_due(batch=100)` một lần → tối đa ~100 sự kiện và ~100 delivery mỗi giây. Ví dụ Redis ngừng 30 phút ở 50 sự kiện/giây, 3 handler: ~270 nghìn delivery, cần ~45 phút để xả.

## Việc cần làm
- [ ] Trong một vòng, lặp lại từng bước khi bước trước trả đủ `batch`; có giới hạn thời gian mỗi vòng để vẫn dừng kịp khi nhận SIGTERM.
- [ ] Đo trên staging theo mục tiêu ở [10-nfr.md mục 1](../../../../docs/architecture/10-nfr.md).

## Quyết định
Gợi ý thiết kế (review kiến trúc `shared/events` ngày 03/11/2026):
- Vòng xả đặt trong module `relay`, vd. `relay.run_round(stop, budget)`: gồm batch, time budget, điểm dừng, trả số liệu.
- `run_outbox_relay` chỉ đăng ký signal và ngủ giữa các vòng.
- `drain_events` (đang ở `shared.testing.events`) dùng lại cùng hàm.
- Test AC bằng cách gọi thẳng hàm với clock giả, không cần dựng management command.

## Acceptance criteria
- [ ] Tồn đọng lớn hơn `batch` được xả trong một vòng tới khi hết hoặc hết thời gian vòng.
- [ ] Relay vẫn dừng trong vài giây khi nhận SIGTERM giữa lúc xả tồn đọng.

## Ghi chú
- Sau [one-app-per-module/02](../../../one-app-per-module/issues/02-django-apps/spec.md): `shared/events` → `common/events`, `drain_events` → `common/events/testing.py`.
