# Báo cáo

### Báo cáo 04/11/2026

**Nhánh:** `feat/openapi-docs-quality` · **PR:** chưa mở · **Mode:** full

#### Đã làm

| AC | Bằng chứng |
| --- | --- |
| 1. Tag `<store\|backoffice> · <module>` do `AutoSchema` suy ra | `shared/tests/test_api_schema.py::test_tags_derive_from_app_and_module` |
| 2. Mọi operation có `summary`, ví dụ request/2xx, ví dụ lỗi tự khai, tiếng Anh; docstring không vào schema | `shared/tests/test_api_schema.py::test_current_operations_have_summary_and_examples`, `::test_declared_errors_have_examples_with_matching_code`, `::test_docstrings_are_not_in_schema` |
| 3. Request body chỉ `application/json`; mọi 429 có `Retry-After` | `shared/tests/test_api_schema.py::test_json_operation_accepts_only_json`, `::test_throttled_response_declares_retry_after`, `::test_default_errors_have_english_description_and_example`, `::test_default_errors_have_example_with_matching_code`, `::test_default_error_examples_follow_error_dto`, `::test_default_error_descriptions_name_their_code` (3 test sau tách ở R1) |
| 4. Trang giới thiệu tiếng Anh và tuỳ chọn Swagger UI | `shared/tests/test_api_schema.py::test_info_describes_apps_auth_errors_and_headers`, `::test_swagger_ui_settings_are_configured` |
| 5. `gen_openapi.py --check` báo `<operationId>: <thiếu gì>` cho luật 1–7, có test đạt/vi phạm; `make lint` xanh | `tests/test_gen_openapi.py::test_quality_rule_reports_violation`, `::test_quality_rule_passes_annotated_operation` (parametrize luật 1–7), `::test_check_reports_quality_violation_from_rendered_schema`, `::test_check_passes_when_schema_is_current` |
| 6. Tài liệu 04 §5.6, 13, skill phase 2; gỡ mục backlog | Diff commit `sync`: 04 §5.6, 13 §2, 12 §5, 02, 08, `phases/2-code.md`, `.scratch/backlog.md` (tài liệu, không test tự động) |

Test hồi quy giữ xanh: `shared/tests/test_api_schema.py::test_declared_error_response_is_kept`, `modules/identity/tests/test_api_backoffice_me.py::test_openapi_declares_me_auth_errors`.

Sau R1: `make fmt` OK · `make lint` xanh (ruff, mypy, import-linter, `gen_openapi --check` không vi phạm, không drift) · `make test`: 519 passed, 0 failed (coverage `shared` 95.45%) · test skill 55 OK · `check_ac_trace` OK. Lần chạy trước (S3) có 15 test giới hạn đăng nhập sai đỏ do `backend/.env` trỏ `REDIS_URL` vào `redis:6379` (host trong Docker); người dùng đã sửa sang `localhost:6380`, nay xanh.

#### Chưa làm

- Không còn. Ticket sau: đặt tên `operationId` khi frontend chuyển sang sinh TS client (ghi ở 12 §5).

#### Gap

- `--check` gọi `django.setup()` để import `shared.api.schema.ERROR_DESCRIPTIONS`. Lỗi mặc định được nhận diện bằng mô tả trùng với mô tả mặc định, nên view nào khai lại một mã mặc định (400/401/…) với mô tả khác sẽ bị coi là lỗi tự khai và phải có ví dụ đúng `code`.
- drf-spectacular camelize tên ví dụ (`INVALID_CREDENTIALS` thành `InvalidCredentials`), nên luật 4 kiểm `error.code` trong value của ví dụ, không kiểm key.
- `shared/events/tests/test_consumer.py::test_interrupted_handler_fails_after_max_interrupted_runs` đỏ một lần khi chạy cả bộ ở S2, chạy riêng thì xanh 3/3, lần `make test` cuối cũng xanh. Có vẻ flaky, không thuộc ticket này.
- Chạy đủ `make test` xanh cần Redis local (`make up`).

#### Thay đổi theo yêu cầu

- 04/11/2026: sửa `progress.py`, `common.py` của skill ship-ticket-fashion để nhận feature lồng trong `.scratch/module-plans/<feature>/`. Người dùng chọn gộp vào PR này. Đã commit cùng task `R1` (`38139af`) kèm test feature lồng trong `test_scripts.py` (finding T8), vì commit không có `Task:` hợp lệ làm `commit_map.py` báo FAIL.

#### Review

Ba trục (Spec, Standards, Bug) chạy lại 04/11 sau khi finding lần đầu mất ở `/clear`. Một vòng sửa R1 (`38139af`), xanh.

