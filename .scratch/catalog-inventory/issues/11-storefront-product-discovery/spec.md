# 11 – Storefront duyệt, tìm, lọc và xem Sản phẩm

Status: ready-for-agent · Ưu tiên: 14 · Blocked by: [06](../06-product-images/spec.md), [07](../07-pricing/spec.md), [10](../10-stock-count/spec.md) · **PR:** —

## Mục tiêu
Người mua không cần Tài khoản duyệt, tìm, lọc, sắp xếp và xem chi tiết Sản phẩm active với đúng ảnh, Biến thể, Giá áp dụng và trạng thái còn hàng.

## Việc cần làm
- [ ] `catalog/selectors/products.py`: list/filter/search/sort + detail, trả `ProductSummaryDTO` page và `ProductDTO`. Viết DTO và signature trước.
- [ ] Schema `ProductQuery` validate query ([04 §5.5](../../../../docs/architecture/04-api-contract.md)).
- [ ] `catalog/api/store/`: `GET products`, detail theo `slug`; view chỉ parse query và gọi selector. Cập nhật OpenAPI.
- [ ] Migration index nếu thiếu: GIN trigram trên `immutable_unaccent(lower(name))` ([03 §3](../../../../docs/architecture/03-data-model.md)).
- [ ] Test: US-101–104, hidden/hết hàng, query-count, index-plan.

## Quyết định
- Chỉ `active` hiển thị; hết hàng vẫn hiện (BR-CAT-07, BR-CAT-08).
- Tìm kiếm theo BR-CAT-13: chuỗi con liên tiếp trong tên, trim, không dấu, không phân biệt hoa thường, escape `%`/`_`; không tìm gần đúng.
- Filter `category`, `size`, `color`, `price_min`/`price_max`, `in_stock`, `q`, `ordering` theo [04 §4.1](../../../../docs/architecture/04-api-contract.md); size + màu phải khớp cùng một Biến thể còn hàng.
- Ảnh theo màu (BR-CAT-05).

## Acceptance criteria
- [ ] Danh sách chỉ có active; hết hàng vẫn hiện; draft/archived không lộ.
- [ ] Tìm kiếm trim/không dấu/không phân biệt hoa thường/chuỗi con liên tiếp và escape wildcard đúng BR-CAT-13.
- [ ] Filter category/size/color/price/in_stock và sort không duplicate; size + màu khớp cùng Biến thể còn hàng.
- [ ] Detail trả đúng màu/ảnh/size/SKU/Giá bán/Giá áp dụng/availability.
- [ ] Public API/OpenAPI, query-count/index-plan và US-101–104 flow tests xanh.

## Ghi chú
- Lọc theo Biến thể dễ sinh dòng trùng: dùng `Exists`/`Subquery` thay join + `distinct` để pagination đúng.
- `select_related`/`prefetch_related` có chủ đích; khoá query count bằng test.
