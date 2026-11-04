# Spec: Mỗi module một Django app

Status: ready-for-agent

## Mục tiêu
Đưa code về cấu trúc đích của [ADR 0018](../../docs/adr/0018-one-django-app-per-module.md) và [02-backend-structure.md](../../docs/architecture/02-backend-structure.md) **trước khi** M1 viết module mới. Lúc này mới có `identity` và `shared` có code, chưa có môi trường chạy thật nên đổi rẻ.

Hiện trạng: Django project nằm trong `backend/`; một app `modules` chứa mọi module; `shared` chứa hạ tầng và địa giới; test dồn phẳng trong `shared/tests/`, đặt tên không theo quy tắc.

## Phạm vi
- Chỉ di chuyển, đổi tên, cấu hình lại. **Không đổi hành vi** nghiệp vụ hay API.
- Tài liệu nhắc đường dẫn code được sửa trong PR của ticket chạm tới nó.
- Ngoài phạm vi: viết module mới hoặc adapter bên thứ ba; đổi tên repo GitHub.

## Quyết định
- **Thứ tự:** 3 ticket nối tiếp, mỗi ticket một PR, CI xanh: đưa lên gốc repo → đổi Django app → sắp test.
- **Migration:** sinh lại từ đầu ở ticket 02, không viết migration chuyển dữ liệu. Mỗi dev chạy `make db-reset` một lần sau khi merge.
- **`infrastructure/`:** chưa tạo vì chưa có adapter. Package, lớp `infrastructure` trong contract `layers` và contract "chỉ module sở hữu import" tạo cùng adapter đầu tiên (VNPay/MoMo, GHN hoặc Google).
- **Module chưa có code:** không tạo app rỗng; package rỗng trong `modules/` bị xoá ở ticket 02.
- **Số test:** mỗi ticket so `pytest --collect-only -q` trước và sau; phải bằng nhau.
- **Nhánh:** tách từ `dev` theo [11](../../docs/architecture/11-git-workflow.md), PR vào `dev`.
- **Tài liệu lịch sử:** ADR 0006, 0017 và `.scratch/` không sửa đường dẫn.

## Ticket
1. [`01-flatten-repo-root/`](./issues/01-flatten-repo-root/spec.md): đưa Django project từ `backend/` lên gốc repo.
2. [`02-django-apps/`](./issues/02-django-apps/spec.md): `shared` → `common` + `apps/geo`, `modules` → `apps/identity`, sinh lại migration.
3. [`03-mirror-test-layout/`](./issues/03-mirror-test-layout/spec.md): đặt lại vị trí và tên file test theo quy tắc soi gương.
