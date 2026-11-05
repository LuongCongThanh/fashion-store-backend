# Module `identity`

> Trạng thái: **Đã chốt cho MVP**, đã có code một phần (Tài khoản Staff/Admin; đăng nhập, refresh xoay vòng, đăng xuất back-office). Mục _(kế hoạch)_ chưa có code. Khuôn chung: [02 mục 4](../02-backend-structure.md#4-khuôn-mẫu-một-module).

## 1. Sở hữu

- Tài khoản (Khách hàng, Staff, Admin), xác thực JWT, xác thực email, sổ địa chỉ, đồng ý xử lý dữ liệu, Yêu cầu xoá dữ liệu.
- Lớp 3, chỉ phụ thuộc `geo` (FK địa chỉ) và `infrastructure.google`. `inventory`, `promotions`, `ordering`, `notifications` phụ thuộc vào nó.

## 2. Cây thư mục

`models`, `services` là package (Tài khoản, phiên đăng nhập, dữ liệu cá nhân độc lập nhau).

```
apps/identity/
├── apps.py                    # name = "apps.identity", label = "identity"
├── contracts.py               # (kế hoạch) mục 4.1
├── events.py                  # (kế hoạch) mục 4.2
├── exceptions.py              # mục 4.3
├── constants.py               # AccountKind…
├── models/
│   ├── account.py             # Account (AUTH_USER_MODEL = "identity.Account")
│   ├── auth.py                # RefreshToken, RefreshReplay; AccountToken (kế hoạch)
│   ├── address.py             # (kế hoạch) Address, FK tới geo.Ward
│   └── privacy.py             # (kế hoạch) Consent, ErasureRequest, CustomerDataAccessLog
├── services/
│   ├── accounts.py            # create_staff_account; register, verify_email, update_profile (kế hoạch)
│   ├── auth.py                # login_backoffice, refresh_session, logout_session; reset mật khẩu, login_with_google (kế hoạch)
│   └── privacy.py             # (kế hoạch) record_consent, erase_customer, apply/finalize_erasure_request
├── auth/                      # adapter hạ tầng riêng của identity
│   ├── tokens.py              # phát hành, kiểm tra access/refresh/lookup JWT (Ed25519, kid)
│   ├── authentication.py      # JWTAuthentication cho DRF (back-office)
│   ├── login_attempts.py      # failure ledger đăng nhập trên Redis
│   └── replay_crypto.py       # mã hoá AES-GCM response refresh để replay (ADR 0014)
├── tasks.py                   # purge_refresh_replays; job khác (kế hoạch), mục 5.4
├── api/
│   ├── backoffice/            # POST auth/login, auth/refresh, auth/logout; GET auth/me
│   └── store/                 # (kế hoạch) đăng ký, đăng nhập, Google, hồ sơ, sổ địa chỉ
├── management/commands/
│   └── create_staff.py        # tạo Tài khoản Staff/Admin
├── migrations/                # migration đầu tiên phải có Account
└── tests/                     # soi gương cây ở trên; factories.py; concurrency/ (login ledger, refresh)
```

## 3. Quan hệ với module khác

```mermaid
graph LR
    identity((identity)) -->|"FK Address → Ward"| geo
    identity -->|"verify_id_token"| google[infrastructure.google]

    ordering -->|"find_verified_customer_id, record_consent<br/>issue/verify_order_lookup_token<br/>apply_erasure_request, get_erasure_subject<br/>log_customer_data_access"| identity
    notifications -->|"get_customer, get_erasure_subject<br/>issue_*_link"| identity
    inventory -->|"FK actor → Account"| identity
    promotions -->|"FK customer → Account<br/>get_erasure_subject"| identity

    identity -.->|"customer-registered<br/>verification-email-requested<br/>registration-attempted<br/>password-reset-requested"| notifications
    identity -.->|"email-verified"| ordering
    identity -.->|"customer-erased"| ordering
    identity -.->|"customer-erased"| promotions
    identity -.->|"customer-erased"| notifications
```

## 4. Public API

### 4.1. `contracts.py` _(kế hoạch)_

DTO:

- `CustomerDTO`: `id: UUID`, `email: str`, `full_name: str`, `language: Language`, `email_verified: bool`, `is_active: bool`. Tài khoản đã ẩn danh trả `is_active = false` và email `erased+<id>@invalid`; bên gọi không gửi email tới địa chỉ này.
- `LookupTokenClaimsDTO`: `order_code: str`, `expires_at: datetime`. Khác `OrderLookupDTO` của API ([04 mục 5.2](../04-api-contract.md#52-schema-dùng-chung-và-checkout)).
- `ErasureSubjectDTO`: `erasure_request_id: UUID`, `account_id: UUID | None`, `email: str` (email Tài khoản trước ẩn danh, `''` với Khách vãng lai), `phone: str` (E.164, `''` khi yêu cầu theo Tài khoản). Đọc được suốt `processing`, kể cả khi Tài khoản đã ẩn danh ([03 mục 10](../03-data-model.md#10-ẩn-danh-dữ-liệu-cmp-05)).

| Hàm | Ai gọi | Ghi chú |
|---|---|---|
| `get_customer(account_id: UUID) -> CustomerDTO` | notifications | |
| `find_verified_customer_id(email: str) -> UUID \| None` | ordering | Checkout gắn đơn của Khách vãng lai vào Tài khoản đã xác thực (BR-ORD-08) |
| `issue_order_lookup_token(order_code: str, now: datetime) -> str` | ordering | Mục 5.2 |
| `verify_order_lookup_token(token: str, now: datetime) -> LookupTokenClaimsDTO` | ordering | Ném `InvalidLookupToken`; `ordering` tự kiểm Mã đơn khớp URL |
| `issue_email_verification_link(account_id: UUID) -> str`, `issue_password_reset_link(account_id: UUID) -> str` | notifications | Sinh token lúc gửi email, không lúc phát sự kiện |
| `record_consent(account_id: UUID \| None, subject_phone: str, purpose: ConsentPurpose, policy_version: str, channel: ConsentChannel, granted: bool) -> None` | ordering (checkout, cùng transaction tạo đơn); `identity` tự gọi khi đăng ký, sửa hồ sơ | Chỉ thêm dòng. Cần `account_id` hoặc `subject_phone` |
| `get_erasure_subject(erasure_request_id: UUID) -> ErasureSubjectDTO` | service của ordering, promotions, notifications khi xử lý `customer-erased` | Lấy đối tượng cần ẩn danh |
| `apply_erasure_request(erasure_request_id: UUID, staff_id: UUID) -> ErasureStatus` | chỉ ordering | Sau khi ordering kiểm CMP-05; ghi `processing` và phát sự kiện, chưa ghi `completed_at`. Gọi lại khi đã `processing`/`completed` trả trạng thái hiện tại |
| `log_customer_data_access(staff_id: UUID, customer_id: UUID \| None, subject_phone: str, order_code: str, action: DataAccessAction) -> None` | ordering | CMP-07 |

### 4.2. `events.py` _(kế hoạch)_

Payload không mang token hay PII ([07 mục 2](../07-async-events-jobs.md#2-danh-mục-sự-kiện)).

| Sự kiện | `event_type` | Payload | Phát khi |
|---|---|---|---|
| `CustomerRegisteredV1` | `identity.customer-registered` | `account_id: UUID`, `language: Language` | Đăng ký mới |
| `VerificationEmailRequestedV1` | `identity.verification-email-requested` | `account_id: UUID` | Gửi lại email xác thực, hoặc đăng ký lại bằng email chưa xác thực |
| `RegistrationAttemptedV1` | `identity.registration-attempted` | `account_id: UUID` | Đăng ký bằng email đã thuộc Tài khoản đã xác thực hoặc Tài khoản nội bộ (US-501 AC2) |
| `EmailVerifiedV1` | `identity.email-verified` | `account_id: UUID` | Email chuyển sang đã xác thực, từ `verify_email` hoặc `login_with_google` |
| `PasswordResetRequestedV1` | `identity.password-reset-requested` | `account_id: UUID` | Yêu cầu đặt lại mật khẩu |
| `CustomerErasedV1` | `identity.customer-erased` | `erasure_request_id: UUID` | Yêu cầu xoá dữ liệu bắt đầu xử lý |

### 4.3. `exceptions.py`

- Tài khoản: `EmailAlreadyUsed`, `InvalidEmail`, `WeakPassword`.
- Đăng nhập và phiên: `InvalidCredentials`, `RefreshRejected`, `RefreshExpired`, `RefreshSuperseded`, `RefreshReplayUnavailable`, `SessionStateUnavailable`.
- _(kế hoạch)_ `InvalidLookupToken`; thêm lỗi khi làm các luồng còn lại.

## 5. Quy tắc riêng

### 5.1. Tài khoản

- `Account` là custom user, phải nằm trong migration đầu tiên của `identity`. Field: email duy nhất cho mọi `kind` (một email là một Tài khoản), `kind` (`customer` / `staff` / `admin`), `language`, `token_version`, `is_active`, `email_verified`, `anonymized_at`.
- `create_staff_account` (lệnh `create_staff`, back-office US-1001) kiểm email, độ mạnh mật khẩu, email trùng.
- `update_profile` đổi họ tên, số điện thoại, ngôn ngữ; không đổi email.

### 5.2. Token và đăng nhập

- `auth/tokens.py` là hàm thuần, nhận `now` từ caller. Access/refresh/lookup token có validator loại trừ nhau ([05](../05-auth-security.md)).
- **Lookup token** (tra cứu đơn): JWT Ed25519; bắt buộc `iss`, `aud = order_lookup`, `token_use = lookup`, `sub` (Mã đơn), `iat`, `exp` (30 phút); chỉ chấp nhận EdDSA và `kid` đã cấu hình.
  - DTO chỉ trả Mã đơn và hạn token; `ordering` tự kiểm Mã đơn khớp URL.
  - `identity` không truy vấn model Đơn hàng; `ordering` không import `identity.auth`.
- `JWTAuthentication` xác minh access token `aud = backoffice`, rồi đọc `Account` từ PostgreSQL mỗi request. Khai theo từng view bằng `authentication_classes`; `DEFAULT_AUTHENTICATION_CLASSES` để rỗng ([05](../05-auth-security.md) mục 4).
- **Login ledger** (05 mục 5): `reserve`, `complete_failure`, `complete_success`, `release`; Lua atomic trên Redis, fail-open khi Redis lỗi.
- `refresh_session` xoay vòng refresh token, mỗi token có đúng một token kế tiếp; `logout_session` thu hồi cả family. `RefreshToken` lưu `jti`, `family_id`, `token_hash`, `expires_at`, `used_at`, `successor_jti`, `revoked_at`; `RefreshReplay` giữ response mã hoá (`auth/replay_crypto.py`) 10 giây để trả lại cho request trùng ([ADR 0014](../../adr/0014-refresh-single-successor.md)).
- `AccountToken` (đặt lại mật khẩu, xác thực email) phân biệt bằng `purpose`, chỉ lưu hash.

### 5.3. Đăng nhập Google _(kế hoạch)_

- `infrastructure.google` chỉ xác minh `id_token`; nghiệp vụ nằm trong `services/auth.py`.
- Khớp Tài khoản có `email_verified = false`: đánh dấu đã xác thực, `set_unusable_password`, tăng `token_version`, thu hồi mọi refresh token.
- Tạo Tài khoản mới hoặc đánh dấu đã xác thực thì phát `EmailVerifiedV1`.

### 5.4. Dữ liệu cá nhân và job

- _(kế hoạch)_ `reconcile_erasure_requests` (mỗi phút) gọi `finalize_erasure_request`: đối chiếu delivery của các handler bắt buộc qua `common.events`, hoàn tất yêu cầu `processing`. Không truy vấn model của module khác.
- Khi hoàn tất, thay `subject_phone` bằng `subject_phone_hmac` trên ErasureRequest, Consent, CustomerDataAccessLog cùng transaction ([ADR 0016](../../adr/0016-erasure-evidence-phone-hmac.md)). HMAC dùng chung: `common.security.privacy.pii_hmac`.
- `purge_refresh_replays` (mỗi phút, đã có) và `purge_expired_tokens` (hằng ngày, _(kế hoạch)_) xoá dữ liệu token hết hạn.

## 6. Tài liệu liên quan

- Schema: [03 mục 2](../03-data-model.md#2-identity)
- Xác thực, JWT, BFF, throttle: [05](../05-auth-security.md); [ADR 0002](../../adr/0002-auth-nextauth-session-django-jwt.md), [ADR 0014](../../adr/0014-refresh-single-successor.md)
- Google OAuth: [06](../06-integrations.md) mục 5
- Ẩn danh dữ liệu: [03 mục 10](../03-data-model.md), [ADR 0016](../../adr/0016-erasure-evidence-phone-hmac.md)
