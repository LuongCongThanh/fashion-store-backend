# Báo cáo

### Báo cáo 01/11/2026 (sau review)

**Nhánh:** `chore/module-branch-coverage` · **PR:** #56 · **Mode:** full

#### Đã làm

| AC | Bằng chứng |
| --- | --- |
| 1. Branch < 80% ở `services/` + `handlers.py` của một module, hoặc nhóm `shared`, bị CI chặn | `tests/test_module_coverage.py::test_gate_rejects_low_branches_despite_high_combined_coverage`, `::test_gate_checks_shared_targets` (gồm lõi `shared/idempotency.py`), `::test_gate_rejects_branch_percentage_that_rounds_up_to_eighty`, `::test_gate_accepts_exactly_eighty_percent`, `::test_gate_counts_unexecuted_service_files`, `::test_gate_rejects_statement_only_data`, `::test_gate_rejects_missing_data`, `::test_gate_reads_data_file_from_coverage_environment`, `::test_gate_applies_project_coverage_config`, `::test_gate_resolves_data_file_option_from_working_directory`; CI gọi `python scripts/check_module_coverage.py` ở step *Coverage* của job `backend` (kiểm bằng đọc `ci.yml:121-126`, không có test tự động cho cấu hình CI) |
| 2. Module A 100% không kéo module B 60% qua cổng | `tests/test_module_coverage.py::test_gate_checks_modules_independently` |
| 3. Module chưa có `services/` và `handlers.py` không làm cổng lỗi | `tests/test_module_coverage.py::test_gate_skips_empty_modules`, `::test_gate_checks_handlers_without_services`, `::test_gate_reports_targets_without_branches`, `::test_gate_ignores_django_app_packages` |
| 4. Chạy `pytest -n auto` cho cùng kết quả như chạy tuần tự | `tests/test_module_coverage.py::test_parallel_collection_matches_serial_branch_counts` (pytest thật, serial so với 2 worker, so stdout và exit code của cổng); trên repo thật, review đo serial và 4 lần `-n auto`: tập nhánh thiếu trùng nhau (xem *Gap*) |
| 5. Không có ngưỡng coverage toàn repo | `tests/test_module_coverage.py::test_gate_ignores_unrelated_low_coverage`, `::test_gate_excludes_shared_event_tests_from_branch_totals`; `pyproject.toml` chỉ có `[tool.coverage.run] branch = true`, không có `fail_under` |

`make lint` xanh (import-linter: 1 contract kept, 0 broken) · `make test`: 345 passed trong 15.63s; cổng: identity 6/6 nhánh (100%) PASS, shared 82/84 (97.62%) PASS, các module còn lại SKIP

#### Chưa làm

- Không

#### Gap

- Nhóm `shared` có một nhánh không tất định: `return` ở `shared/events/consumer.py:121` chỉ được chạy khi thread trùng trong `test_concurrent_duplicate_dispatch_commits_once` (`shared/events/tests/test_consumer.py:502`) chen vào giữa hai transaction, khoảng 3/12 lần không chạm kể cả khi chạy tuần tự. Không do xdist; AC4 đạt. Số nhánh của cổng vì vậy lệch ±1 giữa các lần chạy; khi nhóm sát 80% cổng có thể lúc qua lúc chặn. Ticket không được sửa code `backend/shared/` → đã ghi `.scratch/backlog.md`.
- 12 §8 vốn ghi target `shared/api/idempotency.py` từ trước khi PR #40 tách lõi sang `shared/idempotency.py`; ticket đã thêm lõi vào nhóm `shared` và sửa 12 §8 (người dùng duyệt ở review).

#### Thay đổi theo yêu cầu

