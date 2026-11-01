# Báo cáo

### Báo cáo 01/11/2026

**Nhánh:** `feat/openapi-error-responses` · **PR:** #54 · **Mode:** lite

#### Đã làm

| AC | Bằng chứng |
| --- | --- |
| 1. `spectacular --validate` sinh component `ErrorDTO` đúng 04 §5.1 | `shared/tests/test_api_schema.py::test_schema_has_error_dto_component`, `shared/tests/test_api_schema.py::test_error_dto_keys_match_error_body` |
| 2. Endpoint địa giới khai 404 `ErrorDTO` cho `wards` và 400, 429, 500 | `shared/tests/test_api_schema.py::test_every_operation_declares_common_errors`, `shared/tests/test_api_schema.py::test_geo_operations_declare_exact_error_codes` |

Quy tắc thêm sau review: `shared/tests/test_api_schema.py::test_paginated_operation_declares_404` (B1), `shared/tests/test_api_schema.py::test_operation_without_throttle_omits_429` (B3), `shared/tests/test_api_schema.py::test_declared_error_response_is_kept` (mã view tự khai không bị ghi đè).

`make lint` xanh · `make test`: 327 passed

#### Chưa làm

- Không

#### Gap

- 401/403 cho view không `AllowAny` và 503 `AUTH_STATE_UNAVAILABLE` chưa khai mặc định: thêm ở ticket JWT của M1 (backlog).
- `Retry-After` của 429 và ví dụ (`OpenApiExample`) chưa có; 04 §5.6 đòi ví dụ trước khi frontend dùng (backlog).
- Operation webhook/HTML/CSV vẫn nhận `ErrorDTO` mặc định; chưa có view loại này, xem lại ở M3/M5 (backlog).
- `details` là object tự do; component riêng cho `items`, `quote` thêm ở M2.

#### Thay đổi theo yêu cầu

- Không

#### Review

| Mã | Chỗ | Kết luận | Lý do |
| --- | --- | --- | --- |
| B1 | `shared/api/schema.py` `_default_error_codes` | đã sửa | 404 cho list có query `page` (trang vượt quá cuối) |
| B2 | `shared/api/schema.py` `ERROR_DESCRIPTIONS` | đã sửa | mô tả 400 kể `PARSE_ERROR`; 04 §3 thêm mã |
| B3 | `shared/api/schema.py` `_default_error_codes` | đã sửa | 429 chỉ khi view có throttle |
| Sp1 / B6 | `shared/tests/test_api_schema.py` | đã sửa | test mã view tự khai không bị ghi đè |
| Sp2 | `shared/tests/test_api_schema.py` | đã sửa | kiểm `details.additionalProperties` |
| Sp3 | `shared/tests/test_api_schema.py` | đã sửa | so đúng tập mã lỗi |
| St1 | `spec.md` `## Quyết định` | đã sửa | ghi lý do schema viết tay (inline, không thêm component) |
| St2 | `shared/tests/test_api_schema.py` | đã sửa | bộ key `ErrorDTO` so với `error_body()` |
| St4 | `spec.md` `## Quyết định` | đã sửa | 503 để ticket JWT M1 |
| St5 / B8 | `shared/tests/test_api_schema.py` | đã sửa | bỏ `Path` thừa, đổi tên helper, gán biến trước assert |
| B4 | `shared/api/schema.py` | chỉ báo | miễn webhook/CSV khi có view loại này (backlog) |
| St3 | `shared/api/schema.py` | chỉ báo | response không đặt `additionalProperties: false`, như `GeoDTO` |
| B9 | `shared/api/schema.py` | bác | `resolve_serializer` trả component có sẵn trong registry |
| B5, B7 | `report.md`, tài liệu | đã sửa | làm ở sync: hash commit mới, 04 §3 §5.6, 02 §5 |

#### Commit

| Task | Phase | AC | Commit | File |
| --- | --- | --- | --- | --- |
| plan | 1 grill | — | `24314f9` docs: plan openapi error responses ticket | 2 |
| S1 | 2 code | 1, 2 | `65f7d49` feat(shared): declare ErrorDTO and default error responses in OpenAPI | 3 |
| R1 | 4 review | — | `8b9d532` fix(shared): address review findings on openapi error responses | 2 |

#### Tài liệu đã cập nhật

- `docs/architecture/04-api-contract.md`: §3 thêm `PARSE_ERROR` vào dòng 400; §5.6 ghi cách `AutoSchema` gắn response lỗi mặc định.
- `docs/architecture/02-backend-structure.md`: §5 cây `shared/api/` thêm `schema.py`.
- `.scratch/mvp-roadmap/map.md`: Decisions-so-far thêm dòng API OpenAPI lỗi cho mọi module.
- `.scratch/backlog.md`: 3 dòng (401/403/503 ở M1, `Retry-After` và ví dụ, miễn webhook/CSV).
