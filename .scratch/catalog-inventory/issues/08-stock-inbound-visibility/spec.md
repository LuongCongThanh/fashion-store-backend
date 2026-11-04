# 08 – Xem Tồn kho và Nhập kho

Status: ready-for-agent · Ưu tiên: 11 · Blocked by: [05](../05-product-variant-management/spec.md), [07](../07-pricing/spec.md) · **PR:** —

## Mục tiêu
Staff/Admin xem Tồn kho, Số lượng bán được theo Biến thể và Nhập kho theo số phiếu nhập. Retry không cộng Tồn kho hai lần.

## Việc cần làm
- [ ] `inventory/models/`: `Warehouse`, `StockItem`, `StockMovement` + constraint/index theo [03 §4](../../../../docs/architecture/03-data-model.md#4-inventory).
- [ ] Migration: tạo bảng, FK, seed Kho `MAIN`.
- [ ] `inventory/selectors/stock.py`: list + lọc tồn thấp `available_lt`, có pagination; SKU/tên lấy qua `catalog.contracts`.
- [ ] `inventory/services/stock.py`: `receive_stock` (validate → transaction → `select_for_update` → kiểm invariant → ghi movement + projection → trả `StockDTO`).
- [ ] `inventory/contracts.py`: `get_available(variant_ids)` cho mốc sau.
- [ ] `inventory/api/backoffice/`: `GET stock`, `POST stock/inbound` (bắt buộc `Idempotency-Key`), cập nhật OpenAPI.
- [ ] Test: permission, idempotency replay/conflict/pending, concurrency, availability projection, flow.

## Quyết định
- Tồn kho theo Biến thể × Kho, MVP một Kho (BR-INV-01). Số lượng bán được = `on_hand − reserved` (BR-INV-02).
- Endpoint và lọc `available_lt=<n>` (mặc định 5) theo [04 §4.2](../../../../docs/architecture/04-api-contract.md) và US-702; Nhập kho bắt buộc số phiếu nhập (US-701 AC1).
- Mỗi thay đổi `on_hand` ghi một `StockMovement` có actor/reference (BR-INV-09, [03 §4.5](../../../../docs/architecture/03-data-model.md#45-inventory_stock_movement-lịch-sử-thay-đổi-tồn-kho-br-inv-09)).
- Số lượng bán được đổi giữa 0 và > 0 thì gọi `catalog.contracts.set_variant_availability` trong cùng transaction ([modules/inventory §5](../../../../docs/architecture/modules/inventory.md)).
- Khoá StockItem theo `variant_id` tăng dần trước khi chạm `catalog` ([13 §4](../../../../docs/architecture/13-python-django-coding-style.md#4-service-transaction-và-tác-vụ-bên-ngoài)).
- Idempotency theo [03 §1.5](../../../../docs/architecture/03-data-model.md) và [04 §1](../../../../docs/architecture/04-api-contract.md).

## Acceptance criteria
- [ ] Kho `MAIN`/StockItem/StockMovement và constraint/index migrate đúng.
- [ ] Staff/Admin đọc danh sách Tồn kho, lọc tồn thấp, nhận SKU/tên qua public contract.
- [ ] Nhập kho khoá dòng, tăng `on_hand`, ghi movement actor/reference và cập nhật availability cùng transaction.
- [ ] Idempotency replay/conflict/pending đúng; concurrency không làm sai số lượng.
- [ ] Permission, migration, API/OpenAPI, contract và flow tests xanh.

## Ghi chú
- View không giữ row lock, không tự cập nhật Tồn kho; đọc qua selector, ghi qua service.
- Test concurrency dùng connection riêng ([12 §2.9.3](../../../../docs/architecture/12-testing-strategy.md)); kiểm query count cho `GET stock`.
- (từ backlog, ticket nguồn backend-bootstrap/04) `gen_importlinter.py` sinh `ignore_imports` cho FK model → model của module lớp dưới ([02 §6, §8](../../../../docs/architecture/02-backend-structure.md)), kèm test trên cây package tạm. Cần vì `StockItem` khai FK chéo sang Biến thể.
- (từ backlog, ticket nguồn backend-bootstrap/27) Contract test trong CI: snapshot JSON schema của mỗi `(event_type, schema_version)` đã đăng ký, fail khi thêm/bỏ field bắt buộc của `…V1`. Làm khi module đầu tiên thêm sự kiện.