- SonarCloud (PR #56): `backend/scripts/check_module_coverage.py:44` cognitive complexity 16 > 15 → tách `_load` (nạp cấu hình và dữ liệu coverage) khỏi `_check`; 18 test cổng và `make test` xanh (task `ci`)

#### Review

| Mã | Chỗ | Kết luận | Lý do |
| --- | --- | --- | --- |
| B1 / S4 | `backend/scripts/check_module_coverage.py:35` | đã sửa (R1) | nhóm `shared` thêm lõi `shared/idempotency.py`; sửa 12 §8 và `## Quyết định` |
| B2 / B3 / B9 | `backend/scripts/check_module_coverage.py:44-53,78-82` | đã sửa (R1) | đọc `COVERAGE_FILE` / `data_file` / exclude từ `pyproject.toml`; `--data-file` tính từ thư mục đang đứng |
| B5 / S2 | `backend/scripts/check_module_coverage.py:13,21` | đã sửa (R1) | bỏ `management`, `migrations`, `templates` (ADR 0006) |
| T4 / S3 | `backend/scripts/__init__.py` | hoàn tác (R1) | ngoài phạm vi; mypy và pytest không cần |
| T1 | `spec.md` dòng *Tài liệu chi phối* | đã sửa (sync) | cây thư mục là 02 §5, không phải §2 |
| B4 / S1 | `shared/events/tests/test_consumer.py:502` | chỉ báo → backlog | race có từ trước, ngoài `backend/shared/` được phép sửa |
| B7 / T2 | commit `85db251` | chỉ báo | thân commit tiếng Việt; PR squash, R1 trở đi viết tiếng Anh |
| B8 / T3 | commit `d483e72` | chỉ báo | type `feat`; tiêu đề PR khi squash dùng `ci:` |
| B6 | `backend/scripts/check_module_coverage.py:23` | chỉ báo | chưa module nào có `services/tests/` |
| S5 | `.github/workflows/ci.yml:121-126` | chỉ báo | bước chặn CI chỉ kiểm được bằng đọc cấu hình |
| B10, T5–T8 | `backend/tests/test_module_coverage.py`, Makefile, CI | chỉ báo (smell) | test subprocess tốn thời gian, `subprocess.run` lặp, cờ `--cov` ở 5 chỗ, `80` viết thẳng, tên hằng `SERVICE` |

#### Commit

| Task | Phase | AC | Commit | File |
| --- | --- | --- | --- | --- |
| plan | 1 grill | — | `bfff737` docs: plan module branch coverage gate | 2 |
| S1 | 2 code | 1, 2, 3, 5 | `d483e72` feat: enforce branch coverage per module | 5 |
| S2 | 2 code | 1, 4, 5 | `85db251` ci: gate branch coverage in make test and CI | 5 |
| R1 | 4 review | — | `a5c5e0a` fix(scripts): address review findings on module coverage gate | 6 |
| sync | 5 sync | — | `f377abb` docs: sync docs and report for module coverage gate ticket | 4 |
| ci | 6 ship | — | `a71ab39` refactor(ci): split coverage loading out of module gate check | 1 |

#### Tài liệu đã cập nhật

- `docs/architecture/12-testing-strategy.md` mục 8: đo branch riêng bằng `scripts/check_module_coverage.py` thay cho `coverage report --fail-under` (S1); thêm lõi `shared/idempotency.py`, đọc cấu hình coverage của project, bỏ thư mục Django app (R1)
- `docs/architecture/02-backend-structure.md` mục 5: thêm `scripts/check_module_coverage.py` vào cây thư mục (S1, bỏ dòng `scripts/__init__.py` ở R1)
- `docs/architecture/08-local-development.md` mục 3/5: lệnh test có coverage và bước cổng (S2)
- Ticket (sync): `spec.md` sửa số mục cây thư mục 02 §2 → §5 (T1) và dòng `Interface / seam` theo cách đọc cấu hình coverage sau R1; `plan.md` sinh lại từ state (thêm test boundary của S1 và test của R1)
- `.scratch/backlog.md`: test tất định cho nhánh `shared/events/consumer.py:121` (B4/S1)
- `GLOSSARY.md`, ADR: không có thuật ngữ hay quyết định kiến trúc mới

#### Ghi chú cho retro

- Số nhánh `shared` lệch giữa các lần chạy chỉ lộ ra khi phiên chính chạy lại `make test`; phiên chính đoán nguyên nhân là xdist, review đo ra là test race có từ trước. Bằng chứng: dòng backlog 01/11/2026 · backend-bootstrap/01 và finding B4/S1.
- 12 §8 (tài liệu chi phối) đã cũ so với code (`shared/idempotency.py` tách ở PR #40) mà grilling không bắt; trục Bug tìm ra. Bằng chứng: finding B1, dòng "Target idempotency" trong `## Quyết định`.
