# 12 — Acceptance và hardening toàn M1

**What to build:** Chứng minh toàn M1 hoạt động liền mạch bằng API thật: Admin tạo Catalog, Staff Nhập kho và Người mua tìm/xem đúng Sản phẩm; đóng mọi gate migration, OpenAPI, import boundary, query và coverage.

Blocked by: 01–11, 13 — mọi vertical slice M1 và quy ước OpenAPI.

Status: ready-for-agent

**PR:** —

- [ ] Admin/Staff dùng JWT thật; không dùng force_authenticate để chứng minh auth.
- [ ] Flow tạo taxonomy/Sản phẩm/Biến thể/ảnh/giá, publish, Nhập kho, tìm/filter/detail và archive chạy qua.
- [ ] Idempotency replay không tăng Tồn kho lần hai; storefront phản ánh availability/giá đúng.
- [ ] Migration DB rỗng/upgrade, OpenAPI drift, import-linter, query baseline và coverage qua.
- [ ] `make fmt`, `make lint`, `make test` xanh và report thực tế được viết sau implementation.