| Mã | Vị trí | Kết luận | Lý do / cách sửa |
| --- | --- | --- | --- |
| B1 = S4 | `backend/scripts/gen_openapi.py:137` | đã sửa | ví dụ lỗi không có `error` làm `--check` crash `KeyError`; nay báo `missing ErrorDTO example`; test red `4-declared-error-not-error-dto` |
| S1 | `backend/tests/test_gen_openapi.py` | đã sửa | thêm case luật 7: description, response description, ví dụ 2xx |
| S2 | `backend/scripts/gen_openapi.py:123` | đã sửa | thêm case luật 6 operation không có tag |
| S3 | `backend/scripts/gen_openapi.py:145` | chỉ báo | luật 4 đòi `` `CODE` `` trong mô tả: ghi quy ước vào 04 §5.6 ở sync |
| S5 = T6 | `backend/scripts/gen_openapi.py:114` | chỉ báo | nhận lỗi mặc định bằng mô tả; đánh đổi ghi trong docstring `quality_violations` và Gap |
| T1 | `backend/shared/tests/test_api_schema.py:360` | đã sửa | gán `error_codes` trước khi assert (CONTRIBUTING *Quy ước code*) |
| T2, T5 | `backend/shared/tests/test_api_schema.py` | đã sửa | bỏ logic chép từ checker; test operation gọi `quality_violations(...) == []`; test lỗi mặc định tách 4 test; loader dùng chung `tests/helpers.py` |
| T3 | `backend/shared/api/schema.py:125` | đã sửa | comment lý do `type: ignore[override]` (chữ ký DRF gốc khác) |
| T4 | `backend/scripts/gen_openapi.py:27` | đã sửa | dùng `API_APP_PATH` public của `shared.api.schema` |
| T7 | `backend/scripts/gen_openapi.py:92,136` | đã sửa | `operation_label`, `example_values` |
| T8 | `.claude/skills/ship-ticket-fashion/scripts/common.py:52` | đã sửa | lỗi rõ khi ticket ngoài `.scratch`; test feature lồng trong `test_scripts.py` |

Trục Bug soi thêm, không thấy lỗi: `DEFAULT_PARSER_CLASSES` chỉ `JSONParser` (không view nào nhận form/multipart), `get_tags`, `get_description`, `_map_basic_serializer`, exit code của `--check`.

#### Commit

| Task | Phase | AC | Commit | File |
| --- | --- | --- | --- | --- |
| plan | 1 grill | — | `00da75f` docs: plan openapi docs quality ticket | 2 |
| S1 | 2 code | 1, 3, 4 | `0658a14` feat(shared): derive openapi tags and english default errors | 4 |
| S2 | 2 code | 2 | `350e044` feat: annotate current api operations with english summaries and examples | 5 |
| S3 | 2 code | 5 | `2c7d9b1` feat(scripts): check openapi annotation quality in gen_openapi --check | 2 |
| R1 | 4 review | — | `38139af` fix(openapi): address review findings on annotation checker | 8 |
| sync | 5 sync | 6 | (commit này) docs: sync docs and report for openapi docs quality ticket | 9 |

#### Tài liệu đã cập nhật

- `docs/architecture/04-api-contract.md` §5.6: lỗi mặc định 401/403/503 (bỏ câu "chưa khai mặc định"), ví dụ và `Retry-After`; chú thích bắt buộc và checker; quy ước `` `CODE` `` trong mô tả lỗi tự khai (S3); ngoại lệ tiếng Anh trên Swagger; chỉ JSON; không `SERVERS`.
- `docs/architecture/13-python-django-coding-style.md` §2: dòng *Chữ trên Swagger*.
- `docs/architecture/12-testing-strategy.md` §5 và bảng cổng chặn: bỏ "frontend sinh TS client", thêm luật chú thích của `--check`.
- `docs/architecture/02-backend-structure.md`: `scripts/gen_openapi.py` trong cây, mô tả `shared/api/schema.py`, dòng `drf-spectacular`.
- `docs/architecture/08-local-development.md` §3: `make lint` kiểm chú thích.
- `.claude/skills/ship-ticket-fashion/phases/2-code.md` bước 1: nhắc view mới có `summary` + ví dụ tiếng Anh.
- `.scratch/backlog.md`: gỡ 2 mục backend-bootstrap/22 (401/403/503; `Retry-After` và ví dụ).
- `spec.md` `## Quyết định` dòng *Checker*: luật 4, 5 khớp code sau review.
- Không thuật ngữ mới, không ADR (quyết định đảo ngược được, theo spec).

#### Ghi chú cho retro

- Skill không nhận feature lồng trong `.scratch/module-plans/` (`state.py start` báo `Không thấy ticket`); phải sửa `progress.py`/`common.py` → thay đổi trong commit `sync` của ticket này → nên chốt quy ước thư mục feature lồng trong `docs/agents/issue-tracker.md`.
- Commit ngoài task (`chore`, Refs có `/` cuối) bị `commit.py` coi là commit lạ, sau đó `commit_map.py` báo FAIL vì thiếu `Task:` → phải rebase đưa thay đổi về task `sync` → skill nên có task cho yêu cầu thêm của người dùng.
- Finding review chỉ nằm trong context phiên, `/clear` giữa lúc trục Bug chạy làm mất S1–S6, T1–T10 → phải chạy lại cả 3 trục → phase 4 nên ghi finding của mỗi trục vào file ngay khi trục trả về.
- Test tách ở vòng sửa (R1) không vào được `slices.tests` vì `tdd.py verify` chỉ chạy ở phase code → state thiếu 3 test id → skill nên cho ghi verification test ở phase review.
- Dòng *Tài liệu chi phối* viết gộp (`04-api-contract.md::3,4.4,5.1,5.6`) bị `transition --to code` từ chối → phải viết lại từng reference đầy đủ → phase 1 bước 6 nên nói rõ không gộp.
