# 05 – Quản lý Sản phẩm và Biến thể

Status: ready-for-agent · Ưu tiên: 8 · Blocked by: [03](../03-category-navigation/spec.md), [04](../04-size-color-registry/spec.md) · **PR:**

## Mục tiêu
Admin tạo Sản phẩm `draft`, thêm atomically ma trận Biến thể size×màu, sửa, publish và archive; back-office đọc được trạng thái đầy đủ (US-802, US-803).

## Việc cần làm
- [ ] `modules/catalog/models/product.py`, `variant.py`: `Product`, `ProductColor`, `Variant` + migration (FK/unique/check/index).
- [ ] `services/products.py`: create/update, publish (`draft`→`active`), archive.
- [ ] `services/variants.py`: ghi ma trận Biến thể atomic.
- [ ] `selectors/products.py`: list/detail back-office, dùng `select_related`/`prefetch_related`.
- [ ] `api/backoffice/`: `GET/POST products`, `GET/PATCH/DELETE products/{id}`, `POST products/{id}/publish|archive`, `POST products/{id}/variants`, `PATCH products/{id}/variants/{variant_id}`.
- [ ] Audit cho mọi write.

## Quyết định
- Quy tắc: BR-CAT-01, 02, 03 (SKU), 06 (cân nặng), 07 (trạng thái), 09 (không xoá cứng) — [04-business-rules](../../../../docs/business/04-business-rules.md).
- Schema: [03 §3.2, 3.5, 3.7](../../../../docs/architecture/03-data-model.md); endpoint: [04-api-contract](../../../../docs/architecture/04-api-contract.md). `DELETE products/{id}` chỉ cho `draft`.
- Snapshot thay đổi tăng checkout version; availability không tăng version — [ADR 0012](../../../../docs/adr/0012-checkout-price-snapshot.md), [catalog](../../../../docs/architecture/modules/catalog.md).
- Transaction chỉ trong service, lock theo thứ tự ổn định; view chỉ validate rồi gọi service. Tách riêng Product/ProductColor/Variant, không viết một function làm mọi thứ.

## Acceptance criteria
- [ ] Tạo draft và ma trận Biến thể với SKU và size×màu unique; một dòng sai thì rollback toàn bộ.
- [ ] Không publish Sản phẩm thiếu Biến thể, cân nặng hoặc dữ liệu bắt buộc.
- [ ] Snapshot thay đổi tăng checkout version; availability không tăng version.
- [ ] Archive không hard delete; nested Variant phải thuộc đúng Product trong URL.
- [ ] API chỉ Admin, có audit; migration, OpenAPI và end-to-end management test xanh; `make fmt`, `make lint` sạch.

## Ghi chú
- Mentor viết test đỏ (tạo draft trước, rồi rollback/publish/ownership); người làm viết production code. Chạy test sau từng transition.
