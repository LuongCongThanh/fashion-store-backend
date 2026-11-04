# 14. Package dùng và không dùng

> Trạng thái: **Đã chốt cho MVP** ([quy ước](../../README.md#trạng-thái-tài-liệu)).

- File này ghi **vì sao** chọn/loại package. Phiên bản chỉ nằm ở `pyproject.toml` + `uv.lock` (nguồn chuẩn duy nhất); tài liệu không chép số phiên bản.
- Package nghiệp vụ chỉ thêm vào `pyproject.toml` ở mốc thực sự dùng tới.

## 1. Nền tảng

| Hạng mục | Lựa chọn | Ghi chú |
|---|---|---|
| Ngôn ngữ | Python 3.14 | `.python-version` |
| Framework | Django 5.2 LTS | Hỗ trợ tới 04/2028; lên 6.2 LTS khoảng Q3/2027 |
| Database | PostgreSQL 18, extension `unaccent`, `pg_trgm`, `btree_gist` | RDS, CI dùng 18; local dùng major mới nhất ([ADR 0015](../adr/0015-local-postgres-on-host.md)) |
| Cache, broker | Redis: **Valkey 8** ở local, ElastiCache for Valkey trên AWS ([09](./09-deployment-aws-target.md)) | Gọi chung "Redis" theo tên giao thức/thư viện (`redis-py`, `redis://`); Valkey tương thích nên không sửa code |
| Quản lý package | uv | `uv sync --locked --no-build` |

## 2. Runtime

| Package | Dùng để | Vì sao chọn |
|---|---|---|
| `django` | Framework | LTS, hệ sinh thái đã tương thích |
| `djangorestframework` | REST API | Phổ biến nhất, team đã quen |
| `drf-spectacular` | OpenAPI 3, Swagger UI | Chuẩn de facto cho DRF; chưa sinh TS client ([12](./12-testing-strategy.md) mục 5) |
| `django-filter` | Lọc danh sách (size, màu, giá, trạng thái) | Tích hợp sẵn DRF |
| `psycopg[binary,pool]` | Driver PostgreSQL (psycopg 3) | Wheel binary khớp `uv sync --locked --no-build`; dùng pool của Django 5.2 (`OPTIONS["pool"]`, `CONN_MAX_AGE = 0`) |
| `redis` | Client Redis | Cache, throttling, Celery |
| `celery` | Worker chạy job | Retry, định tuyến queue, hệ sinh thái lớn |
| `django-celery-beat` | Lịch job trong DB (`DatabaseScheduler`) | Beat trên ECS không cần ổ đĩa. Lịch khai trong code (`beat_schedule`), đồng bộ vào DB khi beat khởi động; đổi lịch thì sửa code |
| `pydantic` | Schema sự kiện, DTO của `contracts.py` | Có type, validate, sinh JSON Schema (chuẩn bị Schema Registry) |
| `pydantic-settings` | Biến môi trường có kiểu (`config/env.py`) | Sai cấu hình báo lỗi ngay khi khởi động |
| `PyJWT[crypto]` | Ký/kiểm JWT (Ed25519) | Không tự viết mật mã ([ADR 0002](../adr/0002-auth-nextauth-session-django-jwt.md)) |
| `cryptography` | Mã hoá response refresh trong RefreshReplay (AESGCM, 10 giây) | Dependency trực tiếp; không tự viết crypto ([05](./05-auth-security.md) mục 2.1) |
| `google-auth` | Xác minh `id_token` Google (`infrastructure/google/`) | Thư viện chính thức |
| `argon2-cffi` | Hash mật khẩu Argon2 | OWASP khuyến nghị |
| `django-fsm-2` | Máy trạng thái Đơn hàng | `django-fsm` gốc chuyển sang viewflow; bản này giữ API cũ, django-commons duy trì |
| `django-pghistory` | Lịch sử thay đổi (Đơn hàng, Thanh toán, Tồn kho, cấu hình vận hành); chỉ field tường minh, không raw payload/PII ([03](./03-data-model.md) mục 10.1) | Trigger PostgreSQL bắt cả `bulk_update` |
| `httpx` | Gọi VNPay, MoMo, GHN (`infrastructure/`) | Timeout, retry rõ ràng; test bằng `respx` |
| `Pillow` | Xử lý ảnh Sản phẩm | Bắt buộc cho `ImageField` |
| `phonenumbers` | Parse, validate số Việt Nam, chuẩn hoá E.164 (`common/values/phones.py`) | Dùng chung cho lưu, tra cứu, giới hạn Voucher, xác định đối tượng ẩn danh |
| `django-storages[s3]` + `boto3` | Ảnh trên S3 (chỉ AWS) | Local dùng `FileSystemStorage` |
| `vietnam-provinces` | 34 tỉnh/thành và phường/xã sau 07/2025 (`apps/geo`) | Đã theo cấu trúc 2 cấp |
| `structlog` + `django-structlog` | Log JSON có `request_id` | Dễ tìm trên CloudWatch |
| `sentry-sdk[django,celery]` | Theo dõi lỗi, hiệu năng | Chuẩn |
| `gunicorn` | Server production (WSGI, worker `gthread`) | Code đồng bộ (DRF, ORM); ASGI chỉ thêm chi phí `sync_to_async`. Chỉ chuyển khi cần async (ví dụ SSE) |

## 3. Dev và test

Khai trong `[dependency-groups] dev` của `pyproject.toml`.

| Package | Dùng để |
|---|---|
| `ruff` | Lint, format (thay flake8, isort, black) |
| `mypy` + `django-stubs` + `djangorestframework-stubs` | Kiểm kiểu, plugin hiểu Django ORM. Không dùng extra `compatible-mypy` (giới hạn phiên bản mypy) |
| `celery-types` | Stub Celery cho mypy/IDE (`shared_task`, `app.send_task`) |
| `import-linter` | Ranh giới module, bắt buộc trong CI ([02](./02-backend-structure.md) mục 6) |
| `pytest` + `pytest-django`, `pytest-xdist` | Chạy test, chạy song song |
| `coverage`, `pytest-cov` | Độ phủ, kể cả khi chạy song song |
| `factory-boy` | Dữ liệu test |
| `respx` | Giả lập API ngoài khi test `httpx` |
| `time-machine` | Cố định thời gian (Giữ hàng 15 phút, Hoàn tất sau 7 ngày) |
| `django-zeal` | Phát hiện N+1 query khi test |
| `django-test-migrations` | Test data migration có `RunPython` ([12](./12-testing-strategy.md) mục 6) |
| `pip-audit` | Lỗ hổng đã công bố trong dependency (CI) |
| `pre-commit` | Chạy ruff, mypy, import-linter, hook `pre-commit-hooks` trước commit |
| `commitizen` | Kiểm commit message Conventional Commits, gắn tag, sinh CHANGELOG ([11](./11-git-workflow.md)) |

## 4. Không dùng

| Package | Lý do |
|---|---|
| `requirements/*.txt` | Một nguồn: `pyproject.toml` + `uv.lock` có hash |
| `django-environ` | `pydantic-settings` có kiểu, báo lỗi khi khởi động |
| `djangorestframework-simplejwt` | Jazzband đang giải thể ([ADR 0002](../adr/0002-auth-nextauth-session-django-jwt.md)) |
| `django-cors-headers` | Trình duyệt không gọi thẳng Django, mọi request qua Next.js BFF ([ADR 0009](../adr/0009-nextjs-bff-django-private.md)) |
| `django-money`, `py-moneyed` | VND không số lẻ, lưu số nguyên |
| `django-ratelimit` | Không cập nhật từ 2023; dùng throttling DRF |
| `django-health-check` 4.x | Yêu cầu Django 6; tự viết `/healthz`, `/readyz` |
| MinIO | Ngừng bảo trì từ 04/2026 |
| Kafka, Schema Registry | Chưa cần ở MVP ([ADR 0007](../adr/0007-events-outbox-celery-no-kafka.md)) |
| `uvicorn-worker`, chạy ASGI | View đồng bộ; ASGI thêm bước qua thread pool và phải tắt `CONN_MAX_AGE`. Tính lại khi cần websocket/streaming |
