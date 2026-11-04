# Báo cáo

### Báo cáo 04/11/2026

**Nhánh:** `feat/backoffice-login` · **PR:** #65 · **Mode:** full

#### Đã làm

Đường dẫn test tính từ `backend/modules/identity/tests/` trừ khi ghi khác.

| AC | Bằng chứng |
| --- | --- |
| 1. Staff/Admin login nhận `TokenPairDTO`, dùng access token gọi `auth/me` | `test_api_backoffice_login.py::test_backoffice_login_returns_token_pair[staff,admin]`; `test_api_backoffice_me.py::test_login_access_token_reads_me[staff,admin]`, `::test_me_permission_by_kind` |
| 2. Customer, tài khoản vô hiệu, credential sai cùng một lỗi | `test_api_backoffice_login.py::test_backoffice_login_rejects_every_case_with_same_body`, `::test_login_counts_customer_and_missing_email_as_failure`; `test_services_auth.py::test_missing_email_runs_same_password_hashing_work_as_existing_account` |
| 3. Claim, issuer, audience, `token_use`, kid, expiry; từ chối token sai mục đích/audience/alg; startup check key config | `test_services_tokens.py::test_access_token_carries_required_claims_and_header`, `::test_refresh_token_carries_family_and_twelve_hour_expiry`, `::test_decode_access_token_rejects_invalid_token[…]`, `::test_decode_access_token_rejects_missing_claim[…]`; `test_api_backoffice_me.py::test_me_rejects_*` (audience store, refresh làm Bearer, HS256, `alg=none`, kid lạ, hết hạn, header hỏng); `backend/tests/test_env.py::test_jwt_keyring_*`, `::test_jwt_durations_reject_negative`, `::test_jwt_ttl_rejects_zero`; `backend/shared/tests/test_checks.py::test_deploy_check_rejects_empty_jwt_keyring`; `test_api_backoffice_login.py::test_login_issues_token_for_configured_backoffice_audience` |
| 4. Schema `RefreshToken`/`RefreshReplay`; login chỉ lưu hash và family, không log token thô | `test_models_auth.py` (family root, successor cần `used_at`, replay unique, `::test_refresh_token_successor_is_unique`); `test_services_auth.py::test_login_stores_refresh_hash_and_family_without_logging_tokens` |
| 5. Failure ledger theo email/IP, atomic, `Retry-After`, fail-open có metric | `test_services_login_attempts.py` (biên 5/20, cửa sổ 15 phút, hoa thường, lease, `::test_retry_after_ignores_dimension_that_is_not_blocked`, `::test_retry_after_waits_until_count_drops_below_limit`, `::test_success_keeps_email_failure_recorded_after_success_time`, `::test_success_clears_email_failures_and_keeps_ip_failures`, `::test_release_frees_slot_without_recording_failure`, `::test_ledger_fails_open_when_redis_hangs`, `::test_ledger_fails_open_with_metric_event_without_identifier`); `test_concurrency_login_attempts.py::test_parallel_reservations_never_exceed_email_limit`; `test_api_backoffice_login.py::test_login_rate_limited_after_five_failures_with_retry_after`, `::test_login_server_error_does_not_hold_reservation` |
| 6. Đọc trạng thái auth từ PostgreSQL mỗi request; DB lỗi → 503 | `test_api_backoffice_me.py::test_me_reads_auth_state_from_db_each_request[tv,inactive,kind]`, `::test_me_rejects_token_of_deleted_account`, `::test_me_returns_503_when_auth_state_unavailable` |
| 7. OpenAPI và security/API tests | `test_api_backoffice_me.py::test_openapi_declares_me_auth_errors`, `::test_openapi_declares_login_errors`; `test_api_backoffice_clients.py` (fixture `staff_client`/`admin_client` dùng JWT thật) |

