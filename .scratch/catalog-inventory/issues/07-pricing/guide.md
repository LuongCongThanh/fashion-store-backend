# Guide ticket 07 — Pricing

## Mục đích

Quản lý Giá bán và Giá khuyến mãi với constraint thời gian, đồng thời cung cấp Catalog contracts.

## Bản đồ file

| Vị trí | Dùng làm gì | Mục đích |
|---|---|---|
| `modules/catalog/models/sale_price.py` | Lịch giá | Exclusion constraint |
| migration | btree_gist/range constraint | Chặn overlap ở DB |
| `services/pricing.py` | set list/sale price | Transaction/invariant |
| `selectors/pricing.py` | Effective Price tại `now` | Read thống nhất |
| `catalog/contracts.py` | DTO/snapshot/availability | Module boundary |
| back-office API + tests mentor tạo | CRUD giá | Demo end-to-end |

## Cách viết code và thứ tự thực hiện

Ở mỗi Step, biểu diễn tiền và thời gian bằng type phù hợp, viết selector `get_...` cho Giá áp dụng và service cho thay đổi giá. Viết bảng trường hợp boundary trước pseudo-code, sau đó triển khai từng nhánh và chạy test mentor cung cấp.

1. **Step 1:** Nhận test đỏ effective price.
2. **Step 2:** Tạo SalePrice model/migration/constraint.
3. **Step 3:** Viết selector và service price invariants.
4. **Step 4:** Viết API Sale Price + Variant price.
5. **Step 5:** Viết public contracts và import-boundary tests.
6. **Step 6:** Làm xanh boundary/concurrency tests, chạy gates/review.

## Kiến thức

PostgreSQL range/exclusion, timezone-aware `now`, MoneyDTO, locking, Pydantic DTO/contracts.
