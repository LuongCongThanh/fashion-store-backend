# Khung project backend: pyproject, settings, health check, lint và CI

Status: resolved

Spec: [spec.md](../../spec.md)

**PR:** #20

## Việc cần làm

- Tạo `backend/` theo cây thư mục ở [02 mục 5](../../../../docs/architecture/02-backend-structure.md#2-cây-thư-mục), chỉ gồm phần M0 cần:
  - `pyproject.toml` với `[tool.uv] package = false`, cấu hình ruff, mypy, pytest, import-linter đúng như 02 mục 8 và 9.3 (`target-version = "py314"`, `python_version = "3.14"`); `.python-version` = `3.14`; `uv.lock`.
  - Dependency runtime của M0: `django` 5.2.x, `djangorestframework`, `drf-spectacular`, `psycopg[binary,pool]`, `redis`, `celery`, `django-celery-beat`, `pydantic`, `pydantic-settings`, `structlog`, `django-structlog`, `sentry-sdk[django,celery]`, `gunicorn`. Dependency dev theo 02 mục 3.2.
  - `config/env.py` (pydantic-settings) chỉ khai báo các biến nhóm "Từ M0" ở [08 mục 2.3](../../../../docs/architecture/08-local-development.md#23-biến-môi-trường); biến của mốc sau thêm ở mốc dùng tới. `config/settings/{base,local,test,production}.py`, `config/urls.py`, `config/celery.py`, `config/wsgi.py`.
  - App `shared` và app `modules`; `modules/<module>/__init__.py` cho 8 module con, chưa có model.
  - `.env.example` chỉ chứa các biến "Từ M0" của 08 mục 2.3, không chứa secret thật.
- `Makefile` với các lệnh chạy trên máy, không cần container: `test`, `lint`, `fmt` ([08 mục 3](../../../../docs/architecture/08-local-development.md#3-lệnh-hằng-ngày-makefile)). Các lệnh dùng container thêm ở ticket [15](../15-docker-compose-local/spec.md), `gen_importlinter.py --check` thêm vào `make lint` ở ticket [04](../04-import-linter-test-factories/spec.md).
- Job `backend` trong `.github/workflows/ci.yml`:
  - Thêm `services:` gồm `postgres:18` và `valkey/valkey:8` (pin tới bản vá), có health check.
  - Thêm khối `env:` ở cấp job: `DJANGO_SETTINGS_MODULE=config.settings.test`, `DATABASE_URL`, `REDIS_URL` trỏ tới hai service trên, và giá trị giả cho các biến bắt buộc còn lại của M0. Không commit file `.env` cho CI.
- `/healthz` và `/readyz` theo [04 mục 4.4](../../../../docs/architecture/04-api-contract.md#44-vận-hành).
- Kiểm tra cờ của `cz` theo bản `commitizen` được pin, gỡ nhãn **[Cần xác minh]** ở [11](../../../../docs/architecture/11-git-workflow.md).
- Một smoke test: Django khởi động với `config.settings.test`, `/healthz` trả 200, `/readyz` trả 200 khi có DB.

`make test` ở local cần PostgreSQL trên máy, gọi qua `localhost` (cài bằng `scripts/setup/postgres.sh`). Ticket này không cần container gọi được PostgreSQL; phần đó thuộc ticket 08 và 15.

## Acceptance criteria

- [x] `make lint` (ruff check, ruff format --check, mypy, lint-imports) và `make test` qua ở local.
- [x] Job `backend` trong `.github/workflows/ci.yml` bắt đầu chạy thật (đã có `backend/pyproject.toml`), dùng PostgreSQL và Valkey của `services:`, và xanh.
- [x] `pre-commit run --all-files` chạy ruff, mypy, import-linter trên `backend/` và qua.
- [x] Thiếu một biến bắt buộc của M0 trong `.env` thì Django báo lỗi rõ tên biến ngay khi khởi động. Không có biến nào của M1 trở đi bị bắt buộc.
- [x] `11` không còn nhãn **[Cần xác minh]** về cờ của `cz`.
- [x] Tài liệu nào lệch với cái đã làm (lệnh Makefile, biến môi trường, phiên bản pin) được sửa trong cùng PR.
