# 03 — Quản lý Danh mục và storefront navigation

**What to build:** Admin tạo, sắp xếp, di chuyển và xóa Danh mục hợp lệ; Người mua xem cây Danh mục công khai theo đúng thứ tự để điều hướng.

Blocked by: 01 — cần Admin JWT cho API quản trị.

Status: ready-for-agent

**PR:** —

- [ ] Admin tạo cây nhiều cấp, sửa parent/position và đọc cây back-office.
- [ ] Self-parent/cycle/slug trùng/xóa node đang có con hoặc Sản phẩm bị từ chối rõ ràng.
- [ ] Người mua gọi storefront categories không cần token và nhận cây đúng thứ tự.
- [ ] Staff/Customer/anonymous không ghi được Danh mục; write có audit.
- [ ] Migration, API/OpenAPI và flow tests của lát cắt xanh.
