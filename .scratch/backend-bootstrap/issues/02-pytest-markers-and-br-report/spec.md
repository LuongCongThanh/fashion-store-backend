# Khai báo marker pytest và lệnh `make br-report`

Status: ready-for-agent

Blocked by: 07

Spec: [spec.md](../../spec.md)

## Việc cần làm

- Làm cùng lúc khởi tạo backend (khi có `backend/pyproject.toml`).
- Trong `pyproject.toml`, bật `--strict-markers` và khai báo 3 marker `br`, `concurrency`, `flow` theo `docs/architecture/12-testing-strategy.md` mục 3.
- Viết lệnh `make br-report`: lấy mọi mã `BR-xxx` trong `docs/business/04-business-rules.md`, so với các mã gắn trong `@pytest.mark.br(...)` (thu thập bằng `pytest --collect-only`), rồi in ra các mã chưa có test.
- `make br-report` không chạy trong CI.

## Quyết định

Chốt khi grilling ngày 02/11/2026.

| Chủ đề | Quyết định |
|---|---|
| Tài liệu chi phối | `backend/pyproject.toml` và `backend/scripts/br_report.py`: `12 §3` (Marker của pytest); `backend/Makefile`: `08 §3` (Lệnh Makefile), `12 §3`; `backend/tests/test_pytest_markers.py`: `12 §3`, `02 §9.2` (quy ước tên test) |
| Marker pytest | Khai báo 3 marker `br`, `concurrency`, `flow` trong `[tool.pytest.ini_options]` của `pyproject.toml`; bật `addopts = "--strict-markers"` để pytest báo lỗi khi test dùng marker chưa khai báo |
| `make br-report` | Thêm target `br-report` vào `backend/Makefile` gọi `uv run python scripts/br_report.py`. Không chạy trong CI |
| `scripts/br_report.py` | Lấy toàn bộ mã `BR-xxx` từ `docs/business/04-business-rules.md` bằng regex `\bBR-[A-Z0-9]+-\d+\b` giữ thứ tự xuất hiện. Thu thập các mã đã gắn marker `br` qua `pytest --collect-only` (hook `pytest_collection_modifyitems`). In các mã chưa có test ra stdout, mỗi mã một dòng, và luôn thoát với mã 0 |
| Mode & Slice | Mode lite: ticket có 3 AC, không thêm model/migration hay endpoint; thực hiện trong 1 slice S1 |

## Acceptance criteria

- [ ] Test dùng marker chưa khai báo thì pytest báo lỗi.
- [ ] `pytest -m concurrency` và `pytest -m flow` chỉ chạy đúng nhóm test đó.
- [ ] `make br-report` in đúng danh sách mã `BR-xxx` chưa có test và luôn thoát với mã 0.
