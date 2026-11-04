# `shared` thành `common` + `apps/geo`, `modules` thành `apps/identity`

Status: ready-for-agent

Blocked by: 01

Spec: [spec.md](../../spec.md)

Theo [ADR 0018](../../../../docs/adr/0018-one-django-app-per-module.md): mỗi module là một Django app trong `apps/`; `common` là hạ tầng nội bộ. Cây đích ở [02 mục 2](../../../../docs/architecture/02-backend-structure.md#2-cây-thư-mục). Không đổi hành vi.

## Việc cần làm

- **`common/`** (app label `common`) thay `shared/`, gom theo vai trò:
  - giữ ở gốc: `models.py`, `exceptions.py`, `tasks.py`;
  - `values/`: `money.py`, `phones.py`; `security/`: `privacy.py`, `checks.py`; `observability/`: `logging.py`, `health.py` (từ `health/views.py`);
  - giữ nguyên package: `api/`, `events/`, `idempotency/`;
  - `management/commands/`: các lệnh hạ tầng (relay, replay, retry, `sync_beat_schedule`, `reset_db`).
- **`apps/geo/`** (label `geo`) từ `shared/geo/`, kèm lệnh `load_geo`; API đặt ở `api/store/`.
- **`apps/identity/`** (label `identity`) từ `modules/identity/`, kèm lệnh `create_staff`. `AUTH_USER_MODEL = "identity.Account"`.
- Bỏ app `modules`: việc tự nạp `events.py`, `handlers.py` của `modules/apps.py` chuyển sang `common.events`, nạp từ mọi app trong `INSTALLED_APPS`.
- Bỏ `shared/testing/`: factory về `common/tests/factories.py`, fixture về `conftest.py` ở gốc, `drain_events()` về `common/events/testing.py`.
- Tên bảng: `shared_outbox_event`, `shared_event_delivery`, `shared_idempotency_key` → `common_*`; `shared_province`, `shared_ward` → `geo_province`, `geo_ward`.
- **Migration:** xoá migration cũ, sinh lại mỗi app một chuỗi. Giữ thao tác tạo extension `unaccent`, `pg_trgm`, `btree_gist` (đang ở `shared/migrations/0001_postgres_extensions.py`, viết tay) trong `common/migrations/0001`.
- Celery: `autodiscover_tasks()` tìm `tasks.py` của mọi app, cộng `common.events`, `common.idempotency`; đổi tên task `shared.*` thành `common.*` (`purge_old_outbox_events`, `purge_idempotency_keys`).
- `import-linter`: `root_packages = ["config", "common", "apps"]`; contract `layers` theo 02 mục 3 (chưa có `infrastructure`); sửa `scripts/_modules.py` quét `apps/`; sinh lại vùng `forbidden`; contract outbox trỏ `common.events.relay`, `common.events.tasks`.
- `scripts/check_module_coverage.py`, `[tool.coverage]`, `--cov=` trong CI và Makefile: `apps`, `common`.
- Comment `(02 mục X)` trong code: đổi theo đánh số mới của 02.
- Tài liệu: `03` (tên bảng, mục `## 1. shared`), `05`, `06`, `07` (tên job `shared.*`, `shared.events`), `08`, `10`, `12` (`--cov`), `13` (ví dụ code), `README.md` (dòng ADR 0008 `shared.models.uuid7`), `modules/geo.md` và `modules/identity.md` (bỏ ghi chú "đang nằm ở `shared/geo/`"); bỏ ghi chú "Cấu trúc đích" ở đầu 02.

## Quyết định

| Chủ đề | Quyết định |
|---|---|
| Tài liệu chi phối | `docs/adr/0018-one-django-app-per-module.md`, `docs/architecture/02-backend-structure.md::2,3,4,6`, `docs/architecture/03-data-model.md::0,1,2`, `docs/architecture/07-async-events-jobs.md::3.2`, `docs/architecture/12-testing-strategy.md::4,8`, `docs/adr/0008-uuid-v7-primary-keys.md` |
| Lớp | `notifications` → `ordering` → `inventory` \| `promotions` → `identity` \| `catalog` \| `payments` \| `shipping` → `geo` → `common`; module chưa có code không khai trong `layers` |
| Vị trí test | Ticket này chỉ chuyển test theo package của chúng (`shared/tests/` → `common/tests/`, `modules/identity/tests/` → `apps/identity/tests/`, test geo → `apps/geo/tests/`), chưa đổi tên file; ticket 03 làm phần soi gương |

## Acceptance criteria

- [ ] Không còn package `shared`, `modules`. `INSTALLED_APPS` có `common`, `apps.geo`, `apps.identity`; `makemigrations --check` không sinh gì.
- [ ] `make db-reset` rồi `make migrate`, `load_geo`, `create_staff`, đăng nhập back-office chạy được như trước.
- [ ] `lint-imports` xanh với contract mới; test ranh giới import (`tests/tooling/test_import_boundaries.py`) chứng minh module import nội bộ module khác vẫn fail.
- [ ] `make fmt`, `make lint`, `make test` xanh; cổng branch coverage đạt cho `apps.identity`, `apps.geo`, `common`.
- [ ] `git grep -nE "\bshared[./]|\bmodules\."` chỉ còn trong `.scratch/` và ADR lịch sử.
