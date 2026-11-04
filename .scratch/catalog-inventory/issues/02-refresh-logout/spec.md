# 02 — Xoay refresh token và đăng xuất

**What to build:** Người dùng back-office có thể dùng refresh token để nhận đúng một successor và đăng xuất để family hiện tại không cấp thêm token. Retry hợp lệ trong cửa sổ nhận lại đúng response; reuse đáng ngờ thu hồi family.

Status: resolved · Blocked by: [01](../01-backoffice-login/spec.md), [one-app-per-module/03](../../../one-app-per-module/issues/03-mirror-test-layout/spec.md) · **PR:** #73

## Việc cần làm

- Tách kết quả phát token khỏi DTO output, thêm `decode_refresh_token` và phát token trong family có sẵn.
- Cấu hình khoá AESGCM cho RefreshReplay, mã hoá/giải mã response với AAD và deploy check.
- Service refresh rotation (khoá Account → RefreshToken, một successor, replay 10 giây, REFRESH_SUPERSEDED, thu hồi family) và service logout.
- Endpoint `POST backoffice/auth/refresh`, `POST backoffice/auth/logout`, OpenAPI và `openapi.yaml`.
- Job `identity.purge_refresh_replays` mỗi phút.

## Quyết định

Chốt khi grilling ngày 04/11/2026.

| Chủ đề | Quyết định |
|---|---|
| Mode | `full`: hai endpoint mới, cấu hình khoá mới, concurrency và crypto test. |
| Interface / seam | `auth/tokens.py`: `issue_token_pair(*, account, audience, now, family_id=None) -> IssuedTokenPair` (mang thêm `refresh_jti`, `family_id`, `refresh_expires_at` để lưu DB) và `TokenPairDTO` chỉ còn 4 field output; `decode_refresh_token(token, *, expected_audience, now, verify_exp=True) -> RefreshClaimsDTO`; `decode_access_token` bắt buộc `now`. `auth/replay_crypto.py`: `encrypt_replay(payload, *, parent_jti, family_id, audience) -> SealedReplay` và `decrypt_replay(sealed, *, parent_jti, family_id, audience) -> bytes`, ném `ReplayUnavailable` khi thiếu khoá, sai `key_id` hay giải mã lỗi. `services/auth.py`: `refresh_session(*, refresh_token, audience, now) -> TokenPairDTO` và `logout_session(*, refresh_token, audience, now) -> None`; nhận `audience` để storefront (M6) dùng lại, ticket này chỉ mở endpoint back-office. Seam test: service với `now` truyền vào, crypto thuần, endpoint qua `APIClient`. |
| Khoá replay | Một khoá theo 08 mục 2.3: `REFRESH_REPLAY_KEY_ID` (≤ 32 ký tự) + `REFRESH_REPLAY_KEY_PATH` (file đúng 32 byte), `config/env.py` đọc và kiểm lúc khởi động, lỗi không lộ nội dung khoá. Thiếu khoá được phép ở dev/test; deploy check `common.E003` chặn khi `check --deploy`. Xoay khoá chỉ làm replay đang trong cửa sổ ≤ 10 giây trả 503, không cấp nhánh mới. |
| Mã hoá | `cryptography` AESGCM, nonce `os.urandom(12)` mỗi lần encrypt, AAD = `parent_jti|family_id|aud`. Plaintext là JSON của `TokenPairDTO`. Không log token, nonce, ciphertext. |
| Refresh | Trong `transaction.atomic`: decode chữ ký/claim, `select_for_update` Account rồi RefreshToken theo `jti`; kiểm hash, `is_active`, `kind`, `tv`, chưa hết hạn, family chưa thu hồi. Lần đầu: phát cặp mới cùng family, lưu RefreshToken mới, `used_at = now`, `successor_jti`, RefreshReplay `expires_at = used_at + 10 giây`. Đã dùng và `now < replay.expires_at`: successor đã dùng hoặc đã thu hồi → `409 REFRESH_SUPERSEDED`; không thì giải mã trả đúng cặp cũ, không gia hạn. Đã dùng và ngoài cửa sổ → thu hồi family, xoá replay, `401 NOT_AUTHENTICATED` (commit thu hồi trước khi trả lỗi). |
| Mã lỗi refresh | Sai chữ ký/audience/`token_use`/claim, hash lệch, không có dòng, family đã thu hồi, Tài khoản vô hiệu hay lệch `kind`/`tv` → `401 NOT_AUTHENTICATED`; hết hạn → `401 TOKEN_EXPIRED`; DB lỗi → `503 AUTH_STATE_UNAVAILABLE`; trong cửa sổ mà mất/hỏng ciphertext hoặc thiếu khoá, hoặc lần đầu mà thiếu khoá → `503 REFRESH_REPLAY_UNAVAILABLE` (mã mới, bổ sung bảng lỗi 04 mục 3). |
| Logout | Chữ ký, audience, `token_use` phải đúng (sai → 401); bỏ qua `exp`. Khoá Account rồi token của family, đặt `revoked_at` cho token chưa thu hồi, xoá RefreshReplay của family; family đã thu hồi hay `jti` không có trong DB vẫn `204`. Không tăng `tv`, không đụng family khác. |
| Model | Theo 13 mục 7.1: `RefreshToken.mark_used(*, successor, now)`, classmethod `RefreshToken.revoke_family(family_id, *, now)`; QuerySet chỉ chứa vị từ (`unrevoked()`, `RefreshReplay` `expired(now)`). Không đổi schema, không migration. |
| Purge | `identity.purge_refresh_replays` (`apps/identity/tasks.py`, queue `default`, mỗi phút trong `config/celery.py`) xoá RefreshReplay có `expires_at <= now`, log số dòng. Endpoint vẫn kiểm hạn trước decrypt. Theo yêu cầu người dùng 04/11/2026. |
| HTTP contract | Hai view `authentication_classes = ()`, `AllowAny`, throttle mặc định; `RefreshInput`/`LogoutInput` `{refresh_token}`; refresh `200 TokenPairDTO`, logout `204`. Vì `AllowAny` nên view tự khai 401, 409, 503 kèm ví dụ `ErrorDTO` (04 mục 5.6). |
| `shared` | Sửa `shared/checks.py` (thêm `common.E003`) và `shared/tests/test_api_schema.py` (danh sách operation, ví dụ lỗi đã khai). |
| Lệch so với ticket | AC "Crypto/concurrency/API/OpenAPI tests…" tách thành AC5 (crypto) và AC6 (HTTP, OpenAPI, không lộ token); thêm AC7 (purge) và AC8 (tách `TokenPairDTO`, backlog của 01) theo yêu cầu người dùng. |
| Tài liệu chi phối | `docs/adr/0014-refresh-single-successor.md`; `docs/adr/0002-auth-nextauth-session-django-jwt.md`; `docs/architecture/05-auth-security.md::2.1`; `docs/architecture/05-auth-security.md::2.2`; `docs/architecture/05-auth-security.md::9`; `docs/architecture/03-data-model.md::2.4`; `docs/architecture/03-data-model.md::2.5`; `docs/architecture/04-api-contract.md::3`; `docs/architecture/04-api-contract.md::5.5`; `docs/architecture/04-api-contract.md::5.6`; `docs/architecture/07-async-events-jobs.md::3.2`; `docs/architecture/08-local-development.md::2.3`; `docs/architecture/12-testing-strategy.md::2.1`; `docs/architecture/12-testing-strategy.md::2.2`; `docs/architecture/12-testing-strategy.md::2.4`; `docs/architecture/12-testing-strategy.md::2.5`; `docs/architecture/13-python-django-coding-style.md::3.1`; `docs/architecture/13-python-django-coding-style.md::4`; `docs/architecture/13-python-django-coding-style.md::5.2`; `docs/architecture/13-python-django-coding-style.md::7.1`; `docs/architecture/13-python-django-coding-style.md::9`; `docs/architecture/13-python-django-coding-style.md::10`. |
| Baseline | `make test` xanh trên `origin/dev` (db6a51a). Container worker/beat/relay chưa chạy vì PostgreSQL khởi động trước Docker; không ảnh hưởng test, người dùng sửa sau. |

