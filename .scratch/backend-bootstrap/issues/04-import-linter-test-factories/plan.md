# Kế hoạch

Sinh bằng `plan.py` từ state của skill. Mỗi task là đúng một commit có trailer `Task: <task>`.

| Task | AC | Seam | Test dự kiến | File | Sau |
| --- | --- | --- | --- | --- | --- |
| S1 | 1, 5, 6, 7 | gen_importlinter.py chạy trên cây package tạm, rồi lint-imports --config qua subprocess | `tests/test_gen_importlinter.py::test_check_reports_hand_edited_forbidden_contract`<br>`tests/test_gen_importlinter.py::test_committed_pyproject_is_up_to_date`<br>`tests/test_import_boundaries.py::test_ordering_tests_importing_inventory_models_fails`<br>`tests/test_import_boundaries.py::test_ordering_services_calling_inventory_contracts_passes`<br>`tests/test_import_boundaries.py::test_non_test_code_importing_other_module_internals_fails`<br>`tests/test_import_boundaries.py::test_module_importing_outbox_relay_fails` | `backend/scripts/gen_importlinter.py`<br>`backend/pyproject.toml`<br>`backend/Makefile`<br>`.github/workflows/ci.yml`<br>`backend/tests/test_gen_importlinter.py`<br>`backend/tests/test_import_boundaries.py`<br>`docs/architecture/02-backend-structure.md`<br>`docs/architecture/08-local-development.md`<br>`docs/architecture/11-git-workflow.md`<br>`docs/architecture/12-testing-strategy.md` | — |
| S2 | 2, 3, 4 | contract layers thật trên cây package tạm, lint-imports --config qua subprocess | `tests/test_import_boundaries.py::test_inventory_tests_importing_ordering_factories_fails`<br>`tests/test_import_boundaries.py::test_payments_tests_importing_shipping_factories_fails`<br>`tests/test_import_boundaries.py::test_ordering_tests_importing_inventory_factories_passes` | `backend/tests/test_import_boundaries.py`<br>`docs/architecture/12-testing-strategy.md` | S1 |

Commit dự kiến: `plan` → `S1` → `S2` → `R1 (khi review cần sửa)` → `sync` → `close`.
