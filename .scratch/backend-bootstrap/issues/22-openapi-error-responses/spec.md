# Khai báo `ErrorDTO` và response lỗi trong OpenAPI

Status: resolved

**PR:** #54

Spec: [spec.md](../../spec.md)

Tách từ ticket [17](../17-shared-geo/spec.md) khi review ngày 30/10/2026.

## Bối cảnh

[04 mục 5.6](../../../../docs/architecture/04-api-contract.md) yêu cầu mỗi operation khai báo request, response, status, permission và error schema trong OpenAPI. Mọi lỗi API đã trả `ErrorDTO` qua `shared.api.exception_handler` (ticket 16), nhưng schema do drf-spectacular sinh chưa có component `ErrorDTO` và chưa operation nào khai báo response lỗi. Ví dụ `GET store/geo/provinces/{code}/wards` của ticket 17 trả 404 `ErrorDTO` nhưng OpenAPI chỉ ghi `200`.

## Việc cần làm

- Thêm component `ErrorDTO` (`{error: {code, message, details, request_id}}`, 04 mục 5.1) vào schema.
- Chọn cách gắn response lỗi cho operation (mặc định qua hook hoặc `AutoSchema` riêng, hay khai báo từng view bằng `extend_schema`), áp cho endpoint địa giới hiện có.
- Làm trước hoặc cùng ticket [03](../03-openapi-schema-drift-check/spec.md) để `openapi.yaml` commit lần đầu đã có `ErrorDTO`.

## Quyết định

Chốt khi grilling ngày 01/11/2026.

| Chủ đề | Quyết định |
|---|---|
| Tài liệu chi phối | `backend/shared/api/schema.py` (mới) → 04 §3 (bảng status và mã lỗi), §5.1 (`ErrorDTO`), §5.6 (OpenAPI); 02 §5 (cây `shared/api/`, thêm dòng `schema.py`). `backend/config/settings/base.py` → 02 §5 (`REST_FRAMEWORK`). `backend/shared/tests/test_api_schema.py` → 02 §9.2 (tên file test `test_api_*.py` của `shared`), 02 §9.5 (không cần factory: chỉ sinh schema), 12 §5 (OpenAPI). `docs/architecture/04-api-contract.md` §5.6 ghi cách gắn response lỗi mặc định trong cùng PR. |
| Cách gắn response lỗi | Subclass `AutoSchema` trong `shared/api/schema.py`, đặt làm `REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"]`. Override `get_operation` (method public): gọi super rồi thêm các mã lỗi mặc định mà operation chưa khai, theo thứ tự mã tăng dần để `openapi.yaml` của ticket 03 ổn định. Không chọn postprocessing hook (không biết view) hay `extend_schema` từng view (lặp ở mọi view của M1). View vẫn tự khai mã đặc thù (409, 422…) bằng `extend_schema`; mã đã khai thì không bị ghi đè. |
| Bộ mã mặc định | Mọi operation: 400, 500. View có throttle (`view.get_throttles()` khác rỗng): thêm 429 (sửa sau review, B3: view không throttle không trả được 429). Operation có path parameter hoặc có query `page` của phân trang: thêm 404 (sửa sau review, B1: `StandardPagination` trả 404 khi trang vượt quá cuối). Mô tả 400 kể cả `PARSE_ERROR` (JSON hỏng) mà `exception_handler` sinh từ DRF `ParseError`; 04 §3 thêm mã này ở phase sync (B2). 401/403 cho view không `AllowAny` và 503 `AUTH_STATE_UNAVAILABLE` để ticket JWT của M1, vì hiện anonymous nhận 403 chứ không phải 401 (chưa có lớp xác thực); ghi vào backlog. Không khai 405, 406, 415 để schema đỡ nhiễu. |
| Component `ErrorDTO` | DRF serializer có `@extend_schema_serializer(component_name="ErrorDTO")`, cùng kiểu `GeoDTO`, đặt trong `shared/api/schema.py`, đúng 04 §5.1: `{error: {code, message, details, request_id}}`, mọi field bắt buộc. Không dùng `APPEND_COMPONENTS` vì settings sẽ phải import `shared`. Phần `error` là schema viết tay gắn vào một `DictField` bằng `@extend_schema_field`, không phải nested serializer, để object nằm inline trong `ErrorDTO` thay vì sinh thêm một component (St1). Test so bộ key với `error_body()` của `exception_handler` để schema không lệch body thật (St2). |
| `details` | Object tự do (`additionalProperties`); mô tả ghi hình dạng của `VALIDATION_ERROR` (`fields: {field_path: string[]}`) và `{}` cho mã không có chi tiết. Component riêng cho `items`, `quote` thêm ở M2 khi có mã dùng tới. |
| `Retry-After` và ví dụ | Chưa làm: hai AC không đòi, chưa có frontend dùng. Ghi vào backlog (04 §5.6 đòi ví dụ trước khi frontend dùng). |
| Interface / seam | Seam là schema sinh ra (`call_command("spectacular", "--validate", "--fail-on-warn", "--file", …)` rồi đọc YAML). Deletion test: bỏ subclass thì mọi view phải lặp `extend_schema` với 400/429/500 và khai lại 200, nên subclass giữ được độ sâu. |

## Acceptance criteria

- [x] `manage.py spectacular --validate` sinh schema có component `ErrorDTO` đúng 04 mục 5.1.
- [x] Endpoint địa giới khai báo response 404 dạng `ErrorDTO` cho `geo/provinces/{code}/wards` và các status lỗi chung (400, 429, 500) theo cách đã chọn.
