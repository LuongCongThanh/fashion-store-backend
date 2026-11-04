# 11 — Storefront duyệt, tìm, lọc và xem Sản phẩm

**What to build:** Người mua không cần Tài khoản có thể duyệt danh sách, tìm/lọc/sắp xếp và xem chi tiết Sản phẩm active với đúng ảnh, Biến thể, Giá áp dụng và trạng thái còn hàng.

Blocked by: 06 — ảnh; 07 — pricing; 10 — trạng thái Tồn kho hoàn chỉnh.

Status: ready-for-agent

**PR:** —

- [ ] Danh sách chỉ có active; hết hàng vẫn hiện, draft/archived không lộ.
- [ ] Tìm kiếm trim/không dấu/không phân biệt hoa thường/chuỗi con liên tiếp và escape wildcard đúng BR-CAT-13.
- [ ] Filter category/size/color/price/in_stock và sort không duplicate; size+màu khớp cùng Biến thể còn hàng.
- [ ] Detail trả đúng màu/ảnh/size/SKU/Giá bán/Giá áp dụng/availability.
- [ ] Public API/OpenAPI, query-count/index-plan và US-101–104 flow tests xanh.
