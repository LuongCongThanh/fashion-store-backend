# Commit `openapi.yaml` và chặn schema lệch trong CI

Status: resolved

**PR:** #59

Blocked by: 07

Spec: [spec.md](../../spec.md)

## Việc cần làm

- Làm sau khi backend có endpoint đầu tiên.
- Sinh schema bằng `manage.py spectacular --validate --file openapi.yaml` và commit tại `backend/openapi.yaml`.
- Thêm lệnh `make openapi` để sinh lại schema.
- Thêm bước vào job `backend` của `.github/workflows/ci.yml`: sinh schema ra file tạm, so với `backend/openapi.yaml`, fail nếu khác và in hướng dẫn chạy `make openapi`.
- Xem `docs/architecture/12-testing-strategy.md` mục 5.

## Quyết định

Chốt khi grilling ngày 03/11/2026.

| Chủ đề | Quyết định |
| --- | --- |
| Lệnh sinh | `manage.py spectacular --validate --fail-on-warn --file openapi.yaml`. Thêm `--fail-on-warn` so với *Việc cần làm*: warning (serializer không đoán được, enum trùng tên) làm schema thiếu mà vẫn exit 0; `shared/tests/test_api_schema.py` đã dùng cùng cờ. `--validate` tự exit 1 khi schema sai chuẩn OpenAPI (đã thử với `VERSION` là số). |
| Seam | Script `backend/scripts/gen_openapi.py`, cùng khuôn `gen_importlinter.py`: không cờ thì `spectacular --file openapi.yaml` ghi thẳng file (lỗi thì file giữ nguyên; Python không đọc rồi ghi lại nội dung, SonarCloud coi đó là Path Traversal); `--check` sinh ra file tạm, so với file đã commit, lệch thì in diff và hướng dẫn chạy `make openapi`, exit 1. Luôn đọc/ghi `openapi.yaml` của thư mục hiện tại như `gen_importlinter.py`, không nhận đường dẫn từ CLI (SonarCloud báo Path Traversal với cờ `--schema` ở PR #59); test đặt `cwd` là thư mục tạm. Script gọi `manage.py spectacular` bằng subprocess; thiếu `DJANGO_SETTINGS_MODULE` thì đặt `config.settings.test` như pytest, mypy và CI, để `make openapi` trên máy (mặc định `manage.py` là `local`) sinh cùng file với CI (review B1). |
| File sinh và hook | `trailing-whitespace`, `end-of-file-fixer` của pre-commit bỏ qua `backend/openapi.yaml`: hook sửa file sinh thì `--check` lệch mãi (review B4). |
| Chỗ chạy `--check` | Bước Lint của job `backend` trong CI và `make lint`, cùng thứ tự ở hai nơi như `gen_importlinter.py --check`. Khác *Việc cần làm* (bước riêng trong CI) vì recipe `Makefile` không dùng cú pháp shell POSIX (ADR 0017) nên phép so sánh phải nằm trong script, và dev bắt được lệch trước khi push. |
| Độ ổn định | Đã kiểm: sinh hai lần, và với `config.settings.local` / `config.settings.test`, cho cùng output. `.gitattributes` ép LF nên không lệch dòng trên Windows. |
| Test | `backend/tests/test_gen_openapi.py`, chạy script bằng subprocess với `tests.helpers.isolated_env()` như `tests/test_gen_importlinter.py`. Schema sai chuẩn tạo bằng module settings tạm trong `tmp_path` đặt `SPECTACULAR_SETTINGS["VERSION"]` là số. |
| Tài liệu chi phối | `docs/architecture/12-testing-strategy.md::5`, `docs/architecture/08-local-development.md::3`, `docs/architecture/11-git-workflow.md::3.4`, `docs/adr/0017-windows-native-dev-api-on-host.md`, `docs/architecture/11-git-workflow.md::8` |

## Acceptance criteria

- [x] PR đổi API mà không cập nhật `backend/openapi.yaml` bị CI chặn.
- [x] `--validate` báo lỗi schema thì CI cũng fail.
