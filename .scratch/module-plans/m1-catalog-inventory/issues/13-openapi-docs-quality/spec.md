# 13 — Chất lượng OpenAPI và Swagger UI

**What to build:** Dev mở `/api/docs/` thấy endpoint nhóm theo ứng dụng và module, mỗi operation có tóm tắt và ví dụ tiếng Anh, biết cách lấy token và gọi thử; checker chặn mọi operation mới thiếu chú thích hoặc lẫn tiếng Việt, nên chất lượng này giữ được cho các ticket M1 sau.

Blocked by: 01 — `AutoSchema` 401/403/503 và hai endpoint auth (PR #65). Làm trước 03–11 dù số lớn hơn: 03, 04 bị chặn bởi ticket này.

Status: ready-for-agent

**PR:** —

## Việc cần làm

- Cấu hình drf-spectacular: `info.description`, Swagger UI settings, chỉ nhận JSON.
- `shared.api.schema.AutoSchema`: tag tự suy ra, bỏ docstring, mô tả và ví dụ lỗi mặc định tiếng Anh, header `Retry-After` cho 429.
- Luật chất lượng trong `scripts/gen_openapi.py --check`, có test.
- Chú thích đủ cho mọi operation đang có (`backoffice auth/login`, `backoffice auth/me`, `store geo/provinces`, `store geo/provinces/{code}/wards`) và sinh lại `openapi.yaml`.
- Cập nhật tài liệu và skill.

## Quyết định

Chốt qua grilling ngày 04/11/2026.

| Chủ đề | Quyết định |
|---|---|
| Người dùng schema | Dev đọc Swagger UI. Frontend không sinh client từ schema, nên `operationId` để drf-spectacular tự sinh; mở ticket đặt tên khi chuyển sang sinh client. |
| Nhóm | Tag `<store\|backoffice> · <module>`, do `AutoSchema` suy ra: ứng dụng từ path `/api/v1/<store\|backoffice>/`, module từ package của view (`modules.identity…` → `identity`, `shared.geo` → `geo`). View không tự khai tag. |
| Content type | `DEFAULT_PARSER_CLASSES = [JSONParser]` toàn cục; endpoint upload (ticket 06) tự khai `MultiPartParser`. Swagger không còn hiện form/multipart cho endpoint JSON. |
| Ngôn ngữ | Mọi chữ hiển thị trên Swagger viết tiếng Anh: `info.description`, `summary`, `description`, mô tả lỗi mặc định, dữ liệu ví dụ. Đây là ngoại lệ có chủ đích của quy tắc "tài liệu viết tiếng Việt": docstring vẫn tiếng Việt và `AutoSchema` không đưa docstring vào schema; mô tả chỉ lấy từ `extend_schema` / `extend_schema_serializer`. |
| Chú thích bắt buộc | Mỗi operation dưới `/api/v1/` có `summary`; ví dụ request khi có body; ví dụ cho mọi response 2xx có body; ví dụ `ErrorDTO` đúng `code` cho mã lỗi view tự khai (409, 422, 401 `INVALID_CREDENTIALS`…). Lỗi mặc định (400/401/403/404/429/500/503) nhận ví dụ chung do `AutoSchema` gắn. Dữ liệu ví dụ là dữ liệu giả (`staff@example.com`). |
| 429 | Mọi response 429 do `AutoSchema` sinh có header `Retry-After` (integer, giây). Đóng mục backlog 01/11/2026 của backend-bootstrap/22 về `Retry-After` và ví dụ. |
| Trang giới thiệu | `SPECTACULAR_SETTINGS["DESCRIPTION"]` tiếng Anh: hai ứng dụng `store`/`backoffice` và chỉ BFF Next.js gọi API; lấy token (`POST backoffice/auth/login` → Authorize với access token); định dạng `ErrorDTO` (`message` dịch theo `Accept-Language`, mặc định `vi`); header chung `Accept-Language`, `X-Request-ID`, `Idempotency-Key`. Không khai `SERVERS` để Swagger gọi đúng host đang mở (local, staging). |
| Swagger UI | `SWAGGER_UI_SETTINGS`: `persistAuthorization`, `displayRequestDuration`, `filter`, `docExpansion: "none"`, `deepLinking`. Token lưu trong localStorage chấp nhận được vì Swagger chỉ bật ở local và staging nội bộ (04 §4.4). |
| Checker | Luật nằm trong `gen_openapi.py --check` (đã chạy ở `make lint` và CI; pre-commit không chạy script này), không dùng hook Claude. Luật viết thành hàm thuần nhận dict schema đã render, chạy trước bước so drift; test luật nạp script bằng `importlib` và truyền dict mẫu (nhanh, mỗi luật một cặp đạt/vi phạm), thêm một test subprocess chứng minh `--check` in vi phạm từ schema render thật. Mỗi vi phạm in `<operationId>: <thiếu gì>`. Luật: (1) có `summary`; (2) có ví dụ request khi có body; (3) có ví dụ cho mọi 2xx có body; (4) có ví dụ `ErrorDTO` cho mã lỗi view tự khai, `code` của ví dụ ghi trong mô tả response dạng `` `CODE` `` (chốt ở review, S3); ví dụ không phải `ErrorDTO` là vi phạm, không crash; (5) lỗi mặc định (nhận bằng mô tả trùng `ERROR_DESCRIPTIONS`) không đòi ví dụ ở view; (6) tag đúng dạng `<store\|backoffice> · <module>`, path ngoài `/api/v1/` được miễn; (7) không có ký tự tiếng Việt có dấu trong `summary`, `description`, ví dụ, trừ field `message` của ví dụ lỗi. |
| Ghi ngoại lệ ngôn ngữ | `04-api-contract.md` §5.6 và một dòng ở `13-python-django-coding-style.md` (docstring/serializer). Không sửa `CLAUDE.md` (checker chặn tự động), không cần ADR (đảo ngược được). Skill `ship-ticket-fashion` phase 2 thêm một dòng nhắc "view mới phải có summary + ví dụ tiếng Anh". |
| Docstring | `AutoSchema` bỏ docstring của view **và** serializer (hiện `AccountOutput` lộ docstring tiếng Việt thành mô tả component `AccountDTO`). `ERROR_BODY_SCHEMA`, `ERROR_DESCRIPTIONS` và mô tả 401 của login chuyển sang tiếng Anh; test mẫu `CUSTOM_NOT_FOUND_DESCRIPTION` đổi sang tiếng Anh. |
| Thứ tự slice | S1 `AutoSchema` + settings → S2 chú thích 4 operation → S3 checker. Checker vào sau cùng để `make lint` xanh ở mọi commit. |
| Tài liệu lệch phát hiện khi lập bản đồ | Sửa trong phase sync: 04 §5.6 còn ghi 401/403/503 "chưa khai mặc định" (đã làm ở ticket 01); 12 §5 ghi "frontend sinh TS client" trái quyết định *Người dùng schema*; 02 cây `scripts/` thiếu `gen_openapi.py`; gỡ cả mục backlog 401/403/503 của backend-bootstrap/22 (đã xong). |
| Tài liệu chi phối | `docs/architecture/04-api-contract.md::3`; `docs/architecture/04-api-contract.md::4.4`; `docs/architecture/04-api-contract.md::5.1`; `docs/architecture/04-api-contract.md::5.6`; `docs/architecture/12-testing-strategy.md::5`; `docs/architecture/13-python-django-coding-style.md::2`; `docs/architecture/13-python-django-coding-style.md::3.1`; `docs/architecture/13-python-django-coding-style.md::8`; `docs/architecture/02-backend-structure.md::5` (cây `shared/api/`, `scripts/`). |

## Acceptance criteria

- [ ] **AC1:** Swagger UI nhóm mọi operation theo tag `<store|backoffice> · <module>`; tag do `AutoSchema` suy ra, không view nào tự khai.
- [ ] **AC2:** Mọi operation hiện có có `summary`, ví dụ request/response 2xx và ví dụ cho lỗi tự khai, toàn bộ tiếng Anh; docstring không xuất hiện trong `openapi.yaml`.
- [ ] **AC3:** Endpoint JSON chỉ khai `application/json` cho request body; mọi 429 có header `Retry-After`.
- [ ] **AC4:** Trang Swagger có phần giới thiệu tiếng Anh (ứng dụng, cách lấy token, `ErrorDTO`, header chung) và các tuỳ chọn Swagger UI đã chốt.
- [ ] **AC5:** `gen_openapi.py --check` fail với thông báo `<operationId>: <thiếu gì>` cho từng luật 1–7, có test cho mỗi luật (cả trường hợp đạt và vi phạm); `make lint` xanh trên schema mới.
- [ ] **AC6:** 04 §5.6, 13 và skill phase 2 ghi quy ước; mục backlog `Retry-After`/ví dụ của backend-bootstrap/22 được gỡ.
