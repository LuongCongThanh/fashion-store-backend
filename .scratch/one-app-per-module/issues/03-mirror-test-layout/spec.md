# Đặt lại vị trí và tên file test theo quy tắc soi gương

Status: ready-for-agent

Blocked by: 02

Spec: [spec.md](../../spec.md)

Theo [02 mục 4.4](../../../../docs/architecture/02-backend-structure.md#44-test-đặt-ở-đâu-tên-là-gì): đường dẫn test soi gương đường dẫn code, thêm `test_` trước tên file. Hiện 53 file test đặt tên theo nhiều kiểu (`test_api_*`, `test_services_*`, `test_idempotency_purge.py`…), riêng `shared/tests/` có 24 file phẳng. Chỉ đổi chỗ, đổi tên và tách file; không đổi nội dung test.

## Việc cần làm

- `common/tests/`: chuyển mỗi file về đường dẫn soi gương, ví dụ `test_api_pagination.py` → `api/test_pagination.py`, `test_money.py` → `values/test_money.py`, `test_idempotency_purge.py` → `idempotency/test_tasks.py`, test outbox → `events/test_<file>.py`.
- `apps/identity/tests/`, `apps/geo/tests/`: tương tự, ví dụ `test_services_auth.py` → `services/test_auth.py`, `test_api_backoffice_login.py` → `api/backoffice/test_views.py`.
- File test đang kiểm nhiều file nguồn thì tách theo file nguồn. Test nhiều thread để ở `tests/concurrency/` của app.
- Test không gắn với một file nguồn (migration, cấu hình check) đặt cạnh thứ nó kiểm gần nhất; trường hợp không rõ ghi vào `report.md`.
- Mỗi thư mục con trong `tests/` có `__init__.py`, để các file trùng tên (`test_views.py`) ở nhiều app không đụng nhau.
- Thêm `tests/tooling/test_test_layout.py`: mọi `<pkg>/tests/**/test_<x>.py` phải ứng với file hoặc package `<pkg>/**/<x>` có thật, trừ thư mục `concurrency/`, `flows/`, `tooling/` và danh sách ngoại lệ có lý do.
- Tài liệu: sửa đường dẫn test cụ thể còn ghi trong `12` (ví dụ mục 2.9), `05` mục 9, `06` mục 9.

## Quyết định

| Chủ đề | Quyết định |
|---|---|
| Tài liệu chi phối | `docs/architecture/02-backend-structure.md::4.4`, `docs/architecture/12-testing-strategy.md::2,4`, `docs/architecture/13-python-django-coding-style.md::9` |
| Giữ quy ước bằng test | `test_test_layout.py` chặn file test đặt sai chỗ trong CI, thay vì chỉ dựa vào review |

## Acceptance criteria

- [ ] Số test pytest thu thập được trước và sau bằng nhau (`pytest --collect-only -q`), mọi test xanh.
- [ ] Mỗi file test nằm đúng đường dẫn soi gương hoặc trong thư mục ngoại lệ; `test_test_layout.py` xanh và fail khi thêm một file test đặt sai chỗ.
- [ ] `make fmt`, `make lint`, `make test` xanh.
