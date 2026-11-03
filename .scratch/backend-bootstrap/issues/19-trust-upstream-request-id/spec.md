# Dùng `X-Request-ID` từ BFF làm `request_id`

Status: ready-for-agent

Blocked by: 16

Spec: [spec.md](../../spec.md)

Tách từ ticket [16](../16-shared-api-layer/spec.md) khi grilling ngày 29/10/2026.

## Bối cảnh

[10-nfr](../../../../docs/architecture/10-nfr.md) ghi `request_id` lấy từ `X-Request-ID` nếu có, không có thì tự sinh. Hiện `django-structlog` luôn tự sinh vì `DJANGO_STRUCTLOG_TRUST_UPSTREAM_REQUEST_ID` mặc định `False`. Bật cờ đó thì client bất kỳ cũng đặt được `request_id`; nên chỉ tin header khi `X-BFF-Secret` khớp (middleware `client_ip` của ticket 16).

## Việc cần làm

- Chọn cách tin `X-Request-ID` chỉ khi secret BFF đúng, kiểm định dạng và độ dài.
- Trả `X-Request-ID` trong response nếu tài liệu yêu cầu.

## Quyết định

Chốt khi grilling ngày 03/11/2026.

| Chủ đề | Quyết định |
|---|---|
| Tài liệu chi phối | `backend/shared/api/client_ip.py` → `docs/architecture/05-auth-security.md::5`, `docs/adr/0009-nextjs-bff-django-private.md`. `backend/shared/api/request_id.py` (mới) → `docs/architecture/10-nfr.md::4`, `docs/architecture/05-auth-security.md::8`, `docs/architecture/13-python-django-coding-style.md::10`. `backend/shared/apps.py` → `docs/architecture/02-backend-structure.md::5`. `backend/shared/tests/test_api_request_id.py` → `docs/architecture/12-testing-strategy.md::2.4`, `docs/architecture/13-python-django-coding-style.md::9`. Phase sync sửa 10 §4 (chỉ tin header khi secret BFF đúng) và thêm dòng `request_id.py` vào cây 02 §5. |
| Cơ chế | Receiver cho signal `bind_extra_request_metadata` của `django-structlog` 11.0.0, nối trong `SharedConfig.ready()`. Signal chạy sau khi thư viện bind `request_id` tự sinh và trước log `request_started`, nên rebind ở đây thì mọi dòng log, `error.request_id` (`current_request_id()`) và `correlation_id` của sự kiện cùng dùng giá trị mới. Không bật `DJANGO_STRUCTLOG_TRUST_UPSTREAM_REQUEST_ID` (thư viện không kiểm secret hay định dạng); không subclass `RequestMiddleware`, giữ nguyên `MIDDLEWARE`. |
| Interface / seam | `client_ip.py`: `_secret_matches(provided)` thành `bff_secret_matches(request: HttpRequest) -> bool` (đọc `X-BFF-Secret`, so mọi secret bằng `hmac.compare_digest`, không dừng sớm); `resolve_client_ip` và receiver cùng gọi, nên chỉ một chỗ giữ quy tắc tin BFF. Deletion test: bỏ hàm thì logic so secret lặp ở hai file. Không gán cờ lên request để không phụ thuộc thứ tự middleware. Seam test là HTTP request qua `APIClient` tới route test `shared.tests.api_urls`. |
| Định dạng | Nhận `X-Request-ID` khớp `[A-Za-z0-9._-]{1,64}` (đủ cho UUID, ULID, trace id). Secret đúng nhưng header sai định dạng hoặc quá dài: giữ `request_id` tự sinh, log `WARNING` `request_id_invalid` không kèm giá trị header. Secret đúng mà không có header: giữ giá trị tự sinh, không log. |
| Thiếu / sai secret | Bỏ qua header, giữ `uuid4` của thư viện, không log (AC2). |
| Response header | Không trả `X-Request-ID` trong response vì tài liệu không yêu cầu (khác *Việc cần làm*: mục đó chỉ làm "nếu tài liệu yêu cầu"). Ghi một dòng `.scratch/backlog.md`. |
| Test | `backend/shared/tests/test_api_request_id.py`, dùng hằng `BFF_SECRET`, `error_of` của `shared/tests/_helpers.py` và `override_settings(BFF_SHARED_SECRETS=…)` như `test_api_client_ip.py`; log kiểm bằng `structlog.testing.capture_logs` kèm `merge_contextvars`. Không cần factory (không có model). `test_api_client_ip.py` chạy lại để chứng minh đổi tên hàm không đổi hành vi. |

## Acceptance criteria

- [ ] Secret BFF đúng và `X-Request-ID` hợp lệ thì `error.request_id` và log dùng giá trị đó.
- [ ] Thiếu hoặc sai secret thì `request_id` được tự sinh, bỏ qua header.
