# 01 — Staff/Admin đăng nhập back-office

**What to build:** Staff hoặc Admin nhập đúng email/mật khẩu tại back-office và nhận một cặp access/refresh token đúng audience. Customer, tài khoản vô hiệu hoặc credential sai nhận cùng lỗi đăng nhập chung; token back-office gọi được endpoint được bảo vệ.

Blocked by: None — can start immediately.

Status: ready-for-agent

**PR:** —

## Việc cần làm

- Thêm dependency và typed configuration cho JWT Ed25519, Argon2 và các TTL/audience.
- Tạo schema refresh token/replay, token codec, failure ledger, login service và HTTP adapter.
- Thêm `JWTAuthentication`, endpoint `auth/me`, OpenAPI và security matrix.

## Quyết định

Chốt khi grilling ngày 04/11/2026; chờ duyệt G1 trước khi viết code.

| Chủ đề | Quyết định |
|---|---|
| Mode | `full`: ticket có migration, hai endpoint và security/concurrency matrix. |
| Interface / seam | `tokens.py` cung cấp function phát/xác minh token thuần; `login_attempts.py` cung cấp `reserve`, `complete_failure`, `complete_success`. Đây là seam cho crypto clock và Redis failure injection; bỏ các seam này sẽ trộn crypto/Redis vào service và làm test lỗi hạ tầng phụ thuộc dịch vụ thật. |
| JWT | Ed25519 qua PyJWT 2.15.1; `kid` chỉ chọn key nội bộ; decode allow-list `EdDSA`, kiểm đủ claim/type/audience/purpose và leeway 30 giây. Access sống 10 phút, refresh back-office 12 giờ. |
| Key config | Keyring signing chứa `kid`, private/public key; key đầu phát token mới, mọi public key còn lại dùng verify. Startup check từ chối keyring rỗng, `kid` trùng/sai và TTL không dương. `.env.example` chỉ dùng placeholder. |
| Password | `Argon2PasswordHasher` đứng đầu production; giữ các hasher mặc định để đọc hash cũ. Email không tồn tại vẫn chạy dummy password verification và dùng cùng lỗi `INVALID_CREDENTIALS`. |
| Refresh persistence | Schema theo `docs/architecture/03-data-model.md::2.4-2.5`; login lưu SHA-256 của refresh token và family, không lưu token thô, không tạo `RefreshReplay`. |
| Failure ledger | Redis Lua atomic với reservation có lease; hạn mức 5 failure/email và 20 failure/IP trong cửa sổ trượt 15 phút. Key dùng `pii_hmac`; Redis lỗi fail-open và tăng metric không chứa định danh. |
| DB auth state | `JWTAuthentication` xác minh token rồi đọc `Account` từ PostgreSQL ở mọi request back-office, đối chiếu `is_active`, `kind`, `token_version`; lỗi DB thành `503 AUTH_STATE_UNAVAILABLE`. |
| HTTP contract | `POST /api/v1/backoffice/auth/login` là `AllowAny`; `GET /api/v1/backoffice/auth/me` dùng `JWTAuthentication` + `IsStaff`; lỗi credential/kind/inactive dùng cùng body. |
| Tài liệu chi phối | `docs/architecture/02-backend-structure.md::5`; `docs/architecture/03-data-model.md::2.1,2.4,2.5`; `docs/architecture/04-api-contract.md::4.2,5.1,5.4`; `docs/architecture/05-auth-security.md::2-5,8-9`; `docs/architecture/12-testing-strategy.md::2.1,2.2,2.4,2.5,5,6`; `docs/architecture/13-python-django-coding-style.md::3.1,4,7,9,10`; `docs/adr/0002-auth-nextauth-session-django-jwt.md`; `docs/adr/0014-refresh-single-successor.md`; [research](../../research/backoffice-auth-libraries.md). |
| Baseline | `make lint` xanh; `python -m pytest modules/identity/tests -q` xanh 28 test. `uv run pytest` bị Windows Application Control chặn shim nên dùng `uv run python -m pytest`. |

## Acceptance criteria

- [ ] **AC1:** Staff và Admin đăng nhập thành công, nhận đủ `TokenPairDTO` và dùng access token gọi `GET backoffice/auth/me`, endpoint trả `AccountDTO`.
- [ ] **AC2:** Customer, tài khoản vô hiệu, email/mật khẩu sai bị từ chối mà không lộ nguyên nhân.
- [ ] **AC3:** Token có đúng issuer/audience/`token_use`/kid/expiry và claims bắt buộc; token sai mục đích/audience/algorithm bị từ chối.
- [ ] **AC4:** `RefreshToken` và `RefreshReplay` có schema đúng data model; login chỉ tạo refresh family/hash, chưa tạo replay record và không lưu/log token thô.
- [ ] **AC5:** Failure ledger giới hạn đăng nhập sai theo email/IP, atomic khi Redis hoạt động, trả đúng `Retry-After` và fail-open có metric khi Redis lỗi.
- [ ] **AC6:** Mọi request back-office đọc trạng thái auth từ PostgreSQL; DB không xác minh được trả `503 AUTH_STATE_UNAVAILABLE`.
- [ ] **AC7:** OpenAPI và security/API tests chứng minh đầy đủ hành vi trên.
