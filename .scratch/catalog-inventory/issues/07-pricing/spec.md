# 07 — Giá bán và Giá khuyến mãi

**What to build:** Admin đặt Giá bán cho Biến thể và lịch Giá khuyến mãi cho một Biến thể hoặc toàn Sản phẩm; API đọc trả Giá áp dụng đúng thời điểm và public contracts sẵn sàng cho Inventory/Ordering.

Blocked by: 05 — Sản phẩm và Biến thể.

Status: ready-for-agent

**PR:** —

- [ ] Giá nguyên VND >0; Giá khuyến mãi nhỏ hơn Giá bán và khoảng hiệu lực không chồng.
- [ ] Hạ Giá bán xung đột với lịch giá bị từ chối; product-target tạo toàn bộ hoặc rollback.
- [ ] Giá áp dụng đúng boundary start/end; response dùng MoneyDTO.
- [ ] Catalog contracts có DTO rõ, availability update idempotent và import boundary được bảo vệ.
- [ ] Constraint/concurrency/API/OpenAPI/contract tests xanh.
