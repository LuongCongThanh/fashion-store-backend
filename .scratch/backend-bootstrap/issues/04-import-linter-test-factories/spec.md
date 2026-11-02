# `gen_importlinter.py` và ranh giới `import-linter` cho test và factory

Status: ready-for-agent

Blocked by: 07

Spec: [spec.md](../../spec.md)

## Việc cần làm

- `scripts/gen_importlinter.py` sinh contract `forbidden` cho mọi cặp module và có chế độ `--check` (02 mục 8). Contract `layers` đã có trong `pyproject.toml` từ ticket 07. Thêm `gen_importlinter.py --check` vào `make lint` và bước Lint của job `backend` trong `.github/workflows/ci.yml`.
- Không thêm contract riêng cho factory. Contract `layers` đã chặn test của module lớp dưới import factory của module lớp trên, và chặn hai module cùng lớp import lẫn nhau. `backend/tests/` không thuộc `root_packages` nên `flows/` được import mọi factory. Xem `docs/architecture/12-testing-strategy.md` mục 4.
- Trong contract `forbidden` "Module khác chỉ được dùng contracts và events" (và trong `scripts/gen_importlinter.py`), đặt `allow_indirect_imports = true`. Mặc định import-linter cấm cả chuỗi gián tiếp, nên mọi lời gọi hợp lệ `ordering.services → inventory.contracts → inventory.services → inventory.models` đều bị báo lỗi. Xem `docs/architecture/02-backend-structure.md` mục 8.
- Không dùng `ignore_imports` cho `modules.*.tests.**`: test kiểm tra dữ liệu của module khác qua `contracts`, không import `models` của module đó.
- Viết test cho cấu hình: mỗi acceptance criteria dưới đây có một file Python mẫu, chạy `lint-imports` và kiểm tra kết quả.

## Quyết định

Chốt khi grilling ngày 02/11/2026.

| Chủ đề | Quyết định |
| --- | --- |
| Tài liệu chi phối | `backend/scripts/gen_importlinter.py`, `backend/pyproject.toml` → `02 §8` (cấu hình import-linter), `02 §6.1` (phần public: `contracts`, `events`, `exceptions`), `02 §4` (thứ tự lớp). `backend/Makefile` → `08 §3` (dòng `make lint`), ADR 0017 (recipe chỉ `uv run`). `.github/workflows/ci.yml` → `11` (job `backend`), `12 §8` (cổng chặn CI). Test `backend/tests/test_gen_importlinter.py`, `backend/tests/test_import_boundaries.py` → `12 §4` (ranh giới module, factory), `12 §8`. |
| Cách sinh contract | Mỗi cặp (module nguồn → module đích) một contract `forbidden`, chỉ sinh khi module đích có phần nội bộ. `forbidden_modules` = mọi package/module con thực sự tồn tại của module đích, trừ `contracts`, `events`, `exceptions`, `tests` (02 §6.1). Luôn có `allow_indirect_imports = true`. Không có `ignore_imports`. Danh sách module lấy bằng cách quét `modules/` (bỏ `_*`, `management`, `migrations`, `templates`, như `scripts/check_module_coverage.py`). |
| Contract "không tự đẩy sự kiện" | Generator sinh thêm contract tĩnh của 02 §8: `source_modules = ["modules"]`, cấm `shared.events.relay`, `shared.events.tasks`. Ticket không nhắc nhưng tài liệu chi phối đã quy định, và generator quản lý mọi contract `forbidden`. |
| Vùng sinh trong `pyproject.toml` | Generator chỉ ghi giữa hai dòng đánh dấu `# BEGIN gen_importlinter` / `# END gen_importlinter`; contract `layers` viết tay nằm ngoài vùng. `--check` so vùng hiện có với nội dung sinh lại: lệch → exit 1 kèm diff, lỗi đọc/thiếu dấu → exit 2 (giống `check_module_coverage.py`). Không thêm dependency (ghi text, đọc bằng `tomllib`). |
| Tên contract | ASCII tiếng Anh cho mọi contract, kể cả `layers` (gốc lỗi cp1252 trong backlog 01/11/2026). Vẫn giữ `PYTHONUTF8` ở các entry point; gỡ nó là việc khác. Khác *Việc cần làm* (tên "Module khác chỉ được dùng contracts và events") và ví dụ 02 §8: sửa 02 §8 trong cùng PR. |
| Ngoại lệ FK (`ignore_imports` model → model) | Chưa làm: chưa có FK chéo module. Ghi backlog, làm khi FK đầu tiên xuất hiện ở M1. |
| Seam test | Cây package tạm trong `tmp_path` (như `tests/test_module_coverage.py`), chép phần `[tool.importlinter]` thật của `pyproject.toml`, chạy generator trên cây đó rồi `lint-imports --config <tmp>/pyproject.toml --no-cache` bằng subprocess, kiểm exit code. Như vậy test kiểm cấu hình thật, không phải cấu hình viết riêng cho test. |
| CI và `make lint` | `make lint` thêm `uv run python scripts/gen_importlinter.py --check` trước `lint-imports`; bước Lint của CI thêm `python scripts/gen_importlinter.py --check` trước `lint-imports`. Hook pre-commit giữ nguyên. |

## Acceptance criteria

- [ ] Sửa tay contract `forbidden` trong `pyproject.toml` thì `gen_importlinter.py --check` báo lệch, cả ở `make lint` lẫn CI.
- [ ] Test của `inventory` import `modules.ordering.tests.factories` thì `lint-imports` báo lỗi.
- [ ] Test của `payments` import `modules.shipping.tests.factories` thì `lint-imports` báo lỗi.
- [ ] Test của `ordering` import `modules.inventory.tests.factories` thì `lint-imports` qua.
- [ ] Test của `ordering` import `modules.inventory.models` thì `lint-imports` báo lỗi.
- [ ] `modules.ordering.services` gọi `modules.inventory.contracts` thì `lint-imports` qua.
- [ ] Code ngoài `tests` vẫn không được import trực tiếp `models`, `services`, `selectors`, `api` của module khác.
