# Kế hoạch

Sinh bằng `plan.py` từ state của skill. Mỗi task là đúng một commit có trailer `Task: <task>`.

| Task | AC | Seam | Test dự kiến | File | Sau |
| --- | --- | --- | --- | --- | --- |
| S1 | 1, 2 | schema sinh bằng manage.py spectacular --validate --fail-on-warn | `shared/tests/test_api_schema.py::test_schema_has_error_dto_component`<br>`shared/tests/test_api_schema.py::test_every_operation_declares_common_errors`<br>`shared/tests/test_api_schema.py::test_operation_with_path_parameter_declares_404` | `backend/shared/api/schema.py`<br>`backend/config/settings/base.py`<br>`backend/shared/tests/test_api_schema.py` | — |

Commit dự kiến: `plan` → `S1` → `R1 (khi review cần sửa)` → `sync` → `close`.
