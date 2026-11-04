# 12 – Acceptance và hardening toàn M1

Status: ready-for-agent · Ưu tiên: 15 · Blocked by: 01–11, [13](../13-openapi-docs-quality/spec.md) · **PR:** —

## Mục tiêu
Chứng minh M1 chạy liền mạch qua API thật: Admin tạo Catalog, Staff Nhập kho, Người mua tìm/xem đúng Sản phẩm. Đóng mọi gate. Không viết feature mới.

## Việc cần làm
- [ ] Flow test Admin: login → taxonomy/Sản phẩm/Biến thể/ảnh/giá → publish.
- [ ] Flow test Staff: login → Nhập kho → `GET stock` → idempotency replay.
- [ ] Flow test storefront: category/search/filter/detail → archive.
- [ ] Sửa production gap ở đúng module/tầng sở hữu, thay đổi nhỏ nhất.
- [ ] Chạy migration DB rỗng + upgrade, OpenAPI drift (`backend/openapi.yaml`), import-linter, query baseline, coverage.
- [ ] Chạy `make fmt`, `make lint`, `make test`; xanh rồi mới viết `report.md`.

## Quyết định
- Flow test theo [12 §2.7, §2.9.6](../../../../docs/architecture/12-testing-strategy.md); gate CI theo [12 §8](../../../../docs/architecture/12-testing-strategy.md).
- Không nới test hợp lệ hay gate để cho xanh; không tạo abstraction cho một trường hợp.

## Acceptance criteria
- [ ] Admin/Staff dùng JWT thật; không dùng `force_authenticate` để chứng minh auth.
- [ ] Flow tạo taxonomy/Sản phẩm/Biến thể/ảnh/giá, publish, Nhập kho, tìm/filter/detail và archive chạy qua.
- [ ] Idempotency replay không tăng Tồn kho lần hai; storefront phản ánh availability/giá đúng.
- [ ] Migration DB rỗng/upgrade, OpenAPI drift, import-linter, query baseline và coverage qua.
- [ ] `make fmt`, `make lint`, `make test` xanh; report thực tế viết sau implementation.

## Ghi chú
- `report.md` ghi kết quả lệnh thật và gap còn lại.
