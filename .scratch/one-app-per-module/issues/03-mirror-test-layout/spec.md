# 03 – Đặt lại vị trí và tên file test theo quy tắc soi gương

Status: ready-for-agent · Ưu tiên: 4 · Blocked by: [02](../02-django-apps/spec.md) · **PR:**

Spec: [spec.md](../../spec.md)

## Mục tiêu
Nhìn đường dẫn code là biết file test ở đâu ([02 mục 4.4](../../../../docs/architecture/02-backend-structure.md#44-test-đặt-ở-đâu-tên-là-gì)), và CI chặn file test đặt sai chỗ. Hiện 53 file test đặt tên nhiều kiểu (`test_api_*`, `test_services_*`, `test_idempotency_purge.py`…), riêng `shared/tests/` có 24 file phẳng.

## Việc cần làm
- [x] `common/tests/`: chuyển về đường dẫn soi gương, vd. `test_api_pagination.py` → `api/test_pagination.py`, `test_money.py` → `values/test_money.py`, `test_idempotency_purge.py` → `idempotency/test_tasks.py`, test outbox → `events/test_<file>.py`.
- [x] `apps/identity/tests/`, `apps/geo/tests/`: tương tự, vd. `test_services_auth.py` → `services/test_auth.py`, `test_api_backoffice_login.py` → `api/backoffice/test_views.py`.
- [x] File test kiểm nhiều file nguồn: tách theo file nguồn. Test nhiều thread: `tests/concurrency/` của app.
- [x] Test không gắn một file nguồn (migration, check cấu hình): đặt cạnh thứ nó kiểm gần nhất; ca không rõ ghi vào `report.md`.
- [x] Mỗi thư mục con trong `tests/` có `__init__.py`.
- [x] Thêm `tests/tooling/test_test_layout.py`: mọi `<pkg>/tests/**/test_<x>.py` phải ứng với file hoặc package `<pkg>/**/<x>` có thật; trừ `concurrency/`, `flows/`, `tooling/` và danh sách ngoại lệ có lý do.
- [x] Tài liệu: sửa đường dẫn test cụ thể trong `12` (vd. mục 2.9), `05` mục 9, `06` mục 9.

## Quyết định
- Tài liệu chi phối: [02 mục 4.4](../../../../docs/architecture/02-backend-structure.md), [12](../../../../docs/architecture/12-testing-strategy.md) mục 2, 4, [13](../../../../docs/architecture/13-python-django-coding-style.md) mục 9.
- Chỉ đổi chỗ, đổi tên, tách file; không đổi nội dung test.
- Giữ quy ước bằng `test_test_layout.py` trong CI, không chỉ dựa vào review.

## Acceptance criteria
- [x] Số test thu thập (`pytest --collect-only -q`) trước và sau bằng nhau; mọi test xanh.
- [x] Mỗi file test đúng đường dẫn soi gương hoặc nằm trong thư mục ngoại lệ; `test_test_layout.py` xanh và fail khi thêm một file test đặt sai chỗ.
- [x] `make fmt`, `make lint`, `make test` xanh.

## Ghi chú
- Số test: 524 trước, 524 sau (thêm 8 test của `test_test_layout.py` thành 532).
- Tách/gộp: `test_api_errors.py` → `api/test_views.py` (lỗi ngoài DRF) + `api/test_exception_handler.py`; `test_api_backoffice_login.py` + `_me.py` → `api/backoffice/test_views.py`.
- Ngoại lệ trong `test_test_layout.py`: `common/tests/api/test_i18n.py` (kiểm LocaleMiddleware của settings), `common/tests/test_factories.py` (kiểm factory trong `tests/`).
- `test_api_backoffice_clients.py` kiểm fixture của `conftest.py` gốc nên chuyển sang `tests/tooling/test_backoffice_clients.py`.
- `common/events/tests/` gộp vào `common/tests/events/`; `conftest.py` của outbox lên `common/tests/conftest.py` vì test lệnh `management/commands/` cũng cần.
- mypy: thêm override `apps.*.tests.*` vì pattern kiểu chặt `apps.*.services.*` khớp cả `tests/services/`.
- Thiếu `__init__.py` thì các file trùng tên (`test_views.py`) ở nhiều app đụng nhau khi pytest thu thập.
- Ghi số test trước khi bắt đầu dời file.
