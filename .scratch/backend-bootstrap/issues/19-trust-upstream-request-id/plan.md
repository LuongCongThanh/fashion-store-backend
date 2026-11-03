# Kế hoạch

Sinh bằng `plan.py` từ state của skill. Mỗi task là đúng một commit có trailer `Task: <task>`.

| Task | AC | Seam | Test dự kiến | File → tài liệu chi phối | Sau |
| --- | --- | --- | --- | --- | --- |
| S1 | 1, 2 | HTTP request qua APIClient tới route test; receiver bind_extra_request_metadata + bff_secret_matches | TDD `shared/tests/test_api_request_id.py::test_trusted_request_id_is_used_in_error_and_logs` → AssertionError<br>TDD `shared/tests/test_api_request_id.py::test_malformed_request_id_is_replaced_and_logged_with_reason` → AssertionError<br>Verify `shared/tests/test_api_request_id.py::test_request_id_header_ignored_when_bff_secret_missing`<br>Verify `shared/tests/test_api_request_id.py::test_request_id_header_ignored_when_bff_secret_wrong`<br>Verify `shared/tests/test_api_client_ip.py::test_wrong_secret_uses_remote_addr`<br>Verify `shared/tests/test_api_client_ip.py::test_valid_secret_uses_x_client_ip` | `backend/shared/api/client_ip.py` → docs/architecture/05-auth-security.md::5, docs/adr/0009-nextjs-bff-django-private.md<br>`backend/shared/api/request_id.py` → docs/architecture/10-nfr.md::4, docs/architecture/05-auth-security.md::8, docs/architecture/13-python-django-coding-style.md::10<br>`backend/shared/apps.py` → docs/architecture/02-backend-structure.md::5<br>`backend/shared/tests/test_api_request_id.py` → docs/architecture/12-testing-strategy.md::2.4, docs/architecture/13-python-django-coding-style.md::9 | — |

Commit dự kiến: `plan` → `S1` → `R1 (khi review cần sửa)` → `sync` → `close`.
