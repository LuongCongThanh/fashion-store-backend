# 03 – Quản lý Danh mục và storefront navigation

Status: ready-for-agent · Ưu tiên: 6 · Blocked by: [01](../01-backoffice-login/spec.md), [13](../13-openapi-docs-quality/spec.md), [one-app-per-module/03](../../../one-app-per-module/issues/03-mirror-test-layout/spec.md) · **PR:**

## Mục tiêu
Admin tạo, sắp xếp, di chuyển, xoá Danh mục; Người mua xem cây Danh mục công khai đúng thứ tự để điều hướng (US-801, US-101).

## Việc cần làm
- [ ] `modules/catalog/models/category.py` + migration: self-FK `parent` (PROTECT), `slug` unique, `position`.
- [ ] `modules/catalog/services/categories.py`: create/update/delete, kiểm cycle (viết pseudo-code trước khi ra ORM).
- [ ] `modules/catalog/selectors/categories.py`: dựng cây, thứ tự ổn định.
- [ ] `modules/catalog/api/backoffice/`: `GET/POST categories`, `PATCH/DELETE categories/{id}` (Admin).
- [ ] `modules/catalog/api/store/`: `GET categories` công khai → `CategoryTreeDTO[]`.
- [ ] Audit cho mọi write.

## Quyết định
- Schema: [03 §3.1](../../../../docs/architecture/03-data-model.md); endpoint/DTO: [04-api-contract](../../../../docs/architecture/04-api-contract.md).
- Xoá chỉ khi không còn Danh mục con hay Sản phẩm. Tên Danh mục chỉ tiếng Việt (BR-CAT-10).
- Chỉ Admin ghi; storefront public, không cần token.
- Public function dùng keyword-only args + return type; view không query model trực tiếp — [13](../../../../docs/architecture/13-python-django-coding-style.md).

## Acceptance criteria
- [ ] Admin tạo cây nhiều cấp, sửa parent/position và đọc cây back-office.
- [ ] Self-parent, cycle, slug trùng, xoá node còn con hoặc còn Sản phẩm bị từ chối rõ ràng.
- [ ] Người mua gọi storefront categories không cần token, nhận cây đúng thứ tự.
- [ ] Staff/Customer/anonymous không ghi được; write có audit.
- [ ] Migration, API/OpenAPI và flow test xanh; `make fmt`, `make lint` sạch.

## Ghi chú
- Mentor viết test đỏ (root+child trước); người làm viết production code.
- (từ backlog, ticket nguồn backend-bootstrap/04) `modules/<m>/__init__.py` không re-export phần nội bộ (import-linter không cấm được); ghi quy ước vào [02 §6.1](../../../../docs/architecture/02-backend-structure.md) hoặc thêm check riêng.
