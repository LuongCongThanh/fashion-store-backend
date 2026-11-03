# Báo cáo

### Báo cáo 03/11/2026

**Nhánh:** `chore/openapi-schema-ci-gate` · **PR:** #59 · **Mode:** lite

#### Đã làm

| AC | Bằng chứng |
| --- | --- |
| 1. PR đổi API mà không cập nhật `backend/openapi.yaml` bị CI chặn | `tests/test_gen_openapi.py::test_check_fails_when_committed_schema_is_stale`, `tests/test_gen_openapi.py::test_check_passes_when_schema_is_current`; `scripts/gen_openapi.py --check` chạy trong bước Lint của job `backend` (`.github/workflows/ci.yml`) và trong `make lint` |
| 2. `--validate` báo lỗi schema thì CI fail | `tests/test_gen_openapi.py::test_generation_fails_when_schema_is_invalid` (settings tạm đặt `VERSION` là số: exit 1, file đích giữ nguyên); `--fail-on-warn`: `tests/test_gen_openapi.py::test_generation_fails_on_spectacular_warning` |

Thêm ở review: `tests/test_gen_openapi.py::test_check_rejects_non_utf8_schema` (file schema không phải UTF-8 → `ERROR`, exit 2). Đột biến bỏ `--validate` hoặc `--fail-on-warn` khỏi script làm đúng một test đỏ.

`make lint` xanh (gồm `gen_openapi.py --check` trên `backend/openapi.yaml`) · `make test`: 372 passed trong 12.41s, branch coverage `identity` 100%, `shared` 97.62%

#### Chưa làm

- Không

#### Gap

- Không còn gate OpenAPI mục tiêu; gate migration (12 mục 6) vẫn chưa hoạt động, ngoài ticket này.
- Chưa có `oasdiff` (12 mục 9): reviewer tự đọc diff `openapi.yaml` để bắt breaking change.

#### Thay đổi theo yêu cầu

- SonarCloud (PR #59, Quality Gate E Security): `gen_openapi.py:57`, `:72` Path Traversal vì đường dẫn đích đến từ cờ `--schema` → bỏ cờ, luôn dùng `openapi.yaml` của thư mục hiện tại như `gen_importlinter.py`; test đặt `cwd` là thư mục tạm. `gen_openapi.py:43` cú pháp suppression → lý do của `noqa: S603` về dòng riêng (SonarCloud đọc cả chỉ thị noqa), đảo lại S2 trong `scripts/`.
- SonarCloud lần 2: `gen_openapi.py:72` Path Traversal via file content (ghi nội dung file tạm ra `openapi.yaml`) → chế độ ghi để `spectacular --file` ghi thẳng file đích (spectacular chỉ ghi khi sinh và kiểm xong); chỉ `--check` dùng file tạm.

#### Review

| Mã | Chỗ | Kết luận | Lý do |
| --- | --- | --- | --- |
| B1 | `backend/scripts/gen_openapi.py:35` | đã sửa | Thiếu `DJANGO_SETTINGS_MODULE` thì dùng `config.settings.test` như CI; sửa dòng *Seam* trong `## Quyết định` |
| B2 = P2, S4 | `backend/tests/test_gen_openapi.py:54` | đã sửa | Test AC2 chạy không `--check`, kiểm thông báo lỗi và file giữ nguyên |
| P1 | `backend/scripts/gen_openapi.py:30` | đã sửa | Thêm test `--fail-on-warn` bằng urlconf có `APIView` không serializer |
| B5 | `backend/tests/test_gen_openapi.py:33` | đã sửa | Fixture `scope="module"` sinh schema gốc một lần |
| S3 | `backend/scripts/gen_openapi.py:46` | đã sửa | `UnicodeDecodeError` → `GeneratorError`, `ERROR` + exit 2 như `gen_importlinter.py` |
| S1 = B7 | `backend/scripts/gen_openapi.py:77` | đã sửa | `raise SystemExit(main())` |
| S2 = B6 | `backend/scripts/gen_openapi.py:34` | đã sửa, rồi đảo ở `ci` | SonarCloud báo lý do cùng dòng là sai cú pháp suppression; trong `scripts/` lý do ở dòng riêng |
| B4 | `.pre-commit-config.yaml:18` | đã sửa | `end-of-file-fixer`, `trailing-whitespace` bỏ qua `backend/openapi.yaml` |
| B3 | `docs/architecture/11-git-workflow.md:142` | đã sửa ở sync | Tài liệu cập nhật trong commit `sync` |
| S5 | `backend/scripts/gen_openapi.py:_run` | chỉ báo | Khối so sánh/diff/ghi lặp với `gen_importlinter.py`; mới 2 lần, tách khi có generator thứ ba |

#### Commit

| Task | Phase | AC | Commit | File |
| --- | --- | --- | --- | --- |
| plan | 1 grill | — | `2dec7cc` docs: plan openapi schema drift check ticket | 2 |
| S1 | 2 code | 1, 2 | `7e37437` ci(backend): commit openapi.yaml and fail on schema drift | 5 |
| R1 | 4 review | — | `ae3a551` fix(backend): address review findings on openapi schema check | 5 |

#### Tài liệu đã cập nhật

- `docs/architecture/12-testing-strategy.md`: mục 5 mô tả `make openapi`, `gen_openapi.py --check`, `--fail-on-warn`, settings `test`, hook bỏ qua file sinh; mục 8 thêm dòng cổng `gen_openapi.py --check`, bỏ OpenAPI khỏi gate chưa hoạt động.
- `docs/architecture/11-git-workflow.md` mục 3.5: job `backend` có `gen_openapi.py --check`; chỉ còn gate migration chưa hoạt động.
- `docs/architecture/08-local-development.md` mục 3: `make lint` có `gen_openapi.py --check`, thêm dòng `make openapi`.
- `docs/architecture/04-api-contract.md`: dòng trạng thái trỏ tới `backend/openapi.yaml` đã commit; sửa link "theo12".

#### Ghi chú cho retro

- PostgreSQL local chưa có role/database `fashion` nên `make test` lỗi 164 test với "password authentication failed"; phase 1 bước 1 chạy `manage.py check --database default` báo xanh dù không mở kết nối thật, nên lỗi chỉ lộ ở cuối phase code → gợi ý: kiểm kết nối bằng `connection.ensure_connection()` thay vì `check`.
- Test thêm ở vòng sửa review không ghi được bằng chứng vào slice vì `tdd.py` chỉ chạy ở phase `code` (commit `ae3a551`, `notes.R1` trong state) → gợi ý: cho `tdd.py` nhận vòng `R<n>` ở phase review.
