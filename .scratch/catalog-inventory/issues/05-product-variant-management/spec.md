# 05 — Quản lý Sản phẩm và Biến thể

**What to build:** Admin tạo Sản phẩm draft, thêm atomically các Biến thể size×màu, sửa dữ liệu, publish và archive; back-office đọc được trạng thái đầy đủ.

Blocked by: 03 — Danh mục; 04 — size và màu.

Status: ready-for-agent

**PR:** —

- [ ] Tạo draft và ma trận Biến thể với SKU/size×màu unique; một dòng sai rollback toàn bộ.
- [ ] Không publish Sản phẩm thiếu Biến thể/cân nặng/dữ liệu bắt buộc.
- [ ] Snapshot thay đổi tăng checkout version; availability không tăng version.
- [ ] Archive không hard delete; nested Variant phải thuộc đúng Product URL.
- [ ] Admin-only API, audit, migration, OpenAPI và end-to-end management tests xanh.
