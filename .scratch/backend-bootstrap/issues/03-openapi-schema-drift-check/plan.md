# Kế hoạch

Sinh bằng `plan.py` từ state của skill. Mỗi task là đúng một commit có trailer `Task: <task>`.

| Task | AC | Seam | Test dự kiến | File → tài liệu chi phối | Sau |
| --- | --- | --- | --- | --- | --- |
| S1 | 1, 2 | scripts/gen_openapi.py [--check] [--schema PATH] qua subprocess | TDD `tests/test_gen_openapi.py::test_check_fails_when_committed_schema_is_stale` → AssertionError<br>TDD `tests/test_gen_openapi.py::test_check_passes_when_schema_is_current` → AssertionError<br>TDD `tests/test_gen_openapi.py::test_generation_fails_when_schema_is_invalid` → AssertionError | `backend/scripts/gen_openapi.py` → docs/architecture/12-testing-strategy.md::5<br>`backend/tests/test_gen_openapi.py` → docs/architecture/12-testing-strategy.md::5<br>`backend/openapi.yaml` → docs/architecture/12-testing-strategy.md::5<br>`backend/Makefile` → docs/architecture/08-local-development.md::3, docs/adr/0017-windows-native-dev-api-on-host.md<br>`.github/workflows/ci.yml` → docs/architecture/11-git-workflow.md::3.4, docs/architecture/12-testing-strategy.md::5<br>`.pre-commit-config.yaml` → docs/architecture/11-git-workflow.md::8 | — |

Commit dự kiến: `plan` → `S1` → `R1 (khi review cần sửa)` → `sync` → `close`.