## Acceptance criteria

- [x] **AC1:** Refresh lần đầu cấp một TokenPair mới cùng family và đánh dấu predecessor (`used_at`, `successor_jti`, RefreshReplay) trong cùng transaction.
- [x] **AC2:** Hai refresh đồng thời chỉ tạo một successor; retry trong 10 giây trả đúng cặp đã cấp, không gia hạn cửa sổ.
- [x] **AC3:** Successor đã dùng trả `409 REFRESH_SUPERSEDED`; reuse ngoài cửa sổ thu hồi family; family đã thu hồi, Tài khoản vô hiệu/lệch `tv` bị từ chối; mất ciphertext hoặc thiếu khoá trả `503 REFRESH_REPLAY_UNAVAILABLE` mà không cấp nhánh mới (ADR 0014).
- [x] **AC4:** Logout thu hồi family và xoá replay, trả 204 idempotent, không cần access token còn hạn và không đụng family khác.
- [x] **AC5:** Replay mã hoá AESGCM bằng khoá riêng: khoá khác, AAD sai, ciphertext bị sửa đều không giải mã được; cấu hình khoá sai bị từ chối khi khởi động và `check --deploy` chặn khi thiếu khoá.
- [x] **AC6:** API và OpenAPI của refresh/logout đúng hợp đồng (200/204, 401/409/503 có ví dụ); log và body lỗi không chứa token hay ciphertext.
- [x] **AC7:** Job `identity.purge_refresh_replays` mỗi phút xoá replay hết hạn và giữ replay còn hạn.
- [x] **AC8:** `TokenPairDTO` chỉ còn field output, kết quả phát token mang dữ liệu lưu DB; `decode_access_token` bắt buộc `now`.
