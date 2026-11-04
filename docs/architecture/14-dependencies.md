# 14. Package dùng và không dùng

> Trạng thái: **Đã chốt cho MVP** ([quy ước](../../README.md#trạng-thái-tài-liệu)).

File này ghi **vì sao** chọn hoặc loại từng package. Phiên bản chính xác nằm ở `pyproject.toml` và `uv.lock`, là nguồn chuẩn duy nhất; tài liệu không chép số phiên bản để khỏi lệch. Package của nghiệp vụ chỉ thêm vào `pyproject.toml` ở mốc thực sự dùng tới.

## 1. Nền tảng

| Hạng mục | Lựa chọn | Ghi chú |
|---|---|---|
| Ngôn ngữ | Python 3.14 | `.python-version` |
| Framework | Django 5.2 LTS | Hỗ trợ tới 04/2028; nâng lên 6.2 LTS khoảng Q3/2027 |
| Database | PostgreSQL 18, extension `unaccent`, `pg_trgm`, `btree_gist` | RDS và CI dùng 18; local dùng bản major mới nhất ([ADR 0015](../adr/0015-local-postgres-on-host.md)) |
| Cache, broker | Redis, chạy bằng **Valkey 8** ở local và ElastiCache for Valkey trên AWS ([09](./09-deployment-aws-target.md)) | Tài liệu gọi chung là "Redis" vì đó là tên giao thức và thư viện (`redis-py`, broker `redis://`); Valkey tương thích giao thức nên không phải sửa code |
| Quản lý package | uv | `uv sync --locked --no-build` |

## 2. Runtime

| Package | Dùng để | Vì sao chọn |
|---|---|---|
| `django` | Framework | Bản LTS, cả hệ sinh thái đều đã tương thích |
| `djangorestframework` | REST API | Phổ biến nhất, team đã quen |
| `drf-spectacular` | Sinh OpenAPI 3 và Swagger UI | Chuẩn de facto cho DRF; dev đọc schema qua Swagger UI (chưa sinh TS client, [12](./12-testing-strategy.md) mục 5) |
| `django-filter` | Lọc danh sách (size, màu, giá, trạng thái) | Tích hợp sẵn với DRF |
| `psycopg[binary,pool]` | Driver PostgreSQL | psycopg 3, wheel binary và connection pool; khớp `uv sync --locked --no-build`. Dùng connection pool có sẵn của Django 5.2 (`OPTIONS["pool"]`, `CONN_MAX_AGE = 0`) |
| `redis` | Client Redis | Cache, throttling, Celery |
| `celery` | Worker chạy job | Có retry, định tuyến queue, hệ sinh thái lớn |
| `django-celery-beat` | Lịch job lưu trong DB (`DatabaseScheduler`) | Beat trên ECS không cần ổ đĩa để ghi file lịch. Lịch vẫn khai trong code (`beat_schedule`) và đồng bộ vào DB khi beat khởi động, nên muốn đổi lịch thì sửa code |
| `pydantic` | Schema sự kiện, DTO của `contracts.py` | Có type, validate, sinh JSON Schema (chuẩn bị cho Schema Registry) |
| `pydantic-settings` | Đọc biến môi trường có kiểu (`config/env.py`) | Sai cấu hình thì báo lỗi ngay khi khởi động |
| `PyJWT[crypto]` | Ký và kiểm tra JWT (Ed25519) | Thư viện chuẩn; phần mật mã không tự viết ([ADR 0002](../adr/0002-auth-nextauth-session-django-jwt.md)) |
| `cryptography` | Mã hoá response refresh trong RefreshReplay (AESGCM, 10 giây) | Dependency trực tiếp; dùng thư viện, không tự viết crypto ([05](./05-auth-security.md) mục 2.1) |
| `google-auth` | Xác minh `id_token` của Google (`infrastructure/google/`) | Thư viện chính thức của Google |
| `argon2-cffi` | Hash mật khẩu Argon2 | Thuật toán được OWASP khuyến nghị |
| `django-fsm-2` | Máy trạng thái Đơn hàng | `django-fsm` gốc đã chuyển sang viewflow; bản này giữ API cũ, do django-commons duy trì |
| `django-pghistory` | Lịch sử thay đổi (Đơn hàng, Thanh toán, Tồn kho, cấu hình vận hành). Chỉ theo dõi danh sách field tường minh, không chụp raw payload hay PII ([03](./03-data-model.md) mục 10.1) | Dùng trigger PostgreSQL nên bắt được cả `bulk_update` |
| `httpx` | Gọi API VNPay, MoMo, GHN (`infrastructure/`) | Timeout và retry rõ ràng; test bằng `respx` |
| `Pillow` | Xử lý ảnh Sản phẩm | Bắt buộc cho `ImageField` |
| `phonenumbers` | Parse, validate số Việt Nam và chuẩn hoá E.164 (`common/values/phones.py`) | Dùng chung cho lưu, tra cứu, giới hạn Voucher và xác định đối tượng ẩn danh |
| `django-storages[s3]` + `boto3` | Lưu ảnh trên S3 (chỉ ở AWS) | Ở local lưu ra ổ đĩa (`FileSystemStorage`) |
| `vietnam-provinces` | Dữ liệu 34 tỉnh/thành và phường/xã sau 07/2025 (`apps/geo`) | Đã cập nhật theo cấu trúc 2 cấp |
| `structlog` + `django-structlog` | Log JSON có `request_id` | Dễ tìm kiếm log trên CloudWatch |
| `sentry-sdk[django,celery]` | Theo dõi lỗi và hiệu năng | Chuẩn |
| `gunicorn` | Server production (WSGI, worker `gthread`) | Code toàn đồng bộ (DRF, ORM), chạy ASGI chỉ thêm chi phí `sync_to_async`. Chỉ chuyển sang ASGI khi thực sự cần async (ví dụ SSE) |

## 3. Dev và test

Khai trong `[dependency-groups] dev` của `pyproject.toml`.

| Package | Dùng để |
|---|---|
| `ruff` | Lint và format (thay cho flake8, isort, black) |
| `mypy` + `django-stubs` + `djangorestframework-stubs` | Kiểm tra kiểu, có plugin hiểu Django ORM. Không dùng extra `compatible-mypy` của `djangorestframework-stubs` vì extra này giới hạn phiên bản mypy |
| `import-linter` | Kiểm tra ranh giới giữa các module (bắt buộc trong CI, [02](./02-backend-structure.md) mục 6) |
| `pytest` + `pytest-django` | Chạy test |
| `pytest-xdist` | Chạy test song song |
| `factory-boy` | Tạo dữ liệu test |
| `coverage`, `pytest-cov` | Đo độ phủ, kể cả khi chạy song song |
| `respx` | Giả lập API bên ngoài khi test `httpx` |
| `time-machine` | Cố định thời gian khi test (Giữ hàng 15 phút, Hoàn tất sau 7 ngày) |
| `django-zeal` | Phát hiện lỗi N+1 query khi chạy test |
| `django-test-migrations` | Test data migration có `RunPython` ([12](./12-testing-strategy.md) mục 6) |
| `pip-audit` | Kiểm tra lỗ hổng đã công bố trong dependency (chạy trong CI) |
| `pre-commit` | Chạy ruff, mypy, import-linter và các hook `pre-commit-hooks` trước khi commit |
| `celery-types` | Type stub cho Celery để mypy và IDE kiểm được `shared_task`, `app.send_task` |
| `commitizen` | Kiểm tra commit message theo Conventional Commits, gắn tag phiên bản, sinh CHANGELOG ([11](./11-git-workflow.md)) |

## 4. Không dùng

| Package | Lý do |
|---|---|
| `requirements/*.txt` | Một nguồn khai báo `pyproject.toml` + `uv.lock` có hash, thay cho nhiều file requirements |
| `django-environ` | `pydantic-settings` có kiểu và báo lỗi cấu hình khi khởi động |
| `djangorestframework-simplejwt` | Tổ chức Jazzband đang giải thể ([ADR 0002](../adr/0002-auth-nextauth-session-django-jwt.md)) |
| `django-cors-headers` | Mọi request đi qua Next.js BFF, trình duyệt không gọi thẳng Django ([ADR 0009](../adr/0009-nextjs-bff-django-private.md)) |
| `django-money`, `py-moneyed` | VND không có số lẻ, lưu số nguyên là đủ |
| `django-ratelimit` | Không cập nhật từ 2023; dùng throttling của DRF |
| `django-health-check` 4.x | Yêu cầu Django 6; tự viết `/healthz`, `/readyz` |
| MinIO | Ngừng bảo trì từ 04/2026 |
| Kafka, Schema Registry | Chưa cần ở quy mô MVP ([ADR 0007](../adr/0007-events-outbox-celery-no-kafka.md)) |
| `uvicorn-worker`, chạy ASGI | Mọi view đồng bộ; chạy dưới ASGI chỉ thêm bước chuyển qua thread pool và phải tắt `CONN_MAX_AGE`. Tính lại khi cần websocket hoặc streaming |
