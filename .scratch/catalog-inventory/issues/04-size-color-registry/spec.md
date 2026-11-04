# 04 — Quản lý danh sách size và bảng màu

**What to build:** Admin quản lý danh sách size và bảng màu chuẩn dùng cho Biến thể/filter, gồm tạo, đọc, sửa và ẩn; giá trị đã được dùng không bị xóa.

Blocked by: 01 — cần Admin JWT cho API quản trị; 13 — quy ước OpenAPI cho endpoint mới; one-app-per-module/03 — chuyển code sang cấu trúc ADR 0018 trước khi viết module mới.

Status: ready-for-agent

**PR:** —

- [ ] Admin tạo/list/patch size và màu; code unique, màu đúng định dạng hex.
- [ ] `FREESIZE` tồn tại theo seed/idempotent data migration.
- [ ] Size/màu đã gắn Biến thể chỉ chuyển inactive, không hard delete.
- [ ] Staff/Customer/anonymous không ghi được; write có audit.
- [ ] Migration, pagination, API/OpenAPI tests xanh.
