# Báo cáo

### Báo cáo 01/11/2026

**Nhánh:** `fix/makefile-utf8-output` · **PR:** #52 · **Mode:** lite

#### Đã làm

| AC | Bằng chứng |
| --- | --- |
| 1. Windows: `make lint > out.txt` exit 0, không đặt biến môi trường | Kiểm tay trong `backend/` bằng Git Bash, GNU Make 4.4.1 (`winget install ezwinports.make`), bỏ `PYTHONUTF8`, `PYTHONIOENCODING` khỏi env. Trước khi sửa: exit 2, `UnicodeEncodeError` ở `lint-imports`. Sau R1: exit 0, `Contracts: 1 kept, 0 broken.` (không test tự động: cần make chạy trên Windows) |
| 2. `make lint` và `make test` trên CI vẫn xanh | CI không chạy `make` (`ci.yml` gọi thẳng `ruff`, `mypy`, `lint-imports`, `pytest` trong `.venv`), nên bằng chứng cho phần `make` là lần chạy local sau R1: `make lint` exit 0, `make test` 320 passed. Job `backend` của CI chứng minh lint và test vẫn xanh: chờ ở phase 6 |

`make lint` xanh (output chuyển hướng ra file) · `make test`: 320 passed trong 13.90s

#### Chưa làm

- Job `backend` của CI: chờ khi mở PR.

#### Gap

- Mỗi entry point chạy Python vẫn phải tự đặt `PYTHONUTF8` (Makefile, hook pre-commit, `env` của test, `run_logged.py`); cách sửa tận gốc ghi vào backlog (B4).

#### Thay đổi theo yêu cầu

- Hook `lint-imports` trong `.pre-commit-config.yaml` đặt `PYTHONUTF8=1`. Kiểm tay: `pre-commit run lint-imports --all-files` không đặt biến môi trường, trước khi sửa exit 1 (`UnicodeEncodeError`), sau khi sửa exit 0.
- Tiêu đề PR: `chore: run make recipes with Python UTF-8 mode`.
- B4 ghi vào `.scratch/backlog.md`.

#### Review

| Mã | Chỗ | Kết luận | Lý do |
| --- | --- | --- | --- |
| P1 / B2 | `plan.md:11`, `.github/workflows/ci.yml:113` | đã sửa | CI không chạy `make`; spec và report ghi bằng chứng local cho AC2 |
| B1 | `.pre-commit-config.yaml:42` | đã sửa | Hook crash cùng lỗi, đã tái hiện; người dùng yêu cầu sửa |
| B5 | `docs/architecture/08-local-development.md:221` | đã sửa | Câu thu hẹp lại còn lệnh Python trong recipe |
| B6 / S2 | `backend/Makefile:5` | đã sửa | ANSI code page của máy, cp1252 chỉ là ví dụ |
| S1 | commit `4a6c1ff` | đã sửa | Tiêu đề PR dùng `chore:` |
| B3 | `backend/Makefile:7` | chỉ báo | `make test` có UTF-8 còn IDE thì không; CI và production chạy Linux nên giữ như spec |
| B4 | `backend/pyproject.toml:120` | chỉ báo | Sửa tận gốc đụng ticket 04; ghi backlog |
| B7 | `.claude/skills/ship-ticket-fashion/scripts/run_logged.py:68` | chỉ báo | Việc của skill; đưa vào retro |

#### Commit

| Task | Phase | AC | Commit | File |
| --- | --- | --- | --- | --- |
| plan | 1 grill | — | `9d3970d` docs: plan makefile utf8 output ticket | 2 |
| S1 | 2 code | 1, 2 | `4a6c1ff` fix(config): run make recipes with Python UTF-8 mode | 2 |
| R1 | 4 review | — | `bef0dc3` chore: address review findings on make utf-8 output | 4 |

#### Tài liệu đã cập nhật

- `docs/architecture/08-local-development.md` §3: `Makefile` đặt `PYTHONUTF8=1`, nên các lệnh Python trong recipe ghi UTF-8 khi output chuyển hướng trên Windows; hook `lint-imports` của pre-commit cũng đặt biến này.
- `.scratch/backlog.md`: thêm dòng B4.
