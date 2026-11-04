# 01 – Đưa Django project từ `backend/` lên gốc repo

Status: ready-for-agent · Ưu tiên: 2 · Blocked by: — · **PR:**

Spec: [spec.md](../../spec.md)

## Mục tiêu
Mọi lệnh (`make`, `uv`, `docker compose`, `pre-commit`) chạy từ gốc repo; không còn thư mục `backend/`. Chỉ di chuyển: tên package (`config`, `shared`, `modules`) và Django app giữ nguyên tới ticket 02.

## Việc cần làm
- [x] `git mv` toàn bộ `backend/` lên gốc, kể cả file ẩn (`.env.example`, `.python-version`, `.dockerignore`). Không chép `.venv`, cache, `.env`.
- [x] Xoá `backend/.claude/` (chỉ chứa lock của phiên cũ, không track).
- [x] Gộp `backend/scripts/` vào `scripts/` (giữ nguyên `scripts/setup/`).
- [x] `backend/tests/` (test công cụ) → `tests/tooling/`.
- [x] Sửa đường dẫn `backend/` trong:
  - [x] CI: `.github/workflows/ci.yml` (`working-directory`, bước "đã có backend chưa"), `.github/dependabot.yml` (`directory: /backend`), `.github/ISSUE_TEMPLATE/config.yml`.
  - [x] `.pre-commit-config.yaml` (`files: ^backend/`, entry mypy và import-linter).
  - [x] `Dockerfile`, `docker-compose.yml` (build context, bind mount); `.dockerignore` loại thêm `docs/`, `.scratch/`, `.claude/`, `.agents/`, `.github/`.
  - [x] `Makefile`, `pyproject.toml` (ruff, pytest, coverage), `scripts/gen_importlinter.py`, `scripts/gen_openapi.py`, `scripts/setup/postgres.{sh,ps1}`.
  - [x] IDE: `pyrightconfig.json` (bỏ `venvPath`, `root` = gốc), `.vscode/launch.json`, `.run/*.run.xml`.
  - [x] `.sonarcloud.properties` (`openapi.yaml`); `.gitleaksignore` (thêm fingerprint mới nếu gitleaks báo lại test idempotency ở đường dẫn mới).
  - [x] Test có đường dẫn cứng: `tests/tooling/test_event_payloads.py`, `test_module_coverage.py`, `modules/identity/tests/test_api_backoffice_clients.py`, `shared/testing/fixtures.py`.
  - [x] Skill `ship-ticket-fashion` (`.claude/` và `.agents/`): `SKILL.md`, `phases/`, `reference/`, `gotchas/`, `scripts/` và test.
- [x] Tài liệu: `CLAUDE.md` ("chạy từ `backend/`"), `CONTRIBUTING.md`, `README.md`, `docs/agents/*.md`, `docs/architecture/04`, `07`, `08` (20 chỗ), `11`, `12`, `13`; ghi chú "Cấu trúc đích" đầu `02` bỏ `backend/` khỏi danh sách bố cục cũ.
- [x] Mô tả PR dặn dev: xoá `backend/.venv`, chạy `uv sync` ở gốc.

## Quyết định
- Gốc repo chính là Django project vì repo chỉ chứa backend: [ADR 0018](../../../../docs/adr/0018-one-django-app-per-module.md).
- Tài liệu chi phối: [02 mục 2](../../../../docs/architecture/02-backend-structure.md), [08](../../../../docs/architecture/08-local-development.md), [11](../../../../docs/architecture/11-git-workflow.md).
- Không sửa `backend/` trong `.scratch/**`, ADR 0006, ADR 0017 (lịch sử).

## Acceptance criteria
- [x] Không còn thư mục `backend/`; `git grep -n "backend/"` chỉ còn trong `.scratch/` và ADR lịch sử.
- [x] Số test thu thập (`pytest --collect-only -q`) trước và sau bằng nhau.
- [x] Từ gốc: `make fmt`, `make lint`, `make test` xanh; `docker compose up` chạy được worker, beat, relay; `pre-commit run --all-files` xanh.
- [ ] CI xanh trên PR; Dependabot trỏ đúng thư mục gốc.
- [x] Test skill `ship-ticket-fashion` xanh.

## Ghi chú
- Ticket mở khác còn ghi `backend/...` (vd. backend-bootstrap 14, 20) là lịch sử `.scratch/`, không sửa; người làm sau tự hiểu là đường dẫn ở gốc.
