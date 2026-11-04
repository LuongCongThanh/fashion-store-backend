# 02 – `shared` thành `common` + `apps/geo`, `modules` thành `apps/identity`

Status: ready-for-agent · Ưu tiên: 3 · Blocked by: [01](../01-flatten-repo-root/spec.md) · **PR:**

Spec: [spec.md](../../spec.md)

## Mục tiêu
Mỗi module là một Django app trong `apps/`, `common` là hạ tầng nội bộ, đúng cây ở [02 mục 2](../../../../docs/architecture/02-backend-structure.md#2-cây-thư-mục). Không đổi hành vi.

## Việc cần làm
- [x] **`common/`** (label `common`) thay `shared/`:
  - gốc: `models.py`, `exceptions.py`, `tasks.py`;
  - `values/`: `money.py`, `phones.py` · `security/`: `privacy.py`, `checks.py` · `observability/`: `logging.py`, `health.py` (từ `health/views.py`);
  - giữ nguyên package: `api/`, `events/`, `idempotency/`;
  - `management/commands/`: lệnh hạ tầng (relay, replay, retry, `sync_beat_schedule`, `reset_db`).
- [x] **`apps/geo/`** (label `geo`) từ `shared/geo/`, kèm lệnh `load_geo`; API ở `api/store/`.
- [x] **`apps/identity/`** (label `identity`) từ `modules/identity/`, kèm `create_staff`; `AUTH_USER_MODEL = "identity.Account"`.
- [x] Xoá các package rỗng `modules/{catalog,inventory,ordering,payments,promotions,shipping,notifications}/`; app tương ứng tạo khi module bắt đầu có code.
- [x] Bỏ app `modules`: việc tự nạp `events.py`, `handlers.py` trong `modules/apps.py` chuyển sang `common.events`, nạp từ mọi app trong `INSTALLED_APPS`.
- [x] Bỏ `shared/testing/`: factory → `common/tests/factories.py`; fixture → `conftest.py` ở gốc; `drain_events()` → `common/events/testing.py`.
- [x] Đổi tên bảng: `shared_outbox_event`, `shared_event_delivery`, `shared_idempotency_key` → `common_*`; `shared_province`, `shared_ward` → `geo_province`, `geo_ward`.
- [x] Migration: xoá cũ, sinh lại mỗi app một chuỗi. Chép thao tác tạo extension `unaccent`, `pg_trgm`, `btree_gist` (viết tay ở `shared/migrations/0001_postgres_extensions.py`) vào `common/migrations/0001`.
- [x] Celery: `autodiscover_tasks()` tìm `tasks.py` mọi app + `common.events`, `common.idempotency`; đổi task `shared.*` → `common.*` (`purge_old_outbox_events`, `purge_idempotency_keys`).
- [x] `import-linter`: `root_packages = ["config", "common", "apps"]`; contract `layers` theo 02 mục 3 (chưa có `infrastructure`); `scripts/_modules.py` quét `apps/`; sinh lại vùng `forbidden`; contract outbox trỏ `common.events.relay`, `common.events.tasks`.
- [x] `scripts/check_module_coverage.py`, `[tool.coverage]`, `--cov=` trong CI và Makefile: `apps`, `common`.
- [x] Comment `(02 mục X)` trong code: đổi theo đánh số mới của 02.
- [x] Chuyển test theo package (chưa đổi tên file): `shared/tests/` → `common/tests/`, `modules/identity/tests/` → `apps/identity/tests/`, test geo → `apps/geo/tests/`.
- [x] Tài liệu: `03` (tên bảng, mục `## 1. shared`), `05`, `06`, `07` (job `shared.*`, `shared.events`), `08`, `10`, `12` (`--cov`), `13` (ví dụ code), `README.md` (dòng ADR 0008 `shared.models.uuid7`), `modules/geo.md`, `modules/identity.md` (bỏ ghi chú "đang nằm ở `shared/geo/`"); bỏ ghi chú "Cấu trúc đích" đầu 02.

## Quyết định
- Tài liệu chi phối: [ADR 0018](../../../../docs/adr/0018-one-django-app-per-module.md), [02](../../../../docs/architecture/02-backend-structure.md) mục 2, 3, 4, 6, [03](../../../../docs/architecture/03-data-model.md) mục 0, 1, 2, [07](../../../../docs/architecture/07-async-events-jobs.md) mục 3.2, [12](../../../../docs/architecture/12-testing-strategy.md) mục 4, 8, [ADR 0008](../../../../docs/adr/0008-uuid-v7-primary-keys.md).
- Thứ tự lớp: `notifications` → `ordering` → `inventory` | `promotions` → `identity` | `catalog` | `payments` | `shipping` → `geo` → `common`. Module chưa có code không khai trong `layers`.
- Sinh lại migration, không viết migration chuyển dữ liệu (xem [spec](../../spec.md)).
- Đổi tên file test để ticket [03](../03-mirror-test-layout/spec.md).

## Acceptance criteria
- [x] Không còn package `shared`, `modules`. `INSTALLED_APPS` có `common`, `apps.geo`, `apps.identity`; `makemigrations --check` không sinh gì.
- [x] `make db-reset` rồi `make migrate`, `load_geo`, `create_staff`, đăng nhập back-office chạy như trước.
- [x] `lint-imports` xanh với contract mới; `tests/tooling/test_import_boundaries.py` chứng minh module import nội bộ module khác vẫn fail.
- [x] Số test thu thập (`pytest --collect-only -q`) trước và sau bằng nhau (ghi số trước khi bắt đầu).
- [x] `make fmt`, `make lint`, `make test` xanh; cổng branch coverage đạt cho `apps.identity`, `apps.geo`, `common`.
- [x] `git grep -nE "\bshared[./]|\bmodules\."` chỉ còn trong `.scratch/` và ADR lịch sử.

## Ghi chú
- Factory của geo nằm ở `apps/geo/tests/factories.py`, không ở `common/tests/factories.py`: `common` không được import `apps`.
- Contract `layers` thật chỉ có `apps.identity`, `apps.geo`, `common`; `tests/tooling/test_import_boundaries.py` thay bằng đủ thứ tự lớp ở 02 mục 3 trên cây tạm để vẫn kiểm module tương lai.
- `AccountManager` override `get_queryset` thay cho `from_queryset`: plugin django-stubs không suy được kiểu lớp sinh động sau khi đổi package; hành vi không đổi.
- Tên constraint `shared_*` cũng đổi sang `common_*` cùng tên bảng.
- Quên migration extension thì `unaccent`/`pg_trgm`/`btree_gist` mất trên DB mới; `makemigrations` không tự sinh lại.
- Mô tả PR nhắc mọi dev chạy `make db-reset` một lần.
