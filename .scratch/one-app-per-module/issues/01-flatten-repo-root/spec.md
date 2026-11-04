# Đưa Django project từ `backend/` lên gốc repo

Status: ready-for-agent

Blocked by: —

Spec: [spec.md](../../spec.md)

Theo [ADR 0018](../../../../docs/adr/0018-one-django-app-per-module.md): repo chỉ chứa backend nên gốc repo chính là Django project. Ticket này chỉ di chuyển; tên package Python (`config`, `shared`, `modules`) và Django app giữ nguyên tới ticket 02.

## Việc cần làm

- `git mv` toàn bộ nội dung `backend/` lên gốc, kể cả file ẩn (`.env.example`, `.python-version`, `.dockerignore`). Không chép `.venv`, cache, `.env`.
- Gộp `backend/scripts/` vào `scripts/` đang có (`scripts/setup/` giữ nguyên).
- `backend/tests/` (test công cụ) chuyển thành `tests/tooling/`.
- Sửa mọi đường dẫn `backend/`:
  - CI: `.github/workflows/ci.yml` (`working-directory`, bước "đã có backend chưa"), `.github/dependabot.yml` (`directory: /backend`), `.github/ISSUE_TEMPLATE/config.yml`.
  - `.pre-commit-config.yaml` (`files: ^backend/`, entry của mypy và import-linter).
  - `Dockerfile`, `docker-compose.yml` (build context, bind mount), `.dockerignore` loại thêm `docs/`, `.scratch/`, `.claude/`, `.agents/`, `.github/`.
  - `Makefile`, `pyproject.toml` (đường dẫn trong cấu hình ruff, pytest, coverage), `scripts/gen_importlinter.py`, `scripts/gen_openapi.py`, `scripts/setup/postgres.{sh,ps1}`.
  - IDE: `pyrightconfig.json` (bỏ `venvPath`, `root` = gốc), `.vscode/launch.json`, `.run/*.run.xml`.
  - `.sonarcloud.properties` (`openapi.yaml`), `.gitleaksignore` (thêm fingerprint mới nếu gitleaks báo lại test idempotency ở đường dẫn mới).
  - Test có đường dẫn cứng: `tests/tooling/test_event_payloads.py`, `test_module_coverage.py`, `modules/identity/tests/test_api_backoffice_clients.py`, `shared/testing/fixtures.py`.
  - Skill `ship-ticket-fashion` (`.claude/` và `.agents/`): `SKILL.md`, `phases/`, `reference/`, `gotchas/`, `scripts/` và test của nó.
- Tài liệu: `CLAUDE.md` ("chạy từ `backend/`"), `CONTRIBUTING.md`, `README.md`, `docs/agents/*.md`, `docs/architecture/04`, `07`, `08` (20 chỗ), `11`, `12`, `13`; ghi chú "Cấu trúc đích" ở đầu 02 bỏ `backend/` khỏi danh sách bố cục cũ.

## Quyết định

| Chủ đề | Quyết định |
|---|---|
| Tài liệu chi phối | `docs/adr/0018-one-django-app-per-module.md`, `docs/architecture/02-backend-structure.md::2`, `docs/architecture/08-local-development.md`, `docs/architecture/11-git-workflow.md` |
| Lịch sử | Không sửa `backend/` trong `.scratch/**`, ADR 0006, ADR 0017 |
| `.venv` | Dev xoá `backend/.venv`, chạy `uv sync` ở gốc; ghi vào mô tả PR |

## Acceptance criteria

- [ ] Không còn thư mục `backend/`. `git grep -n "backend/"` chỉ còn trong `.scratch/` và ADR lịch sử.
- [ ] Từ gốc repo: `make fmt`, `make lint`, `make test` xanh; `docker compose up` chạy được worker, beat, relay; `pre-commit run --all-files` xanh.
- [ ] CI xanh trên PR; Dependabot trỏ đúng thư mục gốc.
- [ ] Test skill `ship-ticket-fashion` xanh.
