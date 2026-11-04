# Lệnh hằng ngày (08 mục 3). Mỗi lệnh thêm cùng ticket tạo ra thứ nó gọi.
# Recipe chỉ gọi `uv run`, `docker compose` hoặc target khác qua `$(MAKE)`, không dùng cú pháp
# riêng của shell POSIX, để chạy được bằng GNU make trên Windows (ADR 0017).

# Python ở chế độ UTF-8: trên Windows, output chuyển hướng ra file hay pipe mặc định theo ANSI
# code page của máy (vd. cp1252) nên lint-imports dừng ở tên contract tiếng Việt.
export PYTHONUTF8 := 1

.PHONY: test lint fmt up down run restart-worker logs shell makemigrations migrate load-geo create-admin seed db-reset br-report openapi

# Cùng lệnh với job backend của CI: pytest-cov gom coverage từ các worker xdist, rồi cổng
# branch coverage từng module (12 mục 8)
test:
	uv run pytest -n auto --cov=apps --cov=common --cov-report=
	uv run python scripts/check_module_coverage.py

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy .
	uv run python scripts/gen_importlinter.py --check
	uv run lint-imports
	uv run python scripts/gen_openapi.py --check

fmt:
	uv run ruff format .
	uv run ruff check --fix .

# Service migrate chạy migrate và sync_beat_schedule trước khi worker, beat, relay khởi động
# (08 mục 7)
up:
	docker compose up -d --build

down:
	docker compose down

# API chạy trên máy, tự reload khi sửa code
run:
	uv run python manage.py runserver

# Celery và relay không tự reload: chạy sau khi sửa code
restart-worker:
	docker compose restart worker beat relay

# make logs s=worker
logs:
	docker compose logs -f $(s)

shell:
	uv run python manage.py shell

makemigrations:
	uv run python manage.py makemigrations

# Chạy trên máy; sync_beat_schedule ghi lịch job vào DB (07 mục 3.2)
migrate:
	uv run python manage.py migrate
	uv run python manage.py sync_beat_schedule

# Nạp tỉnh/thành, phường/xã sau migrate (08 mục 2.4 bước 4); chạy lại không trùng, không xoá mã cũ
load-geo:
	uv run python manage.py load_geo

# Tạo Tài khoản Admin (08 mục 2.4 bước 5); hỏi email nếu thiếu, mật khẩu nhập hai lần qua getpass
create-admin:
	uv run python manage.py create_staff --admin

# Tạo Tài khoản Admin, Staff mẫu với mật khẩu dev cố định (08 mục 3); chỉ chạy khi DEBUG bật và
# database ở localhost; chạy lại không tạo trùng
seed:
	uv run python manage.py seed_dev

# Xoá và tạo lại database fashion rồi chạy target migrate (08 mục 2.2); reset_db chỉ chạy với
# DEBUG bật và host localhost
db-reset:
	uv run python manage.py reset_db
	$(MAKE) migrate

# Liệt kê các mã BR-xxx trong docs/business/04-business-rules.md chưa có test gắn marker `br` (12 mục 3)
br-report:
	uv run python scripts/br_report.py

# Sinh lại openapi.yaml (spectacular --validate --fail-on-warn) sau khi đổi API; commit file này
# cùng PR. make lint và CI fail khi file đã commit lệch với code (12 mục 5)
openapi:
	uv run python scripts/gen_openapi.py
