# 08. Môi trường phát triển local (macOS, Windows và Linux)

> Trạng thái: **Đã chốt cho MVP** ([quy ước](../../README.md#trạng-thái-tài-liệu)).
> - **PostgreSQL cài trên máy**: macOS dùng Homebrew qua `scripts/setup/postgres.sh`; Windows dùng bộ cài EDB rồi `scripts/setup/postgres.ps1` ([ADR 0015](../adr/0015-local-postgres-on-host.md), [ADR 0017](../adr/0017-windows-native-dev-api-on-host.md)).
> - Linux (Docker Engine, PostgreSQL cài bằng apt) có hướng dẫn ở mục 2.1, 2.2 nhưng ngoài phạm vi hỗ trợ chính thức.
> - **Django API chạy trên máy** bằng `uv run`; worker, beat, relay, Redis, Mailpit chạy bằng **Docker Compose**.
> - Trên máy cần Docker, `uv` ≥ 0.13 (tự tải Python 3.14 theo `.python-version`), `git`, `make`. Windows không dùng WSL2.

## 1. Tổng quan

| Thành phần | Chạy ở đâu | Cổng |
|---|---|---|
| PostgreSQL (bản major mới nhất) | Cài trên máy: Homebrew (macOS), bộ cài EDB (Windows). Container gọi qua `host.docker.internal` | macOS: 5432, hoặc cổng trống kế tiếp nếu 5432 đang bận; Windows: cổng chọn lúc cài EDB (mặc định 5432). Ghi vào `PG_PORT` |
| Django API | Trên máy (`make run`), gọi các thành phần khác qua `localhost`; sửa code tự reload | 8000 |
| Celery worker, Celery Beat, Outbox relay | Docker, bind mount gốc repo, gọi Redis/Mailpit theo tên service; sửa code xong chạy `make restart-worker` | — |
| Redis (Valkey 8, cùng bản với ElastiCache) | Docker | 6380 trên máy (`REDIS_PORT`), 6379 trong mạng Compose |
| Mailpit | Docker | 1025 (SMTP), 8025 (giao diện xem mail) |
| Ảnh Sản phẩm | Ổ đĩa, thư mục `media/` | — |
| VNPay, MoMo | Fake Gateway trong Django | — |
| GHN | Fake, hoặc sandbox thật (gọi ra được từ local) | — |

## 2. Cài đặt lần đầu

### 2.1. Công cụ

#### macOS

`brew install uv`; Docker Desktop (hoặc OrbStack) cài riêng. PostgreSQL: mục 2.2.

#### Windows

Làm thẳng trên Windows, **không dùng WSL2** ([ADR 0017](../adr/0017-windows-native-dev-api-on-host.md)). `make`, `uv run`, `docker compose` chạy trong PowerShell 7 hoặc Git Bash; lệnh shell thuần (`bash scripts/...`) chạy trong Git Bash.

```powershell
winget install Git.Git astral-sh.uv ezwinports.make Docker.DockerDesktop
git config --global core.autocrlf false   # .gitattributes đã quy định LF/CRLF cho từng loại file
```

Clone repo vào thư mục bất kỳ trên ổ Windows, nên tránh đường dẫn có dấu cách. PostgreSQL: mục 2.2; IDE: mục 6.

| Lỗi hay gặp trên Windows | Cách xử lý |
|---|---|
| `make` báo không tìm thấy | Mở terminal mới sau khi cài để nhận `PATH` mới |
| Lỗi `/bin/sh^M: bad interpreter` trong container | File bị đổi sang CRLF; repo có `.gitattributes` ép LF, chạy `git add --renormalize .` |
| Cổng 6379 đã bị Redis hoặc Memurai của project khác giữ | Không sao: Redis của Compose mở ra máy ở `REDIS_PORT` (mặc định 6380) |

#### Linux

Ngoài phạm vi hỗ trợ chính thức ([ADR 0015](../adr/0015-local-postgres-on-host.md) chỉ chốt macOS và Windows). Áp dụng cho Ubuntu/Debian dùng Docker Engine (không phải Docker Desktop); đã xác minh ngày 2026-11-03 trên Ubuntu 26.04.1 LTS, Docker Engine 29.9.2, PostgreSQL 18 cài bằng apt.

- `git --version`, `make --version`, `docker --version`, `docker compose version`, `uv --version` đều phải in số phiên bản; báo `command not found` thì cài công cụ đó trước.
- `docker ps` không được báo `permission denied`; nếu có, chạy `sudo usermod -aG docker $USER`, đăng xuất rồi đăng nhập lại.
- PostgreSQL: mục 2.2.

### 2.2. Database

PostgreSQL cài trên máy, không chạy trong Docker. Cài cách nào cũng phải ra cùng kết quả:

- Role `fashion` (mật khẩu `fashion`, `LOGIN CREATEDB`) sở hữu database `fashion`. `CREATEDB` để pytest-django tự tạo/xoá database test (`test_fashion`, `test_fashion_gw0`, `test_fashion_gw1`… khi chạy song song).
- `unaccent`, `pg_trgm`, `btree_gist` **có sẵn để cài** (có trong `pg_available_extensions`). **Migration** tạo extension, giống CI và RDS; cả ba là trusted extension (từ PostgreSQL 13) nên chủ database tự tạo được, không cần superuser.
- `DATABASE_URL` và `PG_PORT` chép vào `.env` (mục 2.3).

#### macOS

Từ gốc repo chạy `bash scripts/setup/postgres.sh` (chạy lại nhiều lần vẫn an toàn). Script:

1. Kiểm tra `git`, `make`, `docker`, `uv` (chỉ báo thiếu, không tự cài).
2. Dùng hoặc cài bản major mới nhất `postgresql@<major>` trên Homebrew (cũng chạy được trên Ubuntu/Debian bằng apt PGDG, ngoài phạm vi hỗ trợ).
3. Không đụng cluster khác; 5432 bận thì cluster mới chạy ở cổng trống kế tiếp (5433…).
4. Tạo/cập nhật role và database `fashion`, kiểm tra extension.
5. Thử đăng nhập bằng `fashion` qua `localhost`, rồi in `DATABASE_URL` và `PG_PORT`.

#### Windows

1. **Cài PostgreSQL một lần** (Administrator, bản major mới nhất): `winget install PostgreSQL.PostgreSQL.18`, hoặc bộ cài EDB từ postgresql.org.
   - Mật khẩu superuser `postgres` tự đặt, tự giữ, không ghi vào repo; cổng để mặc định 5432 nếu trống.
   - Kèm pgAdmin 4; `unaccent`, `pg_trgm`, `btree_gist` có sẵn. Chạy thành service `postgresql-x64-<major>`, tự bật cùng máy.
2. **Tạo role và database**: từ gốc repo chạy `pwsh scripts/setup/postgres.ps1` (chạy lại vẫn an toàn). Script hỏi mật khẩu `postgres` (nhập ẩn, không lưu), kiểm tra `git`, `make`, `docker`, `uv`, tìm service `postgresql-x64-*` major cao nhất và đọc cổng (chưa cài thì in lệnh winget ở bước 1 rồi dừng), tạo/cập nhật role và database `fashion`, kiểm tra extension, thử đăng nhập bằng `fashion` rồi in `DATABASE_URL` và `PG_PORT`.

   Chưa có script thì làm tay trong Query Tool của pgAdmin, đăng nhập bằng `postgres`:
   ```sql
   CREATE ROLE fashion LOGIN CREATEDB PASSWORD 'fashion';
   CREATE DATABASE fashion OWNER fashion;
   ```

#### Linux

Công cụ: mục 2.1. Làm đúng thứ tự, mỗi máy một lần, trong cùng một terminal (bước 1 đặt `PGMAJOR` cho các bước sau).

**Bước 1. Kiểm tra PostgreSQL đã cài và đang chạy.** Chạy `pg_lsclusters`. Đúng: một dòng `Status` là `online`, ví dụ `18  main  5432  online`. Không có lệnh nghĩa là chưa cài: cài bản major mới nhất từ apt PGDG hoặc chạy `bash scripts/setup/postgres.sh` từ gốc repo (mục macOS bước 2), rồi làm lại. Ghi lại **cổng** để kiểm `.env` (mục 2.3) và đặt **major**: `PGMAJOR=18` (thay bằng số ở cột Ver).

**Bước 2. Tạo role và database `fashion`.** Chạy lại vẫn an toàn; bỏ qua nếu đã chạy `scripts/setup/postgres.sh`.

```bash
sudo -u postgres psql -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'fashion') THEN CREATE ROLE fashion LOGIN CREATEDB PASSWORD 'fashion'; END IF; END \$\$;"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'fashion'" | grep -q 1 || sudo -u postgres createdb -O fashion fashion
sudo -u postgres psql -d fashion -tc "SELECT name FROM pg_available_extensions WHERE name IN ('unaccent', 'pg_trgm', 'btree_gist')"   # phải in đủ ba extension
psql "postgres://fashion:fashion@localhost:5432/fashion" -c "SELECT current_user"   # thử đăng nhập, đúng thì in fashion
```

**Bước 3. Cho container trong Docker gọi được PostgreSQL.** Trên Linux `host.docker.internal` là IP của `docker0`, còn PostgreSQL mặc định chỉ nghe `127.0.0.1`. Bỏ bước này thì `make up` (mục 2.4) dừng ở `migrate` với `couldn't get a connection after 3.00 sec`.

```bash
ip -4 addr show docker0 | grep inet   # 3.1. IP của docker0, thường là 172.17.0.1
# 3.2. Nghe thêm ở IP đó (thay IP nếu khác)
sudo sed -i "s/^#\?listen_addresses.*/listen_addresses = 'localhost,172.17.0.1'/" /etc/postgresql/$PGMAJOR/main/postgresql.conf
# 3.3. Cho mạng Docker (172.16.0.0/12) đăng nhập role fashion bằng mật khẩu
echo "host  fashion  fashion  172.16.0.0/12  scram-sha-256" | sudo tee -a /etc/postgresql/$PGMAJOR/main/pg_hba.conf
sudo systemctl restart postgresql   # 3.4. Nhận cấu hình mới
ss -ltn | grep 5432                 # 3.5. Kiểm tra
```

3.5 đúng khi in **hai** dòng `127.0.0.1:5432` và `172.17.0.1:5432`; chỉ một dòng thì xem `sudo tail -20 /var/log/postgresql/postgresql-$PGMAJOR-main.log`. Chạy 3.3 hai lần chỉ thêm dòng trùng, vô hại.

**Bước 4. Cho PostgreSQL khởi động sau Docker.** `docker0` chỉ có sau khi Docker chạy. Nếu lúc bật máy PostgreSQL lên trước, nó không bind được `172.17.0.1` (log: `could not bind IPv4 address "172.17.0.1": Cannot assign requested address`) và chỉ nghe `127.0.0.1`, không báo lỗi gì khác; `make up` dừng ở `migrate` dù bước 3 đúng. Thêm drop-in systemd:

```bash
sudo mkdir -p /etc/systemd/system/postgresql@$PGMAJOR-main.service.d
printf '[Unit]\nAfter=docker.service\nWants=docker.service\n' | sudo tee /etc/systemd/system/postgresql@$PGMAJOR-main.service.d/after-docker.conf
sudo systemctl daemon-reload
sudo systemctl restart postgresql
```

Kiểm lại bằng 3.5; lần bật máy sau vẫn phải thấy hai dòng. Nếu `sudo ufw status` in `Status: active` thì chạy thêm `sudo ufw allow from 172.16.0.0/12 to any port 5432`. Tiếp theo: mục 2.3, rồi 2.4.

**Lỗi thường gặp trên Linux**

| Dấu hiệu | Xem bằng | Nguyên nhân và cách sửa |
|---|---|---|
| `service "migrate" didn't complete successfully: exit 1` | `docker compose logs migrate \| tail -5` | Đọc dòng lỗi cuối, so với các dòng dưới |
| `couldn't get a connection after 3.00 sec` | `ss -ltn \| grep 5432` | PostgreSQL chưa nghe ở `172.17.0.1`: làm lại bước 3; đã nghe rồi thì kiểm `ufw` |
| `couldn't get a connection after 3.00 sec` ngay sau khi bật máy, dù bước 3 đã làm và `listen_addresses` đúng | `sudo grep 172.17.0.1 /var/log/postgresql/postgresql-<major>-main.log` | Log có `could not bind IPv4 address "172.17.0.1"`: PostgreSQL khởi động trước Docker. Sửa ngay bằng `sudo systemctl restart postgresql`; làm bước 4 để không lặp lại |
| `no pg_hba.conf entry for host "172.…"` | `sudo grep fashion /etc/postgresql/<major>/main/pg_hba.conf` | Thiếu dòng ở bước 3.3 |
| `password authentication failed for user "fashion"` | — | Mật khẩu trong `DATABASE_URL` của `.env` khác mật khẩu role; đặt lại bằng `sudo -u postgres psql -c "ALTER ROLE fashion PASSWORD 'fashion'"` |
| `port is already allocated` (6380, 1025, 8025) | `ss -ltn \| grep <cổng>` | Cổng đang bị chương trình khác giữ; tắt chương trình đó hoặc đổi `REDIS_PORT` trong `.env` |
| `permission denied ... docker.sock` | `docker ps` | User chưa thuộc nhóm `docker`: xem mục 2.1 → Linux |

#### Khác biệt với CI/production, kết nối và reset

- RDS và CI (`postgres:18`) có thể chạy major cũ hơn local: không dùng tính năng chỉ có ở bản mới; CI sẽ bắt.
- Windows chạy bản build cho Windows, CI và production chạy Linux: khác biệt collation/locale có thể chỉ lộ ra trên CI.
- Tiến trình trên máy (API, IDE, `psql`, pytest) gọi `localhost:<PG_PORT>`.
- Container Compose (worker, beat, relay, migrate) gọi `host.docker.internal:<PG_PORT>`, vì Compose đặt `DATABASE_HOST` thay host của `DATABASE_URL` (mục 7):
  - Windows (Docker Desktop, PostgreSQL 18 EDB): xác minh 2026-10-29, không cần sửa cấu hình. PostgreSQL thấy client là `127.0.0.1`, đã được dòng `host all all 127.0.0.1/32` mặc định của EDB cho phép.
  - macOS **[Cần xác minh]**: nếu container không kết nối được, cách sửa (`listen_addresses`, `pg_hba.conf`) sẽ ghi ở đây (ticket `.scratch/backend-bootstrap/issues/13-local-postgres-installer-macos/spec.md`).
  - Linux (Docker Engine, PostgreSQL 18 apt): xác minh 2026-11-03 trên Ubuntu 26.04.1 LTS; bắt buộc làm bước 3 ở trên.
- Dữ liệu nằm trên máy nên `make down` không mất dữ liệu. Chỉ chạy `make db-reset` (drop và tạo lại database `fashion`, giữ role, rồi migrate) khi migration bị rối do đổi nhánh có migration xung đột, hoặc muốn seed lại từ đầu.

### 2.3. Biến môi trường

Từ gốc repo: `cp .env.example .env`.

- Mỗi biến được khai báo trong `config/env.py` ở mốc đầu tiên dùng tới nó ([roadmap](../../.scratch/mvp-roadmap/map.md)); `.env.example` chỉ chứa biến đã khai báo.
- Thiếu biến bắt buộc thì Django dừng ngay lúc khởi động và báo tên biến.
- `DATABASE_URL` thiếu user, thiếu host, tên database rỗng hoặc chứa `/`, `@`, `:` cũng dừng như vậy; thông báo nêu phần sai, không in giá trị URL. Password có `/`, `@`, `:`, `?`, `#` phải mã hoá phần trăm (`%2F`, `%40`…).

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
JWT_SIGNING_KEYS=                                         # kid|private-key-base64|public-key-base64, nhiều khoá cách nhau bằng dấu phẩy; khoá đầu (phải có private) ký token mới, mọi public key dùng verify; key Ed25519 tạo riêng cho máy, không commit. `check --deploy` từ chối keyring rỗng (common.E002)
JWT_ISSUER=fashion-store
JWT_AUDIENCE_BACKOFFICE=backoffice
JWT_ACCESS_TTL_SECONDS=600                                # số dương
JWT_BACKOFFICE_REFRESH_TTL_SECONDS=43200                  # số dương
JWT_LEEWAY_SECONDS=30                                     # không âm
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

- `.env` viết cho tiến trình trên máy (API, pytest, IDE): mọi địa chỉ là `localhost`. Container ghi đè `REDIS_URL`, `EMAIL_HOST` và đặt `DATABASE_HOST` (chỉ thay host, giữ user, mật khẩu, cổng, tên DB) trong `environment:` (mục 7), nên không sửa `.env` cho container và `docker-compose.yml` không chứa mật khẩu.
- `DJANGO_SETTINGS_MODULE` trong `.env` chỉ có tác dụng trong Compose (nạp vào env của container); trên máy, `.env` được đọc sau khi settings đã chọn. Trên máy thì `export` biến này hoặc dùng mặc định `config.settings.local` của `manage.py`. `wsgi.py` và Celery không có mặc định: process deploy thiếu biến thì dừng ngay.
- `BFF_SHARED_SECRET` phải trùng giá trị ở Next.js local. Next.js gửi nó trong `X-BFF-Secret` kèm `X-Client-IP`; Django chỉ tin `X-Client-IP` khi secret đúng và IP là IPv4/IPv6 hợp lệ ([ADR 0009](../adr/0009-nextjs-bff-django-private.md)). Nhận 1 hoặc 2 secret cách nhau dấu phẩy (2 khi đang xoay, [05 mục 5](./05-auth-security.md)); rỗng hoặc hơn 2 thì Django dừng lúc khởi động. Gọi thẳng `localhost:8000` (Swagger UI, `curl`) vẫn chạy, chỉ là throttle tính theo IP máy gọi.
- `STOREFRONT_ORIGIN` chỉ là origin tin cậy, không kèm path/query/userinfo; payment return path do backend cố định.

Từ M1, sinh khoá JWT và khoá RefreshReplay (độc lập JWT) cho local, chạy từ gốc repo, mọi shell đều được (`cryptography` có từ M1):

```bash
uv run python -c "from pathlib import Path; from cryptography.hazmat.primitives import serialization as s; from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; Path('.secrets').mkdir(exist_ok=True); Path('.secrets/jwt_ed25519.pem').open('xb').write(Ed25519PrivateKey.generate().private_bytes(s.Encoding.PEM, s.PrivateFormat.PKCS8, s.NoEncryption()))"
uv run python -c "from pathlib import Path; import secrets; Path('.secrets').mkdir(exist_ok=True); Path('.secrets/refresh_replay.key').open('xb').write(secrets.token_bytes(32))"
```

- Tạo một lần, không commit; hai lệnh từ chối ghi đè key đã có, không tạo lại mỗi lần khởi động.
- Key RefreshReplay có ID để xoay; các API replica phải cùng đọc được key còn hiệu lực trong cửa sổ replay.

### 2.4. Chạy

Lần đầu, sau mục 2.2 và 2.3, chạy từ gốc repo. Cột "Có từ" như mục 3: chưa tới mốc thì chưa dùng được.

| Bước | Lệnh | Làm gì | Có từ |
|---|---|---|---|
| 1 | `uv sync` | Tạo `.venv` với Python 3.14 và dependency (cả nhóm dev) | M0 (ticket 07) |
| 2 | `uv run pre-commit install` | Cài hook `pre-commit` và `commit-msg` vào `.git/hooks`, một lần cho mỗi bản clone ([11](./11-git-workflow.md) mục 3.4) | M0 (ticket 07) |
| 3 | `make up` | `docker compose up -d --build`; service `migrate` chạy migration và `sync_beat_schedule` trước khi worker, beat, relay khởi động (mục 7) | M0 (ticket 15) |
| 4 | `make load-geo` | Xem mục 3 | M0 (ticket 17) |
| 5 | `make create-admin` | Hỏi email, nhập mật khẩu hai lần (không có cờ `--password`), tối thiểu 8 ký tự theo [05](./05-auth-security.md) mục 3 | M0 (ticket 12) |
| 6 | `make seed` | Xem mục 3 | M1 |
| 7 | `make run` | Chạy API trên máy, tự reload khi sửa code | M0 (ticket 15) |

`make migrate` chỉ cần khi có migration mới mà không muốn khởi động lại container. Kiểm tra sau lần chạy đầu:

| Lệnh | Kết quả đúng |
|---|---|
| `uv run python manage.py check --database default` (sau bước 1) | `System check identified no issues`; lỗi kết nối thì xem lại mục 2.2 và `DATABASE_URL` ở mục 2.3 |
| `docker compose ps` (sau bước 3) | `migrate` là `exited (0)`, `worker`, `beat`, `relay`, `redis`, `mailpit` là `running` |
| `curl -s http://localhost:8000/healthz` / `readyz` (sau bước 7) | API sống / kết nối được PostgreSQL (`readyz` không kiểm tra Redis) |

| Địa chỉ | Dùng để |
|---|---|
| http://localhost:8000/api/docs/ | Swagger UI, gọi thử API |
| http://localhost:8025 | Mailpit, xem email đã gửi |
| http://localhost:8000/dev/fake-gateway/ | Fake Gateway (từ M3) |

Không có Django Admin ([ADR 0004](../adr/0004-custom-nextjs-admin.md)). Xem dữ liệu bằng `psql`, công cụ database của IDE hoặc `make shell`.

## 3. Lệnh hằng ngày (`Makefile`)

- Mỗi target được thêm cùng ticket tạo ra lệnh nó gọi; cột "Có từ" cho biết lệnh nào đã dùng được.
- `Makefile` (và hook `lint-imports` của pre-commit) đặt `PYTHONUTF8=1`, để trên Windows lệnh Python vẫn ghi UTF-8 khi output chuyển ra file hay pipe.

| Lệnh | Làm gì | Có từ |
|---|---|---|
| `make up` / `make down` | Bật / tắt các container; `make up` chạy service `migrate` trước (mục 7) | M0 (ticket 15) |
| `make run` | Chạy API trên máy (`uv run python manage.py runserver`) | M0 (ticket 15) |
| `make restart-worker` | Khởi động lại worker, beat, relay sau khi sửa code (Celery không tự reload) | M0 (ticket 15) |
| `make logs s=worker` | Xem log của một service | M0 (ticket 15) |
| `make shell` | `manage.py shell` chạy trên máy | M0 (ticket 15) |
| `make makemigrations` / `make migrate` | Tạo / chạy migration; `make migrate` chạy thêm `manage.py sync_beat_schedule` để ghi lịch job vào DB ([07](./07-async-events-jobs.md) mục 3.2) | M0 (ticket 15) |
| `make db-reset` | Xoá và tạo lại database `fashion` (`manage.py reset_db`, chỉ chạy khi `DEBUG` bật, host là `localhost` và server nghe ở loopback) rồi `make migrate` (mục 2.2) | M0 (ticket 15) |
| `make test` | `pytest -n auto --cov=apps --cov=common --cov=infrastructure --cov-report=` rồi `python scripts/check_module_coverage.py`, cùng lệnh với job `backend` của CI ([12](./12-testing-strategy.md) mục 8) | M0 (ticket 07; cổng coverage từ ticket 01) |
| `make lint` | `ruff check`, `ruff format --check`, `mypy`, `scripts/gen_importlinter.py --check` (contract `forbidden` trong `pyproject.toml` không lệch với generator), `lint-imports`, `scripts/gen_openapi.py --check` (`openapi.yaml` không lệch với code, operation đủ chú thích theo [04](./04-api-contract.md) mục 5.6); cùng thứ tự với bước Lint của job `backend` trong CI | M0 (ticket 07; `gen_importlinter.py --check` từ ticket 04; `gen_openapi.py --check` từ ticket 03) |
| `make fmt` | `ruff format` + `ruff check --fix` | M0 (ticket 07) |
| `make load-geo` | Nạp 34 tỉnh/thành và phường/xã | M0 (ticket 17) |
| `make create-admin` | Tạo Tài khoản Admin (`manage.py create_staff --admin`; cách nhập ở mục 2.4) | M0 (ticket 12) |
| `make openapi` | Sinh lại `openapi.yaml` (`scripts/gen_openapi.py`, `spectacular --validate --fail-on-warn`); chạy sau khi đổi API rồi commit file cùng PR ([12](./12-testing-strategy.md) mục 5) | M0 (ticket 03) |
| `make br-report` | Liệt kê các mã `BR-xxx` trong `docs/business/04-business-rules.md` chưa có test gắn marker `br` ([12](./12-testing-strategy.md) mục 3) | M0 (ticket 02) |
| `make seed` | Tạo Kho, danh mục, Sản phẩm mẫu, Voucher mẫu | M1 (Voucher mẫu từ M2) |
| `make tunnel` | Mở Cloudflare Tunnel để nghiệm thu với sandbox ([06](./06-integrations.md) mục 8) | M7 |

### 3.1. Lệnh không qua `make`

Chạy từ gốc repo, dùng được từ M0 (ticket 07). `pre-commit install`, `healthz`/`readyz`: mục 2.4; script PostgreSQL: mục 2.2.

| Lệnh | Làm gì |
|---|---|
| `uv sync` | Cập nhật `.venv` theo `uv.lock`, ví dụ sau khi `git pull` có đổi dependency |
| `uv sync --locked` | Như CI: báo lỗi nếu `uv.lock` lệch `pyproject.toml` |
| `uv run pytest <file>` / `uv run pytest <file>::<tên_test>` | Chạy một file hoặc một test; thêm `-x` để dừng ở test lỗi đầu tiên |
| `uv run python manage.py check` | System check của Django và dự án (`common/checks.py`); thêm `--deploy --settings=config.settings.production` để kiểm cấu hình bảo mật production (giá trị local sẽ có cảnh báo: secret ngắn, `ALLOWED_HOSTS` rỗng) |
| `uv run python manage.py <lệnh>` | `showmigrations`, `sqlmigrate`, `dbshell`… |
| `uv run pip-audit --strict` | Quét lỗ hổng dependency như job `backend` của CI; gọi mạng nên không gộp vào `make lint` |
| `uv run pre-commit run --all-files` | Chạy mọi hook trên toàn repo, ví dụ sau khi đổi `.pre-commit-config.yaml` |

Lệnh release (`cz bump`, `cz changelog`) xem [11 mục 5.3](./11-git-workflow.md#53-release).

## 4. Debug

- API chạy trên máy: debug bằng debugger của IDE như chương trình Python thường (mục 6). Không có cổng `debugpy` trong container.
- Debug Celery task: tạm đặt `CELERY_TASK_ALWAYS_EAGER=True` để task chạy ngay trong tiến trình api.

## 5. Chạy test

- Database `test_fashion` do pytest-django tạo trên PostgreSQL của máy, mỗi worker `pytest-xdist` một database. Không dùng SQLite, để giống production (`select_for_update`, `EXCLUDE`, `unaccent`).
- Celery chạy đồng bộ; API bên ngoài dùng Fake hoặc `respx`; cố định thời gian bằng `time-machine`.
- Chạy trên máy bằng `make test`, không cần ghi đè biến nào (`.env` đã trỏ về `localhost`).
- `make test` đo branch coverage (`[tool.coverage.run] branch = true`) rồi chạy cổng riêng từng module: dưới 80% ở `services/` + `handlers.py` của một module, hoặc ở nhóm hạ tầng `common`, thì lỗi ([12](./12-testing-strategy.md) mục 8). `uv run pytest <file>` không đo coverage, không qua cổng.

## 6. Cấu hình IDE dùng chung

Team dùng **VS Code** và **PyCharm**. Repo commit cấu hình chung để clone về là chạy và debug được; cấu hình cá nhân không commit ([11](./11-git-workflow.md) mục 8).

| IDE | File được commit | Nội dung |
|---|---|---|
| VS Code | `.vscode/launch.json` | "Django (local)": chạy `manage.py runserver` bằng interpreter `.venv`; "Pytest (local)": chạy test bằng interpreter `.venv` |
| VS Code | `.vscode/extensions.json` | Extension khuyến nghị: Python, Pylance, Python Debugger, Ruff, Mypy Type Checker, Docker, EditorConfig, Mermaid preview |
| PyCharm | `.run/*.run.xml` | Run configuration lưu dạng file dự án: "Pytest" (đã có), "Django server" (thêm ở ticket 15) |
| VS Code | `pyrightconfig.json` (gốc repo) | Pylance dùng `.venv` và coi gốc repo là gốc import (`config`, `common`, `infrastructure`, `apps`), không cần chọn interpreter tay |
| Cả hai | `.editorconfig` | Thụt lề 4 dấu cách cho Python, 2 cho YAML/JSON/TOML; LF; UTF-8; xoá khoảng trắng cuối dòng |

Interpreter của cả hai IDE là `.venv` (tạo bằng `uv sync`; Windows: `.venv/Scripts/python.exe`, macOS: `.venv/bin/python`). Chỉ chạy `uv` ở gốc repo, không ở thư mục con, để không sinh `.venv` thứ hai khiến Pylance chọn nhầm (`reportMissingImports` cho mọi thư viện).

### 6.1. VS Code

- `pyrightconfig.json` ở gốc repo đã trỏ Pylance tới `.venv`. Còn báo `reportMissingImports` thì chạy *Python: Select Interpreter* chọn `.venv`, rồi *Python: Restart Language Server*.
- Debug: `make up` để bật worker, Redis, Mailpit, rồi chọn "Django (local)" và nhấn F5. Breakpoint đặt trong code sẽ dừng đúng chỗ.

### 6.2. PyCharm

- Interpreter: `.venv` (Add Interpreter → Existing). Chạy/debug Django bằng "Django server". Không cần PyCharm Professional.
- Gốc repo là Sources Root (để import `config`, `common`, `infrastructure`, `apps`), `tests` là Test Sources Root.

Cấu hình sau nằm trong `.idea/` nên không commit; mỗi máy làm một lần:

- Django support (Settings → Languages & Frameworks → Django): Enable, project root là gốc repo, Settings `config/settings/local.py`, Manage script `manage.py`; tick "Do not use Django test runner" (test dùng pytest-django). Có thêm Run manage.py Task (`Ctrl+Alt+R`), Endpoints, gợi ý `settings.*`, model, tên URL.
- Database (Database → + → Data Source → PostgreSQL): host `localhost`, cổng `PG_PORT`, còn lại lấy từ `DATABASE_URL` (mục 2.3). Mật khẩu chỉ lưu trong `.idea/`.
- Ruff (Settings → Python → Tools → Ruff): Enable, tick Formatting và Sort imports; dùng `ruff` của `.venv` và `[tool.ruff]` trong `pyproject.toml`.
- Plugin Makefile Language (Marketplace) để chạy target của `Makefile`; plugin khác cần (Docker, .env, Markdown, Mermaid, TOML, YAML) có sẵn.

## 7. `docker-compose.yml` (rút gọn)

```yaml
name: fashion   # tên project cố định; mặc định là tên thư mục repo, dễ trùng container của project khác

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

- Image ghim tới bản vá, chỉ chọn bản đã phát hành ít nhất 7 ngày (như cooldown của Dependabot).
- `Dockerfile` dựng một image cho `migrate`, `worker`, `beat`, `relay`: từ `python:3.14.<vá>-slim`, `uv` chép từ `ghcr.io/astral-sh/uv`, `uv sync --locked --no-build --no-dev` vào `/opt/venv` (ngoài `/app`, để bind mount gốc repo không đè `.venv` của máy lên venv container), chạy bằng user `app` không phải root.
- Image chép tường minh `manage.py`, `config/`, `common/`, `infrastructure/`, `apps/` (không `COPY . .`) để chạy được khi không bind mount mà không lọt file nhạy cảm; `.dockerignore` giữ `.env`, `.venv` ngoài build context.
- Không có service `postgres` ([ADR 0015](../adr/0015-local-postgres-on-host.md)) hay `api` (API chạy bằng `make run`, [ADR 0017](../adr/0017-windows-native-dev-api-on-host.md)). `REDIS_PORT` đọc từ `.env`.
- `migrate` chạy một lần rồi thoát; `worker`, `beat`, `relay` chỉ khởi động khi nó thoát thành công, nên DB trống không làm `beat`/`relay` lỗi liên tục. Migration lỗi thì `make up` dừng ở đây; xem bằng `make logs s=migrate`.
- Service `relay` có từ ticket 10 của M0, cùng lúc với lệnh `run_outbox_relay`.
