# 10 — Kiểm kê theo số đếm trên kệ

**What to build:** Staff nhập số đếm trên kệ; hệ thống tính chênh lệch tại thời điểm xác nhận, điều chỉnh Tồn kho và ghi lịch sử mà không nhận delta do client tự tính.

Blocked by: 09 — điều chỉnh và invariant Tồn kho đã ổn định.

Status: ready-for-agent

**PR:** —

- [ ] Delta được tính server-side từ counted quantity và hàng trên kệ dưới khóa.
- [ ] Delta 0 không tạo movement nhưng trả kết quả/idempotency ổn định.
- [ ] Không giảm vượt available/reserved invariant; race với thao tác kho khác serialize đúng.
- [ ] Availability projection, permission và idempotency đúng.
- [ ] API/OpenAPI/concurrency tests xanh.
