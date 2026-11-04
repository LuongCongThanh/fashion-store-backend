# Mỗi module là một Django app; `common` cho hạ tầng nội bộ, `infrastructure` cho bên thứ ba

Thay [ADR 0006](./0006-modular-monolith.md) ở phần tổ chức Django app. Các quy tắc ranh giới của 0006 vẫn giữ: module khác chỉ dùng `contracts.py`, `events.py`, `exceptions.py`; lớp dưới báo lên lớp trên bằng sự kiện; phụ thuộc đi một chiều; FK chỉ theo chiều phụ thuộc và không dùng để truy vấn xuyên module.

Gốc repo chính là Django project, không còn thư mục `backend/`. **Module** là một vùng nghiệp vụ có ranh giới và là **đúng một Django app** trong `apps/`, có `migrations/` riêng:

```
<repo>/
├── manage.py, pyproject.toml, uv.lock, Makefile, Dockerfile, docker-compose.yml
├── config/            # settings, urls, celery, env
├── apps/              # geo, identity, catalog, payments, shipping, inventory, promotions, ordering, notifications
├── common/            # hạ tầng nội bộ dùng chung; không phải module
├── infrastructure/    # code gọi API bên thứ ba; không phải module
├── tests/             # chỉ test xuyên module (flows/) và test công cụ (tooling/)
├── scripts/
└── docs/
```

- **`common/`**: thay `shared/`. Gồm nền model và lỗi, kiểu dữ liệu (`values/`), bảo mật (`security/`), log và health (`observability/`), nền DRF (`api/`), outbox (`events/`), `idempotency/`, `tasks.py`. Không import `apps/` hay `infrastructure/`.
- **`apps/geo/`**: dữ liệu địa giới hành chính tách khỏi `shared` thành module ở lớp dưới cùng, vì có model và API riêng.
- **`infrastructure/`**: mọi code của dự án dùng để gọi API bên thứ ba: `payment/` (VNPay, MoMo, Fake), `shipping/` (GHN, Fake), `google/` (xác minh `id_token`). Không import `apps/`, không đọc database; nhận và trả dữ liệu thuần. Mỗi package con chỉ module sở hữu được import (`payments`, `shipping`, `identity`). Thư viện chỉ cần cấu hình (email, storage, cache, Sentry) nằm trong `config/settings/`, không có thư mục ở đây.
- **Test** nằm trong `tests/` của app sở hữu, đường dẫn soi gương code: `apps/ordering/services/checkout.py` được kiểm ở `apps/ordering/tests/services/test_checkout.py`.

Lớp phụ thuộc, từ trên xuống: `notifications` → `ordering` → `inventory` | `promotions` → `identity` | `catalog` | `payments` | `shipping` → `geo` → `infrastructure` → `common`.

Lý do đổi: 0006 chọn một app chỉ để bớt một bước đăng ký app, đổi lại phải chịu `modules/models.py` import mọi model, `management/` và `templates/` bắt buộc nằm ở gốc app, tên class model phải duy nhất trong cả app, và mọi module dùng chung một chuỗi migration. Mỗi domain một app là cách Django và phần lớn dev Django đã quen, nên người mới đọc cấu trúc nhanh hơn. Thời điểm đổi rẻ: chưa có môi trường nào chạy thật và mới có `identity` có code, nên migration được sinh lại mà không phải chuyển dữ liệu.

## Các phương án đã cân nhắc

- **Giữ một app `modules` (ADR 0006)**: loại vì các lý do ở trên.
- **Adapter nằm trong module sở hữu** (`payments/providers/`): loại. Adapter không cần model; tách ra thì nhìn cây thư mục biết hệ thống tích hợp với ai, và module không phụ thuộc chi tiết HTTP.
- **Một cây `tests/` riêng soi gương toàn bộ code** (cách pytest khuyên cho thư viện đóng gói): loại. Đây là ứng dụng Django, không đóng gói; test cạnh app theo quy ước của Django và giữ factory trong module sở hữu.
- **Giữ cấp `backend/` hoặc đổi thành `src/`**: loại, vì repo chỉ chứa backend nên thêm một cấp thư mục không tách được gì.

## Hệ quả

- `AUTH_USER_MODEL = "identity.Account"`. App label là tên ngắn của module (`identity`, `ordering`…), `name` là đường dẫn đầy đủ (`apps.identity`).
- Sinh lại toàn bộ migration; mỗi dev chạy `make db-reset` một lần. Migration của app chỉ phụ thuộc app lớp dưới, nên không có vòng phụ thuộc giữa các chuỗi migration.
- Tiền tố bảng là label của app: `shared_*` đổi thành `common_*` (outbox, event delivery, idempotency) và `geo_*` (tỉnh/thành, phường/xã). Bảng của các module giữ nguyên tên.
- FK sang module khác vẫn khai bằng class được import, không dùng chuỗi, để `import-linter` kiểm được chiều. Quy tắc không truy vấn xuyên module vẫn chỉ kiểm được khi review.
- `import-linter` thêm hai lớp `apps.geo` và `infrastructure`, và contract cho mỗi package con của `infrastructure` chỉ module sở hữu được import.
- `shared/testing/` bị bỏ để không còn cặp tên `testing/` và `tests/`: factory về `common/tests/factories.py`, fixture dùng chung về `conftest.py` ở gốc, `drain_events()` về `common/events/testing.py`.
- Đường dẫn `backend/` trong CI, pre-commit (`files: ^backend/`), Dockerfile, `pyrightconfig.json` và [ADR 0017](./0017-windows-native-dev-api-on-host.md) đổi thành gốc repo. `.dockerignore` loại thêm `docs/`, `.scratch/`, `.claude/`.
