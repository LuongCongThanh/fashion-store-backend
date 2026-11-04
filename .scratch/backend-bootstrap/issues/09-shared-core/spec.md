# Phần dùng chung của `shared`: model cơ sở, tiền, số điện thoại, HMAC, lỗi, logging

Status: resolved

**PR:** #22

Blocked by: 07

Spec: [spec.md](../../spec.md)

Lớp API dùng chung tách sang ticket [16](../16-shared-api-layer/spec.md), địa giới hành chính sang ticket [17](../17-shared-geo/spec.md).

## Việc cần làm

- `shared/models.py`: `uuid7()` gọi `uuid.uuid7()`, `BaseModel` abstract (`id`, `created_at`, `updated_at`) theo [03 mục 0.1](../../../../docs/architecture/03-data-model.md#01-cột-chung-và-khoá) và [ADR 0008](../../../../docs/adr/0008-uuid-v7-primary-keys.md).
- `shared/money.py`: `Money(amount: int, currency="VND")`, từ chối float.
- `shared/phones.py`: `normalize_vn_phone` bằng `phonenumbers` theo [03 mục 0.6](../../../../docs/architecture/03-data-model.md#06-chuẩn-hoá-số-điện-thoại).
- `shared/privacy.py`: `pii_hmac(value) -> "<kid>:<hex>"` với keyring `PII_HMAC_KEYS` ([ADR 0016](../../../../docs/adr/0016-erasure-evidence-phone-hmac.md)).
- `shared/exceptions.py`: `DomainError(code, message, details)`, `RetryLater`.
- `shared/logging.py`: cấu hình structlog JSON, processor `redact_pii` ([13 mục 10](../../../../docs/architecture/13-python-django-coding-style.md#10-logging-exception-và-dữ-liệu-nhạy-cảm)).
- Migration `shared` bật `unaccent`, `pg_trgm`, `btree_gist` và tạo hàm `immutable_unaccent` ([03 mục 0.7](../../../../docs/architecture/03-data-model.md#07-khởi-tạo-và-seed)).

## Quyết định

Chốt khi grilling ngày 29/10/2026.

| Chủ đề | Quyết định |
|---|---|
| `PII_HMAC_KEYS` | `kid2:secret2,kid1:secret1`, khoá đầu dùng cho giá trị mới. `config/env.py` kiểm tra lúc khởi động: không rỗng, `kid` không trùng, `kid` và secret không rỗng. `manage.py check --deploy` (`shared.E001`) đòi mỗi secret từ 32 byte; local và CI dùng khoá ngắn được |
| `shared.privacy` | `pii_hmac(value)` dùng khoá đầu; `pii_hmac_candidates(value)` trả giá trị với mọi khoá để tra bằng `__in`. Không tự chuẩn hoá đầu vào |
| `Money` | Frozen dataclass; chỉ nhận `int` thật (từ chối `float`, `bool`, `Decimal`, `str`); cho phép số âm; `+`, `-`, `* int`, so sánh, chỉ giữa cùng `currency`; không có phép chia; chỉ `"VND"` |
| Số điện thoại | Mọi số hợp lệ thuộc VN, kể cả số cố định; từ chối số nước ngoài. Chỉ nhận chữ số và dấu phân cách, bắt đầu bằng `0` hoặc `+`: từ chối chữ cái, extension và số thiếu `+` trước mã nước để `phonenumbers` không tự đoán. Ném `InvalidPhoneNumber(ValueError)`, serializer đổi thành `400 VALIDATION_ERROR`; thông báo bọc `gettext_lazy`, không chứa số gốc |
| `DomainError` | `code`, `http_status` (mặc định 422), `message` (`gettext_lazy`) là thuộc tính lớp; `__init__(message=None, details=None)`. Khác chữ ký `DomainError(code, message, details)` ở mục Việc cần làm: `code` cố định theo lớp lỗi nên không truyền lúc ném. `RetryLater` không kế thừa `DomainError` |
| `redact_pii` | Khớp chuỗi con không phân biệt hoa thường với `email, phone, address, token, password, card, secret`; xử lý dict/list lồng nhau và `extra` của log stdlib; key đuôi `_hmac` không che. `configure_logging(json=...)`: local in dễ đọc, nơi khác JSON |
| `updated_at` | Manager của BaseModel: `update()` tự gán `updated_at` nếu thiếu; `bulk_update()` thiếu `updated_at` trong `fields` thì gán `timezone.now()` cho mọi object rồi thêm field (báo lỗi như bản đầu vẫn để DB giữ mốc cũ khi bên gọi quên gán giá trị); có sẵn thì giữ giá trị của từng object |
| Migration | `CreateExtension` cho ba extension; `public.immutable_unaccent(text)` gọi `public.unaccent` có schema, có reverse. Chưa thêm `django.contrib.postgres` vào `INSTALLED_APPS` (M1 thêm khi cần lookup) |

## Acceptance criteria

- [x] `0901234567` và `+84 901 234 567` cùng chuẩn hoá thành `+84901234567`; số không hợp lệ bị từ chối.
- [x] `pii_hmac` cùng đầu vào cho cùng kết quả với cùng `kid`; đổi khoá đầu keyring thì giá trị mới mang `kid` mới.
- [x] `Money` từ chối float.
- [x] Log có key `email`, `phone`, `token` bị che.
- [x] Sau migrate, ba extension và hàm `immutable_unaccent` có trong DB.
- [x] `QuerySet.update` và `bulk_update` của BaseModel tự cập nhật `updated_at` khi bên gọi không truyền.
- [x] Số có chữ cái, extension hoặc thiếu `+` trước mã nước bị từ chối.
- [x] `pii_hmac_candidates` tìm được giá trị ghi bằng khoá cũ sau khi xoay khoá.
- [x] `check --deploy` báo lỗi khi secret trong `PII_HMAC_KEYS` ngắn hơn 32 byte.
