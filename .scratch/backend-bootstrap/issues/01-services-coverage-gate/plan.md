# Kế hoạch

Sinh bằng `plan.py` từ state của skill. Mỗi task là đúng một commit có trailer `Task: <task>`.

| Task | AC | Seam | Test dự kiến | File | Sau |
| --- | --- | --- | --- | --- | --- |
| S1 | 1, 2, 3, 5 | CLI kiểm dữ liệu coverage branch thật, từng module và nhóm shared độc lập | `tests/test_module_coverage.py::test_gate_rejects_low_branches_despite_high_combined_coverage`<br>`tests/test_module_coverage.py::test_gate_checks_modules_independently`<br>`tests/test_module_coverage.py::test_gate_skips_empty_modules`<br>`tests/test_module_coverage.py::test_gate_checks_handlers_without_services`<br>`tests/test_module_coverage.py::test_gate_counts_unexecuted_service_files`<br>`tests/test_module_coverage.py::test_gate_checks_shared_targets`<br>`tests/test_module_coverage.py::test_gate_ignores_unrelated_low_coverage`<br>`tests/test_module_coverage.py::test_gate_rejects_statement_only_data` | `backend/scripts/__init__.py`<br>`backend/scripts/check_module_coverage.py`<br>`backend/tests/test_module_coverage.py`<br>`docs/architecture/02-backend-structure.md`<br>`docs/architecture/12-testing-strategy.md` | — |
| S2 | 1, 4, 5 | pytest-cov serial/xdist tạo cùng số nhánh và kết quả gate; cùng lệnh trong local/CI | `tests/test_module_coverage.py::test_parallel_collection_matches_serial_branch_counts` | `backend/pyproject.toml`<br>`backend/Makefile`<br>`.github/workflows/ci.yml`<br>`backend/tests/test_module_coverage.py`<br>`docs/architecture/08-local-development.md` | S1 |

Commit dự kiến: `plan` → `S1` → `S2` → `R1 (khi review cần sửa)` → `sync` → `close`.
