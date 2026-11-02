# Báo cáo

### Báo cáo 02/11/2026

**Nhánh:** `chore/import-linter-boundaries` · **PR:** chưa mở · **Mode:** full

#### Đã làm

| AC | Bằng chứng |
| --- | --- |
| 1. Sửa tay contract `forbidden` thì `gen_importlinter.py --check` báo lệch, ở `make lint` và CI | `tests/test_gen_importlinter.py::test_check_reports_hand_edited_forbidden_contract`, `::test_committed_pyproject_is_up_to_date`; lỗi đọc → exit 2: `::test_check_rejects_missing_markers`, `::test_check_rejects_invalid_toml`, `::test_check_rejects_non_utf8_pyproject`; `make lint` và bước Lint của `ci.yml` gọi `--check` trước `lint-imports` (CI xác nhận ở phase 6) |
| 2. Test `inventory` import factory `ordering` → lỗi | `tests/test_import_boundaries.py::test_inventory_tests_importing_ordering_factories_fails` |
| 3. Test `payments` import factory `shipping` → lỗi | `tests/test_import_boundaries.py::test_payments_tests_importing_shipping_factories_fails` |
| 4. Test `ordering` import factory `inventory` → qua | `tests/test_import_boundaries.py::test_ordering_tests_importing_inventory_factories_passes` |
| 5. Test `ordering` import `inventory.models` → lỗi | `tests/test_import_boundaries.py::test_ordering_tests_importing_inventory_models_fails` |
| 6. `ordering.services` gọi `inventory.contracts` → qua | `tests/test_import_boundaries.py::test_ordering_services_calling_inventory_contracts_passes` (đặt `allow_indirect_imports = false` thì test đỏ) |
| 7. Code ngoài `tests` không import `models`/`services`/`selectors`/`api` của module khác | `tests/test_import_boundaries.py::test_non_test_code_importing_other_module_internals_fails` (parametrize 4 phần) |

Thêm theo quyết định G1: `tests/test_import_boundaries.py::test_module_importing_outbox_relay_fails` (contract "không tự đẩy sự kiện", 02 §8) và `::test_module_enqueueing_task_via_shared_tasks_passes` (chuỗi gián tiếp hợp lệ qua `shared.tasks`). Thêm ở review: `::test_ordering_services_importing_inventory_factories_fails` (code ngoài `tests` không dùng factory của module khác, 12 §4), `tests/test_gen_importlinter.py::test_directory_without_init_is_not_a_module`, `::test_target_without_internals_gets_no_pairwise_contract`.

S2 xanh ngay lần đầu vì contract `layers` đã có; đã chứng minh 3 test đỏ đúng lý do khi tạm đảo thứ tự lớp và đổi `|` thành `:`, rồi hoàn tác.

`make lint` xanh (import-linter: 9 kept, 0 broken) · `make test`: 364 passed trong 13.19s, branch coverage `identity` 100%, `shared` 82/84 (97.62%)

#### Chưa làm

- Ngoại lệ FK (`ignore_imports` model → model của module lớp dưới, 02 §6.3): chưa có FK chéo module; đã ghi `.scratch/backlog.md`, làm ở M1.

#### Gap

- Hôm nay chỉ `identity` có phần nội bộ, nên `pyproject.toml` có 7 contract cặp module + 1 contract outbox. Module mới thêm `models/`… thì `--check` đỏ tới khi chạy lại `python scripts/gen_importlinter.py`.
- Hook pre-commit chưa chạy `gen_importlinter.py --check`; lệch chỉ bị bắt ở `make lint` và CI.
- Contract B2 (chỉ test của module khác import `modules.<X>.tests`) hôm nay chưa sinh ra trong repo thật: chỉ `identity` có `tests` và các module khác chưa có module con làm nguồn. Code của chính một module import `tests` của mình chưa bị chặn.
- Contract không cấm được re-export phần nội bộ ở `modules/<m>/__init__.py` (B5) và hook pre-commit chưa chạy `--check` (B6): đã ghi `.scratch/backlog.md`.
- Working tree còn dòng `kombu>=5.6.2` trong `backend/pyproject.toml` (và `uv.lock`) do phiên khác thêm; người dùng chọn để ngoài ticket, không commit.

#### Thay đổi theo yêu cầu

