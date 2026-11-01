# `make lint` lỗi mã hoá trên Windows khi output bị chuyển hướng

Status: resolved

**PR:** #52

Spec: [spec.md](../../spec.md)

Tách từ retro của ticket [17](../17-shared-geo/spec.md) ngày 30/10/2026.

## Bối cảnh

Trên Windows, Python ghi stdout bị chuyển hướng (pipe, file) bằng code page `cp1252`. `lint-imports` in tên contract tiếng Việt nên dừng với `UnicodeEncodeError: 'charmap' codec can't encode character 'ứ'` và exit 1, dù các contract đều giữ. Tái hiện trong `backend/`, không đặt `PYTHONIOENCODING` hay `PYTHONUTF8`: `uv run lint-imports > out.txt`. Gặp khi agent, IDE task hoặc script chạy `make lint` và đọc output. CI chạy Linux nên không gặp; `run_logged.py` của skill đặt `PYTHONIOENCODING=utf-8` nên cũng không gặp.

## Việc cần làm

- `backend/Makefile` đặt `export PYTHONUTF8 := 1` (cú pháp của make, hợp quy tắc recipe ở ADR 0017) để mọi recipe chạy Python ở chế độ UTF-8.
- Ghi vào `docs/architecture/08-local-development.md` nếu mục lệnh `make` cần nhắc.

## Quyết định

Chốt khi grilling ngày 01/11/2026.

| Chủ đề | Quyết định |
|---|---|
| Tài liệu chi phối | `backend/Makefile` → [ADR 0017](../../../../docs/adr/0017-windows-native-dev-api-on-host.md) (recipe không dùng cú pháp riêng của shell POSIX), [08](../../../../docs/architecture/08-local-development.md) §3. `docs/architecture/08-local-development.md` → §3 |
| Cách sửa | `export PYTHONUTF8 := 1` ở đầu `backend/Makefile`, như mục *Việc cần làm*. `export` là cú pháp của make nên hợp với ADR 0017. Bật chế độ UTF-8 của Python cho mọi recipe, gồm cả stdin và đọc file, chứ không chỉ stdout như `PYTHONIOENCODING` |
| Tài liệu | 08 §3 thêm một câu: `Makefile` đặt `PYTHONUTF8=1`, nên các lệnh Python trong recipe vẫn ghi UTF-8 khi output chuyển hướng trên Windows; hook `lint-imports` của pre-commit cũng đặt biến này |
| Test | Không test tự động. Test đọc chữ trong `Makefile` không kiểm được hành vi; AC1 kiểm tay trên Windows. CI không chạy `make` (`ci.yml` gọi thẳng công cụ trong `.venv`), nên bằng chứng AC2 cho phần `make` là `make lint`, `make test` chạy local sau khi sửa; CI chỉ chứng minh lint và test vẫn xanh |
| Hook pre-commit (thêm sau review, người dùng yêu cầu 01/11/2026) | Hook `lint-imports` trong `.pre-commit-config.yaml` cùng lỗi: `git commit` trên Windows bị chặn dù contract giữ. Entry đặt `PYTHONUTF8=1 uv run lint-imports` (entry chạy bằng `bash -c` nên cú pháp này hợp lệ). Kiểm tay bằng `pre-commit run lint-imports --all-files` |
| Tiêu đề PR | `chore: run make recipes with Python UTF-8 mode`: lỗi chỉ ở tooling local, `config` dành cho Django settings |
| Kiểm AC1 | Cài GNU make bằng `winget install ezwinports.make` (lệnh của 08 §2.1), rồi chạy `make lint > out.txt` trong `backend/` bằng Git Bash. Trước khi sửa đã tái hiện: `uv run lint-imports > out.txt` exit 1 vì `UnicodeEncodeError` (stdout `cp1252`); PowerShell 7 không tái hiện được |
| Mode | lite: 2 AC, không thêm model, migration hay endpoint |

## Acceptance criteria

- [x] Trên Windows, `make lint > out.txt` exit 0 khi code sạch, không đặt biến môi trường nào trước.
- [x] `make lint` và `make test` trên CI vẫn xanh.
