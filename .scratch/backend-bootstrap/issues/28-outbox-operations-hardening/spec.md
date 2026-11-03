# Độ bền của theo dõi và purge outbox khi tồn đọng lớn

Status: ready-for-agent

Blocked by: 26

Spec: [spec.md](../../spec.md)

Tách từ review của ticket [18](../18-outbox-operations/spec.md) ngày 30/10/2026 (finding B3, B5, B7, B9). Các mục cần migration hoặc đổi consumer nên không làm trong ticket 18.

## Bối cảnh

- **B3.** Consumer giữ delivery `pending` mà không dời `next_attempt_at` khi handler không còn trong registry (`event_handler_missing`, ticket [10](../10-shared-events-outbox/spec.md)). `delivery_lag()` tính mọi delivery `pending` tới hạn, nên một dòng mồ côi (handler bị đổi tên hoặc gỡ khi deploy) làm lag tăng mãi và job T4 bỏ mọi lượt huỷ đơn, dù relay, broker và worker vẫn khoẻ.
- **B5.** `purge_old_outbox_events` lọc `occurred_at < cutoff AND deliveries_created_at IS NOT NULL`, nhưng index duy nhất trên `occurred_at` là partial `WHERE deliveries_created_at IS NULL`. Mỗi lô 1.000 và lần đếm cuối đều quét toàn bảng. Khi tồn đọng lớn (lần chạy đầu, hoặc purge ngừng lâu), task có thể vượt `CELERY_TASK_TIME_LIMIT` 120 giây, bị kill rồi giao lại (`acks_late`) liên tục.
- **B7.** `delivery_lag()` tính tuổi sự kiện chưa lập danh sách theo `occurred_at` vì `OutboxEvent` không có cột giờ ghi DB. `occurred_at` có thể sớm hơn lúc commit (transaction dài) hoặc do bên gọi truyền vào (giờ của cổng thanh toán), nên T4 có thể bỏ lượt khi relay đang rảnh.
- **B9.** `retry_failed_events --all` khoá và cập nhật mọi delivery `failed` trong một transaction, không chia lô như replay và purge.

## Việc cần làm

- Quyết định cách xử lý delivery của handler không còn đăng ký: dời lịch, chuyển `failed`, hoặc loại khỏi `delivery_lag` (sửa 07 mục 1.1.1).
- Thêm index phục vụ purge (ví dụ partial trên `occurred_at WHERE deliveries_created_at IS NOT NULL`) hoặc giới hạn thời gian mỗi lượt purge; cập nhật 03 mục 1.3.
- Cân nhắc cột `created_at` (giờ ghi DB) cho `shared_outbox_event` như 07 mục 1.1.1 ghi, và dùng nó trong `delivery_lag()`.
- Chia lô cho `retry_failed_events --all`.

## Acceptance criteria

- [ ] Delivery `pending` của handler không còn đăng ký không làm `delivery_lag()` tăng mãi.
- [ ] Purge với tồn đọng lớn kết thúc trong `CELERY_TASK_TIME_LIMIT`, có test hoặc `EXPLAIN` chứng minh dùng index.
- [ ] `retry_failed_events --all` xử lý theo lô.
