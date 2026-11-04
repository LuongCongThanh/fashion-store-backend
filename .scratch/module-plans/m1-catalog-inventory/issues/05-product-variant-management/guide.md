# Guide ticket 05 — Sản phẩm và Biến thể

## Mục đích và flow

Admin tạo draft → tạo ma trận Biến thể → publish/archive; mỗi bước giữ invariant Catalog.

```mermaid
flowchart LR
  Draft --> Variants[Thêm size x màu]
  Variants --> Publish[Kiểm đủ và publish]
  Publish --> Active
  Active --> Archive
```

## Bản đồ file

| Vị trí | Dùng làm gì | Mục đích |
|---|---|---|
| `modules/catalog/models/product.py`, `variant.py` | Product/ProductColor/Variant | Domain data |
| migration chain | FK/unique/check/index | Bảo vệ invariant |
| `services/products.py`, `variants.py` | transitions/matrix write | Atomic business logic |
| `selectors/products.py` | back-office list/detail | Read tối ưu |
| `api/backoffice/` | Product/Variant endpoints | Capability demo |
| tests mentor tạo | matrix rollback/publish/ownership | Đường ray |

## Cách viết code và thứ tự thực hiện

Ở mỗi Step, tách rõ Product, ProductColor và Variant thay vì viết một function xử lý mọi thứ. Viết signature và pseudo-code trước; transaction chỉ nằm trong service, lock theo thứ tự ổn định, view chỉ validate/gọi service. Chạy test sau từng transition.

1. **Step 1:** Nhận test đỏ tạo draft.
2. **Step 2:** Tạo models/migration và service create/update.
3. **Step 3:** Viết API list/create/detail/patch/delete.
4. **Step 4:** Viết atomic variant matrix service/API.
5. **Step 5:** Viết publish/archive transitions.
6. **Step 6:** Làm xanh invariant/permission/audit tests.
7. **Step 7:** Chạy gates và review.

## Kiến thức

Multi-model transaction, unique constraint, state transition, nested route ownership, select/prefetch related.
