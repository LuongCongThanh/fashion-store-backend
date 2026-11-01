# 08. Môi trường phát triển local (macOS và Windows)

> Trạng thái: **Đã chốt cho MVP** ([quy ước](../../README.md#trạng-thái-tài-liệu)).
> **PostgreSQL cài trên máy** (macOS: Homebrew bằng `scripts/setup/postgres.sh`; Windows: bộ cài EDB rồi `scripts/setup/postgres.ps1`), theo [ADR 0015](../adr/0015-local-postgres-on-host.md) và [ADR 0017](../adr/0017-windows-native-dev-api-on-host.md). **Django API chạy trên máy** bằng `uv run`. Worker, beat, relay, Redis, Mailpit chạy bằng **Docker Compose**. Trên máy cần Docker, `uv` ≥ 0.13 (uv tự tải Python 3.14 theo `backend/.python-version`), `git`, `make`. Windows không dùng WSL2.

## 1. Tổng quan

```mermaid
graph LR
    subgraph host [macOS / Windows]
        pg[(PostgreSQL bản mới nhất · :5432<br/>cài trên máy)]
        api[api · :8000<br/>uv run runserver]
        subgraph docker [Docker Compose]
            worker[worker]
            beat[beat]
            relay[relay]
            redis[(redis · :6380 trên máy)]
            mailpit[mailpit · :1025 / :8025]
        end
    end
    api -- localhost --> pg
    api -- localhost:6380 --> redis
    api -- localhost:1025 --> mailpit
    worker -- host.docker.internal --> pg
    beat --> pg
    relay --> pg
    worker --> redis
    beat --> redis
    relay --> redis
    worker --> mailpit
```

| Thành phần | Chạy ở đâu | Cổng |
|---|---|---|
| PostgreSQL (bản major mới nhất) | Cài trên máy: Homebrew (macOS), bộ cài EDB (Windows). Container gọi qua `host.docker.internal` | macOS: 5432, hoặc cổng trống kế tiếp nếu 5432 đang bận; Windows: cổng chọn lúc cài EDB (mặc định 5432). Ghi vào `PG_PORT` |
| Django API | Trên máy, `uv run python manage.py runserver`; sửa code tự reload | 8000 |
| Celery worker, Celery Beat, Outbox relay | Docker, bind mount `backend/`; sửa code xong chạy `make restart-worker` | — |
| Redis (Valkey 8, cùng bản với ElastiCache) | Docker | 6380 trên máy (`REDIS_PORT`), 6379 trong mạng Compose |
| Mailpit | Docker | 1025 (SMTP), 8025 (giao diện xem mail) |
| Ảnh Sản phẩm | Ổ đĩa, thư mục `backend/media/` | — |
| VNPay, MoMo | Fake Gateway trong Django | — |
| GHN | Fake, hoặc sandbox thật (gọi ra được từ local) | — |

## 2. Cài đặt lần đầu

### 2.1. Công cụ

#### macOS

```bash
brew install uv
# Docker Desktop (hoặc OrbStack) cài riêng
```

PostgreSQL: xem mục 2.2.

#### Windows

Trên Windows làm thẳng trên Windows, **không dùng WSL2** ([ADR 0017](../adr/0017-windows-native-dev-api-on-host.md)). Lệnh `make`, `uv run` và `docker compose` trong tài liệu này chạy được trong PowerShell 7 hoặc Git Bash; lệnh shell thuần (ví dụ `bash scripts/...`) chạy trong Git Bash.

1. **Công cụ**, cài bằng winget (PowerShell):
   ```powershell
   winget install Git.Git astral-sh.uv ezwinports.make Docker.DockerDesktop
   git config --global core.autocrlf false   # .gitattributes đã quy định LF/CRLF cho từng loại file
   ```
2. **PostgreSQL**: xem mục 2.2.

3. **Clone repo** vào bất kỳ thư mục nào trên ổ Windows. Nên chọn đường dẫn không có dấu cách.

4. **IDE**: xem mục 6.

| Lỗi hay gặp trên Windows | Cách xử lý |
|---|---|
| `make` báo không tìm thấy | Mở terminal mới sau khi cài để nhận `PATH` mới |
| Lỗi `/bin/sh^M: bad interpreter` trong container | File bị đổi sang CRLF; repo có `.gitattributes` ép LF, chạy `git add --renormalize .` |
| Cổng 6379 đã bị Redis hoặc Memurai của project khác giữ | Không sao: Redis của Compose mở ra máy ở `REDIS_PORT` (mặc định 6380) |

### 2.2. Database

PostgreSQL cài trên máy, không chạy trong Docker ([ADR 0015](../adr/0015-local-postgres-on-host.md), [ADR 0017](../adr/0017-windows-native-dev-api-on-host.md)). Dù cài cách nào, kết quả cuối cùng phải giống nhau:

- Role `fashion` (mật khẩu `fashion`, quyền `LOGIN CREATEDB`) và database `fashion` do `fashion` sở hữu. Nhờ `CREATEDB`, pytest-django tự tạo và xoá database test (`test_fashion`, và `test_fashion_gw0`, `test_fashion_gw1`… khi chạy song song).
- Extension `unaccent`, `pg_trgm`, `btree_gist` **có sẵn để cài** (nằm trong `pg_available_extensions`). Extension do **migration** tạo, giống CI và RDS. Cả ba là trusted extension (từ PostgreSQL 13), nên chủ database tự tạo được, không cần superuser.
- `DATABASE_URL` và `PG_PORT` chép vào `backend/.env` (mục 2.3).

#### macOS

Từ gốc repo:

```bash
bash scripts/setup/postgres.sh
```

Script làm các việc sau, chạy lại nhiều lần vẫn an toàn:

1. Kiểm tra `git`, `make`, `docker`, `uv` (chỉ báo thiếu, không tự cài).
2. Tìm bản major mới nhất `postgresql@<major>` trên Homebrew. Máy đã có bản đó thì dùng luôn, chưa có thì cài. (Script cũng chạy được trên Ubuntu/Debian bằng apt PGDG, ngoài phạm vi hỗ trợ chính thức.)
3. Không đụng tới cluster PostgreSQL khác đang có. Nếu cổng 5432 đã bị cluster khác giữ, cluster mới chạy ở cổng trống kế tiếp (5433…).
4. Tạo hoặc cập nhật role và database `fashion`, kiểm tra extension.
5. Thử đăng nhập bằng `fashion` qua `localhost`, rồi in `DATABASE_URL` và `PG_PORT`.

#### Windows

1. **Cài PostgreSQL một lần**, bằng quyền Administrator, lấy bản major mới nhất:
   ```powershell
   winget install PostgreSQL.PostgreSQL.18
   ```
   Hoặc tải bộ cài EDB từ postgresql.org. Bộ cài hỏi mật khẩu cho superuser `postgres` (tự đặt và tự giữ, không ghi vào repo) và cổng (để mặc định 5432 nếu trống). Kèm theo có pgAdmin 4; extension `unaccent`, `pg_trgm`, `btree_gist` có sẵn trong bản cài. PostgreSQL chạy thành Windows service `postgresql-x64-<major>`, tự bật cùng máy.

2. **Tạo role và database**, từ gốc repo trong PowerShell:
   ```powershell
   pwsh scripts/setup/postgres.ps1
   ```
   Script hỏi mật khẩu `postgres` (nhập ẩn, không lưu), rồi làm các việc sau, chạy lại nhiều lần vẫn an toàn: kiểm tra `git`, `make`, `docker`, `uv`; tìm service `postgresql-x64-*` có major cao nhất và đọc cổng của nó (chưa cài thì in lệnh winget ở bước 1 rồi dừng); tạo hoặc cập nhật role và database `fashion`; kiểm tra extension; thử đăng nhập bằng `fashion` rồi in `DATABASE_URL` và `PG_PORT`.

   Chưa có script thì làm tay trong Query Tool của pgAdmin, đăng nhập bằng `postgres`:
   ```sql
   CREATE ROLE fashion LOGIN CREATEDB PASSWORD 'fashion';
   CREATE DATABASE fashion OWNER fashion;
   ```

Production (RDS) và CI (`postgres:18`) có thể chạy bản major cũ hơn local: không dùng tính năng chỉ có ở bản mới; CI sẽ bắt lỗi này. Trên Windows, PostgreSQL là bản build cho Windows, còn CI và production chạy Linux: khác biệt về collation và locale có thể chỉ lộ ra trên CI.

Kết nối:

- API, IDE, `psql`, pytest chạy trên máy: `localhost:<PG_PORT>`.
- Container trong Compose (worker, beat, relay, migrate): `host.docker.internal:<PG_PORT>`, vì Compose đặt `DATABASE_HOST` thay host của `DATABASE_URL` (mục 7).
  - Windows (Docker Desktop, PostgreSQL 18 bản EDB): đã xác minh ngày 2026-10-29, không cần sửa cấu hình. Docker Desktop chuyển kết nối qua localhost của máy, nên PostgreSQL thấy client là `127.0.0.1`, và dòng `host all all 127.0.0.1/32` mặc định trong `pg_hba.conf` của EDB đã cho phép.
  - macOS **[Cần xác minh]**. Nếu container không kết nối được thì cách sửa (`listen_addresses`, `pg_hba.conf`) sẽ được ghi ở đây (ticket `.scratch/backend-bootstrap/issues/13-local-postgres-installer-macos/spec.md`).

Dữ liệu nằm trên máy, nên `make down` không làm mất dữ liệu. Thường không cần xoá; chỉ xoá khi migration bị rối (đổi qua lại giữa các nhánh có migration xung đột) hoặc muốn seed lại từ đầu: `make db-reset` (drop và tạo lại database `fashion`, giữ role, rồi migrate).

### 2.3. Biến môi trường

```bash
cd backend
cp .env.example .env
```

Các biến chính trong `.env`. Mỗi biến được khai báo trong `config/env.py` ở mốc đầu tiên dùng tới nó ([roadmap](../../.scratch/mvp-roadmap/map.md)); `.env.example` chỉ chứa biến đã khai báo. Thiếu biến bắt buộc thì Django dừng ngay khi khởi động và báo tên biến. `DATABASE_URL` thiếu user, thiếu host hoặc có tên database rỗng hay chứa `/`, `@`, `:` cũng dừng như vậy, thông báo nêu phần sai mà không in giá trị URL; password có ký tự `/`, `@`, `:`, `?`, `#` phải mã hoá phần trăm (`%2F`, `%40`…).

```dotenv
# Từ M0
DJANGO_SETTINGS_MODULE=config.settings.local
DJANGO_SECRET_KEY=local-only-change-me
DATABASE_URL=postgres://fashion:fashion@localhost:5432/fashion   # theo output của scripts/setup/postgres.sh hoặc postgres.ps1
PG_PORT=5432                                                      # cổng PostgreSQL trên máy, trùng cổng trong DATABASE_URL
REDIS_PORT=6380                                                   # cổng Redis của Compose mở ra máy
REDIS_URL=redis://localhost:6380/0
EMAIL_HOST=localhost
EMAIL_PORT=1025
PII_HMAC_KEYS=local-pii-1:local-pii-secret                # kid:secret, nhiều khoá cách nhau bằng dấu phẩy, khoá đầu dùng cho giá trị mới, không xoá khoá cũ (ADR 0016); `check --deploy` đòi secret từ 32 byte
STOREFRONT_ORIGIN=http://localhost:3000
BFF_SHARED_SECRET=local-bff-secret

# Từ M1 (đăng nhập, JWT, refresh)
JWT_PRIVATE_KEY_PATH=.secrets/jwt_ed25519.pem
JWT_KEY_ID=local-1
REFRESH_REPLAY_KEY_ID=local-replay-1
REFRESH_REPLAY_KEY_PATH=.secrets/refresh_replay.key

# Từ M2 (checkout COD, Fake GHN)
QUOTE_SIGNING_KEYS=local-quote-1:local-quote-secret       # kid:secret, nhiều khoá cách nhau bằng dấu phẩy, khoá đầu dùng để ký (04 mục 5.3)
SHIPPING_PROVIDER=fake
FAKE_PROVIDERS_ENABLED=true

# Từ M3 (thanh toán online)
PAYMENT_PROVIDER_VNPAY=fake
PAYMENT_PROVIDER_MOMO=fake

# Từ M6 (đăng nhập Google)
GOOGLE_OAUTH_CLIENT_ID=
```

`.env` viết cho tiến trình chạy trên máy (API, pytest, IDE): mọi địa chỉ đều là `localhost`. Container trong Compose ghi đè `REDIS_URL`, `EMAIL_HOST` và đặt `DATABASE_HOST` (thay host của `DATABASE_URL`, giữ user, mật khẩu, cổng, tên DB) trong khối `environment:` (mục 7), nên không cần sửa `.env` cho container và `docker-compose.yml` không chứa mật khẩu.

`DJANGO_SETTINGS_MODULE` trong `.env` chỉ có tác dụng trong Compose, vì Compose nạp `.env` vào biến môi trường của container; khi `.env` được đọc thì settings đã được chọn rồi. Chạy trên máy thì `export` biến này, hoặc dùng mặc định `config.settings.local` của `manage.py`. `wsgi.py` và Celery không có giá trị mặc định: process deploy thiếu biến này thì dừng ngay.

`BFF_SHARED_SECRET` phải trùng với giá trị cấu hình ở Next.js local. Next.js gửi secret này trong header `X-BFF-Secret` kèm `X-Client-IP`, và Django chỉ tin `X-Client-IP` khi secret đúng và IP là IPv4/IPv6 hợp lệ ([ADR 0009](../adr/0009-nextjs-bff-django-private.md)). Biến nhận 1 hoặc 2 secret cách nhau bằng dấu phẩy (2 khi đang xoay, [05 mục 5](./05-auth-security.md)); rỗng hoặc hơn 2 thì Django dừng lúc khởi động. Gọi thẳng `localhost:8000` từ Swagger UI hay `curl` vẫn chạy được, chỉ là throttle tính theo IP của máy gọi.

Từ M1, sinh khoá JWT cho local, chạy từ `backend/` (dùng `cryptography`, dependency có từ M1; chạy được trên mọi shell):

```bash
uv run python -c "from pathlib import Path; from cryptography.hazmat.primitives import serialization as s; from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; Path('.secrets').mkdir(exist_ok=True); Path('.secrets/jwt_ed25519.pem').open('xb').write(Ed25519PrivateKey.generate().private_bytes(s.Encoding.PEM, s.PrivateFormat.PKCS8, s.NoEncryption()))"
```

Khoá RefreshReplay độc lập JWT, tạo một lần cho local và không commit. Chạy từ `backend/`:

```bash
uv run python -c "from pathlib import Path; import secrets; Path('.secrets').mkdir(exist_ok=True); Path('.secrets/refresh_replay.key').open('xb').write(secrets.token_bytes(32))"
```

Hai lệnh từ chối ghi đè key đã có; không tạo lại mỗi lần khởi động. Key có ID để xoay và các API replica phải cùng đọc được key còn hiệu lực trong cửa sổ replay. STOREFRONT_ORIGIN chỉ là origin tin cậy, không kèm path/query/userinfo; payment return path do backend cố định.

### 2.4. Chạy

Lần đầu, sau khi đã có PostgreSQL (mục 2.2) và `.env` (mục 2.3). Mọi lệnh chạy từ `backend/`; cột "Có từ" giống mục 3, lệnh chưa tới mốc thì chưa dùng được.

| Bước | Lệnh | Làm gì | Có từ |
|---|---|---|---|
| 1 | `uv sync` | Tạo `backend/.venv` với Python 3.14 và dependency (cả nhóm dev) | M0 (ticket 07) |
| 2 | `uv run pre-commit install` | Cài hook `pre-commit` và `commit-msg` vào `.git/hooks`, một lần cho mỗi bản clone ([11](./11-git-workflow.md) mục 3.4) | M0 (ticket 07) |
| 3 | `make up` | `docker compose up -d --build`; service `migrate` chạy migration và `sync_beat_schedule` trước khi worker, beat, relay khởi động (mục 7) | M0 (ticket 15) |
| 4 | `make load-geo` | Nạp 34 tỉnh/thành và phường/xã | M0 (ticket 17) |
| 5 | `make create-admin` | Tạo Tài khoản Admin: hỏi email, nhập mật khẩu hai lần (không có cờ `--password`), mật khẩu tối thiểu 8 ký tự theo [05](./05-auth-security.md) mục 3 | M0 (ticket 12) |
| 6 | `make seed` | Tạo Kho, danh mục, Sản phẩm mẫu; Voucher mẫu từ M2 | M1 |
| 7 | `make run` | Chạy API trên máy (`uv run python manage.py runserver`), tự reload khi sửa code | M0 (ticket 15) |

`make migrate` chỉ cần khi đã có migration mới mà không muốn khởi động lại container.

| Địa chỉ | Dùng để |
|---|---|
| http://localhost:8000/api/docs/ | Swagger UI, gọi thử API |
| http://localhost:8025 | Mailpit, xem email đã gửi |
| http://localhost:8000/dev/fake-gateway/ | Fake Gateway (từ M3) |

Không có Django Admin ([ADR 0004](../adr/0004-custom-nextjs-admin.md)). Xem dữ liệu bằng `psql`, công cụ database của IDE hoặc `make shell`.

## 3. Lệnh hằng ngày (`Makefile`)

Mỗi lệnh được thêm vào `Makefile` cùng ticket tạo ra lệnh mà nó gọi, nên cột "Có từ" cho biết lệnh nào đã dùng được. `Makefile` đặt `PYTHONUTF8=1`, nên trên Windows các lệnh Python trong recipe vẫn ghi UTF-8 khi output chuyển hướng ra file hay pipe; hook `lint-imports` của pre-commit cũng đặt biến này.

| Lệnh | Làm gì | Có từ |
|---|---|---|
| `make up` / `make down` | Bật / tắt các container; `make up` chạy service `migrate` trước (mục 7) | M0 (ticket 15) |
| `make run` | Chạy API trên máy (`uv run python manage.py runserver`) | M0 (ticket 15) |
| `make restart-worker` | Khởi động lại worker, beat, relay sau khi sửa code (Celery không tự reload) | M0 (ticket 15) |
| `make logs s=worker` | Xem log của một service | M0 (ticket 15) |
| `make shell` | `manage.py shell` chạy trên máy | M0 (ticket 15) |
| `make makemigrations` / `make migrate` | Tạo / chạy migration; `make migrate` chạy thêm `manage.py sync_beat_schedule` để ghi lịch job vào DB ([07](./07-async-events-jobs.md) mục 3.2) | M0 (ticket 15) |
| `make db-reset` | Xoá và tạo lại database `fashion` (`manage.py reset_db`, chỉ chạy khi `DEBUG` bật, host là `localhost` và server nghe ở loopback) rồi `make migrate` (mục 2.2) | M0 (ticket 15) |
| `make test` | `pytest -n auto` | M0 (ticket 07) |
| `make lint` | `ruff check`, `ruff format --check`, `mypy`, `lint-imports`, `scripts/gen_importlinter.py --check` | M0 (ticket 07; `gen_importlinter.py --check` từ ticket 04) |
| `make fmt` | `ruff format` + `ruff check --fix` | M0 (ticket 07) |
| `make load-geo` | Nạp 34 tỉnh/thành và phường/xã | M0 (ticket 17) |
| `make create-admin` | Tạo Tài khoản Admin (`manage.py create_staff --admin`) | M0 (ticket 12) |
| `make seed` | Tạo Kho, danh mục, Sản phẩm mẫu, Voucher mẫu | M1 (Voucher mẫu từ M2) |
| `make tunnel` | Mở Cloudflare Tunnel để nghiệm thu với sandbox ([06](./06-integrations.md) mục 8) | M7 |

### 3.1. Lệnh không qua `make`

Chạy từ `backend/`, trừ khi ghi khác. Đều dùng được từ M0 (ticket 07).

| Lệnh | Làm gì |
|---|---|
| `uv sync` | Cập nhật `.venv` theo `uv.lock`, ví dụ sau khi `git pull` có đổi dependency |
| `uv sync --locked` | Như CI: báo lỗi nếu `uv.lock` lệch `pyproject.toml` |
| `uv run pytest <file>` / `uv run pytest <file>::<tên_test>` | Chạy một file hoặc một test; thêm `-x` để dừng ở test lỗi đầu tiên |
| `uv run python manage.py check` | System check của Django và của dự án (`shared/checks.py`) |
| `uv run python manage.py check --deploy --settings=config.settings.production` | Kiểm tra cấu hình bảo mật của production; với giá trị local sẽ có cảnh báo (secret ngắn, `ALLOWED_HOSTS` rỗng) |
| `uv run python manage.py <lệnh>` | Lệnh quản trị khác: `showmigrations`, `sqlmigrate`, `dbshell`… |
| `uv run pip-audit --strict` | Quét lỗ hổng dependency như job `backend` của CI; gọi mạng nên không gộp vào `make lint` |
| `uv run pre-commit install` | Cài hook vào `.git/hooks`, một lần cho mỗi bản clone (mục 2.4) |
| `uv run pre-commit run --all-files` | Chạy mọi hook trên toàn repo, ví dụ sau khi đổi `.pre-commit-config.yaml` |
| `curl http://localhost:8000/healthz` / `curl http://localhost:8000/readyz` | API đang chạy / API kết nối được PostgreSQL (`readyz` không kiểm tra Redis) |
| Từ gốc repo: `bash scripts/setup/postgres.sh` (macOS) hoặc `pwsh scripts/setup/postgres.ps1` (Windows) | Tạo hoặc sửa role và database `fashion` (mục 2.2); chạy lại nhiều lần vẫn an toàn |

Lệnh release (`cz bump`, `cz changelog`) xem [11 mục 5.3](./11-git-workflow.md#53-release).

## 4. Debug

- API chạy trên máy, nên debug bằng debugger của IDE như một chương trình Python thường (run configuration "Django (local)", mục 6). Không có cổng `debugpy` trong container.
- Debug Celery task: đặt `CELERY_TASK_ALWAYS_EAGER=True` tạm thời để task chạy ngay trong tiến trình api.
- Cách cấu hình theo từng IDE: xem mục 6.

## 5. Chạy test

- Test dùng database `test_fashion` do pytest-django tự tạo trên PostgreSQL cài trên máy, mỗi worker `pytest-xdist` một database riêng (không dùng SQLite, để giống production: `select_for_update`, `EXCLUDE`, `unaccent`).
- Celery chạy đồng bộ; API bên ngoài dùng Fake hoặc `respx`; thời gian cố định bằng `time-machine`.
- Test chạy trên máy bằng `make test`. `.env` đã trỏ mọi địa chỉ về `localhost` (mục 2.3), nên không cần ghi đè biến nào.

## 6. Cấu hình IDE dùng chung

Team dùng cả **VS Code** và **PyCharm**. Repo commit sẵn cấu hình chung để ai clone về cũng chạy và debug được ngay; cấu hình cá nhân không được commit (xem [11-git-workflow.md](./11-git-workflow.md) mục 8).

| IDE | File được commit | Nội dung |
|---|---|---|
| VS Code | `.vscode/launch.json` | "Django (local)": chạy `manage.py runserver` bằng interpreter `.venv`; "Pytest (local)": chạy test bằng interpreter `.venv` |
| VS Code | `.vscode/extensions.json` | Extension khuyến nghị: Python, Pylance, Python Debugger, Ruff, Mypy Type Checker, Docker, EditorConfig, Mermaid preview |
| PyCharm | `.run/*.run.xml` | Run configuration lưu dạng file dự án: "Pytest" (đã có), "Django server" (thêm ở ticket 15) |
| Cả hai | `.editorconfig` | Thụt lề 4 dấu cách cho Python, 2 cho YAML/JSON/TOML; LF; UTF-8; xoá khoảng trắng cuối dòng |

Interpreter của cả hai IDE là `backend/.venv`, tạo bằng `uv sync`. Trên Windows đường dẫn là `backend/.venv/Scripts/python.exe`, trên macOS là `backend/.venv/bin/python`.

### 6.1. VS Code

- Chọn interpreter `backend/.venv`.
- Debug: `make up` để bật worker, Redis, Mailpit, rồi chọn "Django (local)" và nhấn F5. Breakpoint đặt trong `backend/` sẽ dừng đúng chỗ.

### 6.2. PyCharm

- Interpreter: `backend/.venv` (Add Interpreter → Existing). Chạy và debug Django bằng run configuration "Django server". Không cần PyCharm Professional.
- Đánh dấu `backend/` là Sources Root để import `config`, `shared`, `modules` không bị báo lỗi. Đánh dấu `backend/tests` là Test Sources Root.

Các cấu hình dưới đây nằm trong `.idea/` nên không được commit; mỗi máy làm một lần sau khi clone:

- Django support (Settings → Languages & Frameworks → Django): bật Enable Django Support, Django project root là `backend`, Settings là `config/settings/local.py`, Manage script là `backend/manage.py`. Tick "Do not use Django test runner" vì test chạy bằng pytest-django. Sau đó dùng được Run manage.py Task (`Ctrl+Alt+R`), tool window Endpoints và gợi ý cho `settings.*`, model, tên URL.
- Database (tool window Database → + → Data Source → PostgreSQL): host `localhost`, cổng `PG_PORT`, database, user, mật khẩu lấy từ `DATABASE_URL` trong `.env` (mục 2.3). Mật khẩu chỉ lưu trong `.idea/` của máy.
- Ruff (Settings → Python → Tools → Ruff): bật Enable, tick Formatting và Sort imports. PyCharm dùng `ruff` trong `backend/.venv` và đọc cấu hình `[tool.ruff]` trong `pyproject.toml`.
- Plugin Makefile Language (Settings → Plugins → Marketplace) để chạy target trong `backend/Makefile` từ editor. Các plugin khác cần cho repo (Docker, .env, Markdown, Mermaid, TOML, YAML) có sẵn trong PyCharm.

## 7. `docker-compose.yml` (rút gọn)

```yaml
name: fashion   # tên project cố định; mặc định là tên thư mục (backend), dễ trùng container của project khác

x-container-env: &container-env
  # .env viết cho máy (mục 2.3); trong container, localhost là chính container
  DATABASE_HOST: host.docker.internal   # thay host của DATABASE_URL trong .env; user, mật khẩu, cổng giữ nguyên
  REDIS_URL: redis://redis:6379/0
  EMAIL_HOST: mailpit

x-base: &base
  image: fashion-backend   # một image chung, Compose không build lại cho từng service
  build: .
  env_file: .env
  environment: *container-env
  extra_hosts: ["host.docker.internal:host-gateway"]   # Docker Desktop đã có sẵn; Docker Engine trên Linux không được hỗ trợ (PostgreSQL chỉ nghe localhost)
  volumes: [".:/app"]   # Celery không tự reload: sửa code xong chạy make restart-worker

x-app: &app
  <<: *base
  depends_on:
    redis: {condition: service_started}
    migrate: {condition: service_completed_successfully}  # beat cần bảng django_celery_beat, relay cần bảng outbox

services:
  migrate:
    <<: *base
    command: sh -c "python manage.py migrate && python manage.py sync_beat_schedule"
    restart: "no"
  worker:
    <<: *app
    command: celery -A config worker -Q default,events,emails,integrations -l info  # local: 1 worker cho cả 4 queue (07 mục 3.1)
  beat:
    <<: *app
    command: celery -A config beat -l info   # scheduler lấy từ CELERY_BEAT_SCHEDULER của settings
  relay:
    <<: *app
    command: python manage.py run_outbox_relay
  redis:
    image: valkey/valkey:8.1.11   # Valkey 8 như ElastiCache, cùng bản với service của CI
    ports: ["${REDIS_PORT:-6380}:6379"]   # không tranh 6379 với Redis/Memurai của project khác trên máy
  mailpit:
    image: axllent/mailpit:v1.31.6
    ports: ["1025:1025", "8025:8025"]
```

Image ghim tới bản vá, chỉ chọn bản đã phát hành ít nhất 7 ngày (như cooldown của Dependabot). `Dockerfile` dựng một image cho `migrate`, `worker`, `beat`, `relay` từ `python:3.14.<vá>-slim`, `uv` chép từ `ghcr.io/astral-sh/uv`, cài bằng `uv sync --locked --no-build --no-dev` vào `/opt/venv` (ngoài `/app`, để bind mount `backend/` không đè `.venv` của máy lên venv của container), chạy bằng user `app` không phải root. Image chép tường minh `manage.py`, `config/`, `shared/`, `modules/` (không `COPY . .`) để chạy được khi không bind mount mà không lọt file nhạy cảm; `.dockerignore` giữ `.env`, `.venv` ngoài build context. Compose không có service `postgres` ([ADR 0015](../adr/0015-local-postgres-on-host.md)) và không có service `api`: API chạy trên máy bằng `make run` ([ADR 0017](../adr/0017-windows-native-dev-api-on-host.md)). `REDIS_PORT` đọc từ `.env`. Service `migrate` chạy một lần rồi thoát; `worker`, `beat`, `relay` chỉ khởi động khi nó thoát thành công, nên DB trống không làm `beat` hay `relay` lỗi liên tục. Migration lỗi thì `make up` dừng ở bước này, xem bằng `make logs s=migrate`. Service `relay` có từ ticket 10 của M0, cùng lúc với lệnh `run_outbox_relay`.