- `celery-types` vào nhóm `dev`; sửa 4 lỗi mypy stub làm lộ ra: `sync_beat_schedule.py` dùng `schedule.seconds`, 3 test đọc `Task.queue` ghi `# type: ignore[attr-defined]` (stub thiếu thuộc tính). Bằng chứng: `shared/tests/test_sync_beat_schedule.py::test_empty_db_creates_every_job_from_code`, `shared/events/tests/test_relay.py::test_dispatch_event_routed_to_events_queue`, `mypy .` 0 lỗi.
- SonarCloud (PR #57): "Path Traversal via file content" ở `scripts/gen_importlinter.py` (đường dẫn `--root` từ CLI chảy tới `write_text`) → bỏ `--root`, script luôn chạy trên thư mục hiện tại (`backend/` ở Make và CI); test vốn chạy với `cwd` là cây tạm.
- `requests>=2.34.2` thêm ở S3 theo yêu cầu, rồi bỏ ở R1 theo quyết định của người dùng ở review (St1/B10: chưa có code dùng, 02 §3.1 chọn `httpx`).
- Thống nhất venv: `pyrightconfig.json` ở gốc repo trỏ `backend/.venv` và gốc import `backend/`; xoá `.venv` thừa ở gốc repo (không commit được, nằm trong `.gitignore`); 08 §6 ghi quy ước. Bằng chứng: `uvx pyright backend/shared/management/commands/sync_beat_schedule.py` không còn `reportMissingImports`.

#### Review

| Mã | Chỗ | Kết luận | Lý do |
| --- | --- | --- | --- |
| B1 | `scripts/gen_importlinter.py:73` | đã sửa | contract outbox chặn cả chuỗi gián tiếp `shared.tasks → operations → relay → tasks`; thêm `allow_indirect_imports` |
| B4 / Sp1 / Sp4 | `scripts/gen_importlinter.py:114` | đã sửa | file không phải UTF-8 thoát 1 kèm traceback; giờ exit 2, có test TOML hỏng và non-UTF-8 |
| B3 + B8 / St6 | `scripts/gen_importlinter.py:32`, `scripts/check_module_coverage.py:13` | đã sửa | thư mục không có `__init__.py` bị tính là module; quét chung ở `scripts/_modules.py` |
| B2 | `scripts/gen_importlinter.py:16` | đã sửa | code ngoài `tests` import được factory module khác; thêm contract theo 12 §4, ghi `## Quyết định` |
| Sp5 | `scripts/gen_importlinter.py:78` | đã sửa | thêm test module đích rỗng không sinh contract |
| St5 | `scripts/gen_importlinter.py:16` | đã sửa | `PUBLIC` gồm cả `tests`; tách `PUBLIC_API` |
| St4 / B7 | 3 file test | đã sửa | helper chung `tests/helpers.py` |
| St2 | 02 §3.2 | đã sửa | thêm dòng `celery-types` |
| St1 / B10 | `pyproject.toml:22` | hoàn tác | `requests` không ai dùng, 02 §3.1 chọn `httpx`; người dùng duyệt bỏ |
| B5, B6 | `modules/<m>/__init__.py`, `.pre-commit-config.yaml:42` | chỉ báo | ghi backlog |
| B9, St3, Sp3 | test subprocess, `print` trong CLI, dòng `--check` của Makefile/CI | chỉ báo | chi phí test chấp nhận được; `print` cho CLI như `check_module_coverage.py`; CI chứng minh ở phase 6 |
| Sp2 | `.scratch/mvp-roadmap/map.md:44` | bác | quyết định điểm nóng do người dùng chọn đầu phiên, quy tắc ghi vào *Decisions-so-far* |

#### Commit

| Task | Phase | AC | Commit | File |
| --- | --- | --- | --- | --- |
| plan | 1 grill | — | `43b2d2b` docs: plan import-linter boundaries ticket | 4 |
| S1 | 2 code | 1, 5, 6, 7 | `35d93e4` feat(backend): generate forbidden import-linter contracts between modules | 10 |
| S2 | 2 code | 2, 3, 4 | `6e93d26` test(backend): verify layers contract enforces factory import rules | 1 |
| S3 | 2 code |  | `e47876c` chore(backend): add celery-types and pin IDE to backend venv | 8 |
| R1 | 4 review | — | `c02ff73` fix(backend): address review findings on import-linter boundaries | 12 |

#### Tài liệu đã cập nhật

- `docs/architecture/02-backend-structure.md` §3.2: dòng `celery-types`; §5: `scripts/_modules.py` trong cây thư mục; §8: cấu hình mẫu tên ASCII, vùng sinh `BEGIN/END gen_importlinter`, contract forbidden do generator sinh, FK để sau.
- `docs/architecture/08-local-development.md` §3: dòng `make lint`; §6: `pyrightconfig.json`, chỉ một venv `backend/.venv`.
- `docs/architecture/11-git-workflow.md` §3.5: job `backend` chạy `gen_importlinter.py --check`.
- `docs/architecture/12-testing-strategy.md` §4: factory chỉ dùng trong test, có contract chặn; §8: thêm cổng `gen_importlinter.py --check`.

#### Ghi chú cho retro

- Hai phiên cùng sửa `backend/pyproject.toml` trên một nhánh (thêm `celery-types`, `requests`, `kombu` giữa chừng); sub-agent S1 phải tạm gỡ gói và khôi phục từ bản sao lưu để commit sạch → commit `e47876c`, ghi chú `kombu` trong state → gợi ý: `state.py start` cảnh báo khi working tree đổi giữa các bước.
- Cất dòng `kombu` của phiên khác bằng `git stash` để R1 commit sạch; `stash pop` xung đột ở `pyproject.toml` vì stash chụp lúc còn dòng `requests` mà R1 đã bỏ → giải tay, giữ `kombu` → gợi ý: tách việc của phiên khác sang nhánh/worktree riêng thay vì stash.
- `.venv` thừa ở gốc repo làm Pylance báo `reportMissingImports` cho mọi thư viện → `pyrightconfig.json` trong `e47876c`.
