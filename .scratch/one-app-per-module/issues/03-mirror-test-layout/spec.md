# 03 – Đặt lại vị trí và tên file test theo quy tắc soi gương

Status: ready-for-agent · Ưu tiên: 4 · Blocked by: [02](../02-django-apps/spec.md) · **PR:**

Spec: [spec.md](../../spec.md)

## Mục tiêu
Nhìn đường dẫn code là biết file test ở đâu ([02 mục 4.4](../../../../docs/architecture/02-backend-structure.md#44-test-đặt-ở-đâu-tên-là-gì)), và CI chặn file test đặt sai chỗ. Hiện 53 file test đặt tên nhiều kiểu (`test_api_*`, `test_services_*`, `test_idempotency_purge.py`…), riêng `shared/tests/` có 24 file phẳng.

## Việc cần làm
- [ ] `common/tests/`: chuyển về đường dẫn soi gương, vd. `test_api_pagination.py` → `api/test_pagination.py`, `test_money.py` → `values/test_money.py`, `test_idempotency_purge.py` → `idempotency/test_tasks.py`, test outbox → `events/test_<file>.py`.
- [ ] `apps/identity/tests/`, `apps/geo/tests/`: tương tự, vd. `test_services_auth.py` → `services/test_auth.py`, `test_api_backoffice_login.py` → `api/backoffice/test_views.py`.
- [ ] File test kiểm nhiều file nguồn: tách theo file nguồn. Test nhiều thread: `tests/concurrency/` của app.
- [ ] Test không gắn một file nguồn (migration, check cấu hình): đặt cạnh thứ nó kiểm gần nhất; ca không rõ ghi vào `report.md`.
- [ ] Mỗi thư mục con trong `tests/` có `__init__.py`.
- [ ] Thêm `tests/tooling/test_test_layout.py`: mọi `<pkg>/tests/**/test_<x>.py` phải ứng với file hoặc package `<pkg>/**/<x>` có thật; trừ `concurrency/`, `flows/`, `tooling/` và danh sách ngoại lệ có lý do.
- [ ] Tài liệu: sửa đường dẫn test cụ thể trong `12` (vd. mục 2.9), `05` mục 9, `06` mục 9.

## Quyết định
- Tài liệu chi phối: [02 mục 4.4](../../../../docs/architecture/02-backend-structure.md), [12](../../../../docs/architecture/12-testing-strategy.md) mục 2, 4, [13](../../../../docs/architecture/13-python-django-coding-style.md) mục 9.
- Chỉ đổi chỗ, đổi tên, tách file; không đổi nội dung test.
- Giữ quy ước bằng `test_test_layout.py` trong CI, không chỉ dựa vào review.

## Acceptance criteria
- [ ] Số test thu thập (`pytest --collect-only -q`) trước và sau bằng nhau; mọi test xanh.
- [ ] Mỗi file test đúng đường dẫn soi gương hoặc nằm trong thư mục ngoại lệ; `test_test_layout.py` xanh và fail khi thêm một file test đặt sai chỗ.
- [ ] `make fmt`, `make lint`, `make test` xanh.

## Ghi chú
- Thiếu `__init__.py` thì các file trùng tên (`test_views.py`) ở nhiều app đụng nhau khi pytest thu thập.
- Ghi số test trước khi bắt đầu dời file.
