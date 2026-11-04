# 09 — Điều chỉnh Tồn kho có lý do

**What to build:** Staff tăng hoặc giảm Tồn kho bằng một lệnh điều chỉnh có lý do; hệ thống không cho giảm vượt Số lượng bán được và giữ lịch sử/idempotency đầy đủ.

Blocked by: 08 — nền Tồn kho và Nhập kho.

Status: ready-for-agent

**PR:** —

- [ ] Delta khác 0, lý do bắt buộc; movement ghi actor/reason/reference phù hợp.
- [ ] Giảm vượt available trả conflict kèm giới hạn, không thay đổi dữ liệu.
- [ ] Hai điều chỉnh cạnh tranh serialize đúng; không tạo số âm.
- [ ] Idempotency replay/conflict và availability projection đúng.
- [ ] API/OpenAPI/concurrency tests xanh.
