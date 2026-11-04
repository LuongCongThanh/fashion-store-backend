# Kế hoạch thực hiện ticket 01

Spec: [spec.md](./spec.md)

Mode đề xuất: `full`

## Slice

| Slice | AC | Seam và bằng chứng red/green | File chính | Phụ thuộc | Commit dự kiến |
|---|---|---|---|---|---|
| S1 — Auth foundation | AC3, AC7 | Config/startup tests; token codec security matrix: thiếu/sai claim, `kid`, alg, issuer, audience, purpose, expiry/future `iat` | `pyproject.toml`, `uv.lock`, `.env.example`, `config/env.py`, `config/settings/base.py`, `modules/identity/auth/tokens.py`, tests | — | `feat: add backoffice token foundation` |
| S2 — Refresh persistence | AC4, AC7 | Model/migration tests cho field, constraint, index; chứng minh login chưa tạo replay ở slice sau | `modules/identity/models/auth.py`, exports, migration, model tests | S1 | `feat: add refresh token persistence` |
| S3 — Atomic failure ledger | AC2, AC5, AC7 | Unit + integration/concurrency tests cho reserve/complete, boundary 5/20, lease, `Retry-After`, HMAC key và Redis fail-open metric | `modules/identity/auth/login_attempts.py`, tests | S1 | `feat: add login failure ledger` |
| S4 — Login capability | AC1, AC2, AC4, AC5, AC7 | Service tests và API tests: Staff/Admin success, Customer/inactive/missing/wrong password cùng lỗi; refresh hash/family được lưu, replay không được tạo | `modules/identity/services/auth.py`, DTO/serializers/views/urls, `config/urls.py`, exceptions, tests | S1–S3 | `feat: add backoffice login endpoint` |
| S5 — Bearer auth và auth/me | AC1, AC3, AC6, AC7 | API security matrix bằng JWT thật; DB lookup mỗi request; kind/tv/inactive mismatch; DB unavailable 503; OpenAPI 200/401/403/429/500/503 | `modules/identity/auth/authentication.py`, backoffice API, `shared/api/schema.py`, settings, `openapi.yaml`, fixtures/tests | S4 | `feat: protect backoffice authentication` |

## TDD và kiểm chứng

- Mỗi slice bắt đầu bằng test đỏ đúng capability chưa tồn tại hoặc assertion hành vi, rồi code tối
  thiểu để xanh và refactor.
- Test migration/schema dùng PostgreSQL; concurrency failure ledger dùng Redis thật khi cần chứng
  minh atomic, còn lỗi Redis test qua adapter giả.
- Flow acceptance gọi login rồi dùng access token thật gọi `auth/me`; không dùng
  `force_authenticate` để chứng minh JWT.
- Sau từng slice chạy targeted tests. Gate cuối chạy `make fmt`, `make lint`, identity/shared
  targeted tests, migration check và OpenAPI check; full suite trước merge.

## Mapping tài liệu

| Khu vực file | Tài liệu chi phối |
|---|---|
| Config/dependency | `02-backend-structure.md::3.1,5`; `05-auth-security.md::2,3`; `13-python-django-coding-style.md::2,6` |
| Models/migration | `03-data-model.md::2.4,2.5`; `13-python-django-coding-style.md::7`; ADR 0014 |
| Token/authentication | `05-auth-security.md::2,2.2,2.3,4`; ADR 0002; `13-python-django-coding-style.md::4,10` |
| Failure ledger | `05-auth-security.md::3,5,8,9`; ADR 0016; `12-testing-strategy.md::2.2,2.5` |
| Service/API/OpenAPI | `04-api-contract.md::3,4.2,5.1,5.4`; `12-testing-strategy.md::2.1,2.4,5`; `13-python-django-coding-style.md::3.1,4,9` |

## Ngoài phạm vi

- Refresh rotation/replay, logout và purge job thuộc ticket 02.
- Storefront login/registration và Google login không nằm trong ticket này.
- Không thay đổi cấu trúc thư mục `module-plans` theo yêu cầu người dùng; state script của skill
  không quản lý được ticket này nên phase được theo dõi trong chính spec/plan/report.
