# 02 – Xoay refresh token và đăng xuất

Status: ready-for-agent · Ưu tiên: 5 · Blocked by: [01](../01-backoffice-login/spec.md), [one-app-per-module/03](../../../one-app-per-module/issues/03-mirror-test-layout/spec.md) · **PR:**

## Mục tiêu
Người dùng back-office dùng refresh token để nhận đúng một successor, và đăng xuất để family hiện tại không cấp thêm token.

## Việc cần làm
- [ ] Đọc [ADR 0014](../../../../docs/adr/0014-refresh-single-successor.md), vẽ state R1→R2→R3.
- [ ] `modules/identity/auth/tokens.py`: validate refresh, phát successor (token codec thuần).
- [ ] `modules/identity/services/auth.py`: service refresh — khoá `Account` rồi token, tạo successor + `RefreshReplay` mã hoá trong cùng transaction.
- [ ] `modules/identity/api/` (`serializers.py`, `views.py`, `urls.py`): `RefreshInput`/`LogoutInput`, `POST auth/refresh`, `POST auth/logout`.
- [ ] Service + API logout: thu hồi family/replay, trả 204.
- [ ] `modules/identity/tasks.py` + Celery schedule: purge replay hết hạn.
- [ ] Làm xanh test do mentor viết: happy path → concurrent/retry/superseded/reuse → logout.

## Quyết định
- Một predecessor chỉ có một successor; retry trong 10 giây trả lại đúng cặp đã cấp; successor đã dùng → `409 REFRESH_SUPERSEDED`; reuse ngoài cửa sổ thu hồi family — [ADR 0014](../../../../docs/adr/0014-refresh-single-successor.md), [05 §2.1](../../../../docs/architecture/05-auth-security.md).
- Thứ tự khoá: `Account` → refresh token (`select_for_update`).
- Replay response mã hoá AESGCM có AAD; schema theo [03 §2.4–2.5](../../../../docs/architecture/03-data-model.md).
- Logout dùng refresh token đúng audience, không cần access token còn hạn — [04-api-contract](../../../../docs/architecture/04-api-contract.md).
- Service giữ transaction/row lock; view/serializer chỉ là HTTP boundary.

## Acceptance criteria
- [ ] Refresh lần đầu cấp một `TokenPair` mới và đánh dấu predecessor trong đúng transaction.
- [ ] Hai refresh đồng thời chỉ tạo một successor; retry trong 10 giây trả đúng cặp đã cấp.
- [ ] Successor đã dùng hoặc reuse ngoài cửa sổ xử lý đúng ADR 0014.
- [ ] Logout thu hồi family/replay và trả 204; không cần access token còn hạn.
- [ ] Test crypto/concurrency/API/OpenAPI chứng minh hành vi; không lộ token/ciphertext plaintext.
- [ ] `make fmt`, `make lint`, test identity và OpenAPI check xanh.

## Ghi chú
- Mentor viết test; người làm viết production code. Không gom flow vào một function dài.
- (từ backlog, ticket nguồn backend-bootstrap/12) `Account.objects.get_by_natural_key` khớp email phân biệt hoa thường; tra theo email đã chuẩn hoá hoặc `iexact`.
- (từ backlog, ticket nguồn M1/01) `TokenPairDTO` (`identity/auth/tokens.py`) trộn output API (`access_token`, `expires_in`) với dữ liệu lưu DB (`refresh_jti`, `family_id`, `refresh_expires_at`); tách thành kết quả phát token + DTO output; bắt buộc tham số `now` của `decode_access_token`.
- (từ backlog, ticket nguồn M1/01) `JWTAuthentication` query `Account` trực tiếp; chuyển sang selector `find_account` theo [13 §3.2](../../../../docs/architecture/13-python-django-coding-style.md) khi identity có `selectors.py`.
