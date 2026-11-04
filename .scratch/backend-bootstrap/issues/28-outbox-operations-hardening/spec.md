# 28 – Độ bền của theo dõi và purge outbox khi tồn đọng lớn

Status: ready-for-agent · Ưu tiên: 18 · Blocked by: [26](../26-outbox-refactor-smells/spec.md) (đã resolved) · **PR:**

Spec: [spec.md](../../spec.md)

## Mục tiêu
`delivery_lag()` phản ánh đúng sức khoẻ relay (job T4 không bỏ lượt huỷ đơn oan), và purge/retry chạy được khi tồn đọng lớn. Tách từ review ticket [18](../18-outbox-operations/spec.md) ngày 30/10/2026 (finding B3, B5, B7, B9) vì cần migration hoặc đổi consumer.

## Vấn đề
- **B3.** Handler không còn trong registry (`event_handler_missing`, ticket [10](../10-shared-events-outbox/spec.md)): consumer giữ delivery `pending` mà không dời `next_attempt_at`. Một dòng mồ côi làm `delivery_lag()` tăng mãi, T4 bỏ mọi lượt huỷ đơn dù relay, broker, worker vẫn khoẻ.
- **B5.** `purge_old_outbox_events` lọc `occurred_at < cutoff AND deliveries_created_at IS NOT NULL`, nhưng index `occurred_at` duy nhất là partial `WHERE deliveries_created_at IS NULL`. Mỗi lô 1.000 và lần đếm cuối quét toàn bảng; tồn đọng lớn thì vượt `CELERY_TASK_TIME_LIMIT` 120 s, bị kill rồi giao lại (`acks_late`) liên tục.
- **B7.** `delivery_lag()` tính tuổi sự kiện chưa lập danh sách theo `occurred_at` (không có cột giờ ghi DB). `occurred_at` có thể sớm hơn lúc commit hoặc do bên gọi truyền (giờ cổng thanh toán), nên T4 có thể bỏ lượt khi relay rảnh.
- **B9.** `retry_failed_events --all` khoá và cập nhật mọi delivery `failed` trong một transaction, không chia lô.

## Việc cần làm
- [ ] B3: chọn cách xử lý delivery của handler không còn đăng ký (dời lịch, chuyển `failed`, hoặc loại khỏi `delivery_lag`); sửa [07 mục 1.1.1](../../../../docs/architecture/07-async-events-jobs.md).
- [ ] B5: thêm index cho purge (vd. partial trên `occurred_at WHERE deliveries_created_at IS NOT NULL`) hoặc giới hạn thời gian mỗi lượt; cập nhật [03 mục 1.3](../../../../docs/architecture/03-data-model.md).
- [ ] B7: cân nhắc cột `created_at` (giờ ghi DB) cho bảng outbox event như 07 mục 1.1.1 ghi, dùng trong `delivery_lag()`.
- [ ] B9: chia lô cho `retry_failed_events --all`, giống replay và purge.

## Acceptance criteria
- [ ] Delivery `pending` của handler không còn đăng ký không làm `delivery_lag()` tăng mãi.
- [ ] Purge với tồn đọng lớn kết thúc trong `CELERY_TASK_TIME_LIMIT`, có test hoặc `EXPLAIN` chứng minh dùng index.
- [ ] `retry_failed_events --all` xử lý theo lô.

## Ghi chú
- Bảng là `shared_outbox_event`, đổi thành `common_outbox_event` sau [one-app-per-module/02](../../../one-app-per-module/issues/02-django-apps/spec.md).
