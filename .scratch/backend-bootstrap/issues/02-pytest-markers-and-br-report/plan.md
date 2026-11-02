# Kế hoạch

Sinh bằng `plan.py` từ state của skill. Mỗi task là đúng một commit có trailer `Task: <task>`.

| Task | AC | Seam | Test dự kiến | File | Sau |
| --- | --- | --- | --- | --- | --- |
| S1 | 1, 2, 3 | pytest marker enforcement & scripts/br_report.py CLI | `tests/test_pytest_markers.py::test_strict_markers_rejects_undeclared`<br>`tests/test_pytest_markers.py::test_marker_filtering_concurrency_and_flow`<br>`tests/test_pytest_markers.py::test_br_report_outputs_untested_codes_and_exits_zero` | `backend/pyproject.toml`<br>`backend/Makefile`<br>`backend/scripts/br_report.py`<br>`backend/tests/test_pytest_markers.py` | — |

Commit dự kiến: `plan` → `S1` → `R1 (khi review cần sửa)` → `sync` → `close`.
