# 07 – Giá bán và Giá khuyến mãi

Status: ready-for-agent · Ưu tiên: 9 · Blocked by: [05](../05-product-variant-management/spec.md) · **PR:**

## Mục tiêu
Admin đặt Giá bán cho Biến thể và lịch Giá khuyến mãi cho một Biến thể hoặc toàn Sản phẩm; API trả Giá áp dụng đúng thời điểm; public contracts sẵn cho Inventory/Ordering (US-804).

## Việc cần làm
- [ ] Viết bảng case boundary start/end trước khi code.
- [ ] `modules/catalog/models/sale_price.py` + migration: `btree_gist`, exclusion constraint chặn overlap.
- [ ] `selectors/pricing.py`: `get_...` Giá áp dụng tại `now` (timezone-aware).
- [ ] `services/pricing.py`: đặt Giá bán, tạo/sửa/xoá Giá khuyến mãi, giữ invariant trong transaction.
- [ ] `api/backoffice/`: `GET/POST sale-prices`, `PATCH/DELETE sale-prices/{id}`, Giá bán qua `PATCH products/{id}/variants/{variant_id}`.
- [ ] `catalog/contracts.py`: DTO/snapshot/availability + test import boundary.

## Quyết định
- Quy tắc: BR-CAT-04, BR-PRC-01, 02, 03, 05 — [04-business-rules](../../../../docs/business/04-business-rules.md).
- Schema: [03 §3.8](../../../../docs/architecture/03-data-model.md); endpoint: [04-api-contract](../../../../docs/architecture/04-api-contract.md). Hạ Giá bán ≤ Giá khuyến mãi đang/sắp hiệu lực → `422 LIST_PRICE_BELOW_SALE_PRICE`. `DELETE sale-prices/{id}` chỉ khi chưa bắt đầu.
- Product-target tạo Giá khuyến mãi cho mọi Biến thể: toàn bộ hoặc rollback.
- Response tiền dùng `MoneyDTO`. Public contract theo [catalog §4.1](../../../../docs/architecture/modules/catalog.md).

## Acceptance criteria
- [ ] Giá là số nguyên VND >0; Giá khuyến mãi < Giá bán; khoảng hiệu lực không chồng.
- [ ] Hạ Giá bán xung đột lịch giá bị từ chối; product-target tạo toàn bộ hoặc rollback.
- [ ] Giá áp dụng đúng boundary start/end; response dùng `MoneyDTO`.
- [ ] Catalog contracts có DTO rõ; availability update idempotent; import boundary được bảo vệ.
- [ ] Constraint/concurrency/API/OpenAPI/contract test xanh; `make fmt`, `make lint` sạch.

## Ghi chú
- Mentor viết test đỏ (effective price trước); người làm viết production code.
- Bẫy: dùng `now` timezone-aware và truyền vào selector, không gọi đồng hồ rải rác.
