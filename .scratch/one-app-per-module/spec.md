# Spec: Chuyển code sang cấu trúc mỗi module một Django app

Status: ready-for-agent

## Bối cảnh

Tài liệu đã chốt cấu trúc đích theo [ADR 0018](../../docs/adr/0018-one-django-app-per-module.md) và [02-backend-structure.md](../../docs/architecture/02-backend-structure.md), nhưng code vẫn ở bố cục cũ: Django project trong `backend/`, một app `modules` chứa mọi module, `shared` chứa hạ tầng và địa giới, test dồn phẳng trong `shared/tests/` và đặt tên không theo quy tắc.

Mục tiêu: đưa code về đúng cấu trúc đích **trước khi** M1 viết tiếp module mới, khi mới có `identity` và `shared` có code và chưa có môi trường nào chạy thật.

## Phạm vi

Chỉ di chuyển, đổi tên và cấu hình lại; **không đổi hành vi** nghiệp vụ hay API. Tài liệu nhắc tới đường dẫn code được sửa cùng PR của ticket chạm tới nó.

## Quyết định

| Chủ đề | Quyết định |
|---|---|
| Thứ tự | 3 ticket nối tiếp, mỗi ticket một PR và CI xanh: đưa lên gốc repo → đổi Django app → sắp test |
| Migration | Sinh lại từ đầu ở ticket 02, không viết migration chuyển dữ liệu. Mỗi dev chạy `make db-reset` một lần sau khi merge |
| `infrastructure/` | Chưa tạo: chưa có adapter nào. Package, lớp `infrastructure` trong contract `layers` và contract "chỉ module sở hữu import" được tạo cùng adapter đầu tiên (VNPay/MoMo, GHN hoặc Google) |
| Tài liệu | ADR 0006, 0017 và `.scratch/` là lịch sử, không sửa đường dẫn trong đó |

## Ticket

1. [`01-flatten-repo-root/`](./issues/01-flatten-repo-root/spec.md): đưa Django project từ `backend/` lên gốc repo.
2. [`02-django-apps/`](./issues/02-django-apps/spec.md): `shared` → `common` + `apps/geo`, `modules` → `apps/identity`, sinh lại migration.
3. [`03-mirror-test-layout/`](./issues/03-mirror-test-layout/spec.md): đặt lại vị trí và tên file test theo quy tắc soi gương.

## Ngoài phạm vi

- Viết module mới hoặc adapter bên thứ ba.
- Đổi tên repo trên GitHub.