`make lint` xanh · `make test`: 486 passed trong 16,43s (sau rebase lên `dev` #64), coverage nhánh identity 12/12 (100%), shared 86/88 (97,73%). Test Redis thật cần `REDIS_URL` trỏ Redis chạy được trên máy (đã chạy với `redis://localhost:6380/0`; CI có service Redis).

#### Chưa làm

- Không.

#### Gap

- `shared/api/permissions.py` `IsStaff`/`IsAdmin` còn viết cứng audience `"backoffice"`; đổi `JWT_AUDIENCE_BACKOFFICE` sẽ làm `/me` trả 403. Chưa sửa vì kéo theo `IsCustomer` khi chưa có setting audience `store`.
- `JWTAuthentication` khai theo từng view (`authentication_classes`), không đặt `DEFAULT_AUTHENTICATION_CLASSES` toàn cục, để endpoint storefront công khai (`shared/geo`) không bị gắn Bearer back-office. Endpoint back-office mới phải tự khai; quên thì bị 403 (vẫn chặn).
- `JWTAuthentication` cố định audience back-office; storefront cần authenticator riêng (ticket sau).
- Test Redis thật fail (không skip) khi không có Redis; `.env` local trỏ host container `redis:6379` nên chạy test ngoài container phải đặt `REDIS_URL`.
- Thành công xoá failure email có score ≤ thời điểm thành công; lệch đồng hồ giữa các worker có thể làm lệch mốc này.
- Event log `login_failure_ledger_unavailable` (field `operation`) là nguồn metric fail-open.
- Tên component OpenAPI là `AccountOutput`/`TokenPairOutput`, tài liệu 04 viết `AccountDTO`/`TokenPairDTO`.
- Nhánh đang track `origin/dev`; push phải chỉ rõ `origin feat/backoffice-login`.

#### Thay đổi theo yêu cầu

- Hook `PreToolUse` gọi Python qua `.claude/hooks/run_py.sh` để chạy được trên Linux/macOS/Windows (commit `55cfc2d`). Kiểm: `python -m unittest discover -s .claude/hooks` 10/10 xanh.

#### Review

Ba trục (Spec, Standards, Bug) chạy song song; người dùng chọn sửa cả bốn nhóm A–D trong vòng `R1` (commit `60c2b31`). Red → green lưu ở log `r1-red-round1|2`, `r1-green-round1|2`.

| Mã | Chỗ | Kết luận | Lý do |
| --- | --- | --- | --- |
| B1/S1 | `auth/login_attempts.py` Lua reserve | đã sửa | `Retry-After` chỉ tính chiều đang vượt hạn mức |
| B2 | `auth/login_attempts.py`, `services/auth.py`, view | đã sửa | member ZSET là `uuid4`, `X-Request-ID` lặp không vô hiệu lockout |
| B3/S2 | `services/auth.py` | đã sửa | email không tồn tại băm một lần như email có thật |
| B4 | `auth/login_attempts.py::get_login_ledger` | đã sửa | client cache, timeout 0,5s, fail-open khi Redis treo |
| B5/T9 | `services/auth.py`, `conftest.py` | đã sửa | audience lấy từ settings |
| B6/S3 | `config/env.py`, `shared/checks.py` | đã sửa | keyring/TTL validator, deploy check `shared.E002` |
| B7 | `services/auth.py` | đã sửa | `ledger.release` khi exception |
| S4 | `auth/login_attempts.py` | đã sửa | test bắt event fail-open không chứa định danh |
| S5 | Lua success | đã sửa | `ZREMRANGEBYSCORE -inf now` |
| S6 | — | bác | không có scope creep |
| T1, T4, T10, T13 | `services/auth.py`, `constants.py`, ledger | đã sửa | docstring, bỏ `Any`, `BACKOFFICE_KINDS`, keyword `enforced=` |
| T2 | `config/env.py` | đã sửa | `from None`, không lộ byte key |
| T3, T11, T12 | ledger | đã sửa | `timezone.now()`, helper chạy script, bỏ thuộc tính chỉ cho test |
| T5 | tests | đã sửa | đổi tên file test theo 12::2 |
| T6, T16, T17 | tests | đã sửa | factory, fixture dùng chung, tách test, `match=` |
| T7 | tests | đã sửa | ma trận AC5 trên Redis thật và API 429 |
| T8 | `02-backend-structure.md::5`, `12-testing-strategy.md::4` | chỉ báo | sửa tài liệu ở sync |
| T12 (phần `now=None`), T14, T15 | `tokens.py`, `TokenPairDTO`, `authentication.py` | chỉ báo | smell, ghi backlog |

#### Commit

`commit_map.py` không đọc được ticket lồng trong `module-plans/`, nên bảng này lập tay từ trailer `Task:`.

| Commit | Task | Subject |
| --- | --- | --- |
| `2851a9e` | plan | docs: plan backoffice login ticket |
| `f6d5fec` | S1 | feat: add backoffice token foundation |
| `eb245fa` | S2 | feat: add refresh token persistence |
| `8c7622f` | S3 | feat: add login failure ledger |
| `55cfc2d` | — (yêu cầu thêm) | chore: run claude hooks with any available python 3 |
| `7edc1d9` | S4 | feat: add backoffice login endpoint |
| `5dd51bf` | S5 | feat: protect backoffice authentication |
| `60c2b31` | R1 | fix(identity): address review findings on backoffice login |
| `a7503ec` | sync | docs: sync docs and report for backoffice login ticket |
| `fb099aa` | ci | fix(identity): return typed reservation when ledger fails open (SonarCloud) |

#### Tài liệu đã cập nhật

- `docs/architecture/02-backend-structure.md`: `conftest.py` dùng JWT thật (bỏ `force_authenticate`, T8); `checks.py` thêm `shared.E002`; bảng identity thêm `auth/login_attempts.py`, `api/backoffice/`, `login_backoffice`, cách khai `JWTAuthentication`.
- `docs/architecture/05-auth-security.md`: mục 4 `DEFAULT_AUTHENTICATION_CLASSES` rỗng có chủ đích, view back-office tự khai; mục 5 ID suất `uuid4` (không dùng `X-Request-ID`), cách tính `Retry-After`, trả suất khi lỗi 500, event `login_failure_ledger_unavailable` là nguồn metric fail-open.
- `docs/architecture/08-local-development.md` mục 2.3: biến JWT thật (`JWT_SIGNING_KEYS`, issuer, audience, TTL, leeway) thay `JWT_PRIVATE_KEY_PATH`/`JWT_KEY_ID`.
- `docs/architecture/12-testing-strategy.md`: mục 2.2 test Redis thật (`ledger_redis`, DB 15, `REDIS_URL` trên máy) và kịch bản đăng nhập sai đồng thời; mục 4 fixture `staff_client`/`admin_client` dùng JWT thật (T8).
- `spec.md` `## Quyết định`: seam `release`, chi tiết key config, dummy verification, failure ledger và HTTP contract theo code cuối.
- `.scratch/backlog.md`: audience viết cứng trong permission; tách `TokenPairDTO` và bắt buộc `now` (T12, T14); selector `find_account` (T15).
- Code nhỏ ở sync: serializer đổi tên theo quy ước `<X>Output` + `component_name="<X>DTO"` (`LoginInput`, `TokenPairDTO`, `AccountDTO`, khớp 04 mục 5.4) và sinh lại `openapi.yaml`; comment `DEFAULT_AUTHENTICATION_CLASSES` trong `config/settings/base.py`.

#### Ghi chú cho retro

- Hook dự án gọi `python3` nên chặn mọi lệnh shell trên Windows → sửa bằng `run_py.sh` + test `RunPyWrapper` (commit `55cfc2d`).
- `state.py`/`commit_map.py`/`check_ac_trace.py` không resolve được ticket ở `.scratch/module-plans/<mốc>/issues/` → theo dõi tay; S1–S3 lọt thiếu test AC5 và lỗi ledger (B1, B2, S5) mà không check máy nào báo, review mới bắt được (finding B1, B2, T7, commit `60c2b31`).
- `run_logged.py --cwd` tính từ gốc repo; `.env` local trỏ Redis container nên test Redis thật trên máy cần `REDIS_URL=redis://localhost:6380/0`.
