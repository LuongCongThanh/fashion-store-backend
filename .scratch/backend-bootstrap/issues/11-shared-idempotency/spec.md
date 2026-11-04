# Xử lý header `Idempotency-Key`

Status: resolved

**PR:** #40

Blocked by: 16

Spec: [spec.md](../../spec.md)

## Việc cần làm

- Model `IdempotencyKey` theo [03 mục 1.5](../../../../docs/architecture/03-data-model.md#15-common_idempotency_key-khoá-chống-tạo-trùng).
- `shared/api/idempotency.py`: claim key bằng transaction ngắn kèm lease, lưu kết quả cùng transaction với tác động nghiệp vụ, replay kết quả đã `completed`, theo quy ước ở [04 mục 1](../../../../docs/architecture/04-api-contract.md#1-quy-ước-chung). Scope = method + endpoint chuẩn hoá + danh tính (Tài khoản hoặc guest cart token).
- Job `purge_idempotency_keys`: chỉ xoá bản ghi `completed` quá 24 giờ.
- Một endpoint mẫu chỉ có trong `config.settings.test` để test hành vi.

## Quyết định

Chốt khi grilling ngày 30/10/2026.

| Chủ đề | Quyết định |
|---|---|
| Tài liệu chi phối | `shared/models.py`, `shared/migrations/0004_idempotency_key.py`: 03 §1.5, 03 §0.1 (BaseModel), 02 §9.1 (khoá chính), §9.2 (tên bảng, tên constraint), ADR 0008. `shared/idempotency.py` (lõi, thêm khi review): 03 §1.5 (ghi chú claim/lease), 02 §5 (cây `shared/`), 02 §6.1 (services import được), 02 §9.1 (*Transaction*), §9.6 (logging). `shared/api/idempotency.py` (lớp HTTP): 04 §1 (*Chống tạo trùng*), 04 §3 (ErrorDTO, 409, 415), 04 §5.2 (`IdempotencyPendingDTO`), 02 §5 (cây `shared/api/`). `shared/tasks.py`, `config/celery.py`: 07 §3.2 (`shared.purge_idempotency_keys` 03:45), 02 §9.2 (tên Celery task). `shared/testing/factories.py`: 02 §9.5. Test: 12 §2.2 (concurrency), 12 §2.4 (Idempotency-Key), 02 §9.2 (tên file test), §9.5 (factory, time-machine) |
| Model | `IdempotencyKey(BaseModel)` trong `shared/models.py` (02 §5), `db_table = "shared_idempotency_key"`. Cột, `UNIQUE(scope, key)`, hai `CHECK` và partial index `completed_at WHERE status='completed'` đúng 03 §1.5. Kế thừa `BaseModel` (có `id`, `created_at`, `updated_at`) theo 03 §0.1, khác outbox vì 03 §1.5 không loại trừ. `status` là `TextChoices` `in_progress/completed`; `operation_id` UK `default=uuid7` sinh khi claim |
| API | Hàm hai bước, không dùng decorator bọc view (checkout gọi GHN ngoài transaction, kết quả phải lưu trong transaction của service). `begin(request)` chạy transaction ngắn, trả một trong: `Replay` (status/body đã lưu), `Pending` (có `retry_after`, `response(outcome)` của lớp HTTP dựng `202 IdempotencyPendingDTO` + `Retry-After: 3`; người gọi tự dựng body 202 khác được, như `PaymentStartDTO`), `Claim` (`operation_id`, `lease_token`). Khác `request_hash` → raise `IdempotencyConflict` (`DomainError`, `409 IDEMPOTENCY_CONFLICT`), kể cả khi key còn `in_progress`. Service gọi `claim.complete(status, body, resource_id=None)` **bên trong** `atomic` của mình: khoá dòng key, lease không còn khớp thì raise để transaction nghiệp vụ rollback. Kiểm quyền/sở hữu là việc của view, làm trước `begin`. **Tách hai tầng (thêm khi review, T4/T1/T7):** lõi ở `shared/idempotency.py` gồm `Claim`, `Replay`, `Pending`, claim theo `(scope, key, request_hash)`, lease, `complete`, purge, `IdempotencyConflict`, `LeaseLost`; không import DRF hay `request`, để service import được (02 §6.1 cấm services import `api/`). `shared/api/idempotency.py` chỉ đọc header, dựng scope, tính hash, gọi lõi và dựng `Response` cho `Replay`/`Pending`. `complete` là một `UPDATE … WHERE pk AND lease_token`, 0 dòng → `LeaseLost` (kể cả dòng đã bị xoá); chỉ ghi `resource_id` khi được truyền, không xoá giá trị cũ (thêm khi review, A). `claim` mở `transaction.atomic(durable=True)` nên gọi khi đang trong `transaction.atomic` ngoài thì Django raise `RuntimeError`, vì transaction ngoài làm mất tính "ngắn" của claim và việc nhả key (thêm khi review, C) |
| Lỗi nghiệp vụ / rollback | `Claim` là context manager: exception thoát ra thì mở transaction ngắn, xoá dòng key nếu lease vẫn của mình và `resource_id` còn NULL, để gửi lại cùng key chạy lại từ đầu (AC4). Có `resource_id` thì giữ dòng cho luồng khôi phục. Không lưu response lỗi thành `completed` (04 §1: body đổi/quote mới dùng key mới) |
| Lease | Hằng `LEASE = 60 giây` trong module. `in_progress` còn lease → `Pending`; lease đã hết và cùng hash → giành lại với `lease_token` mới; worker cũ gọi `complete` thấy lệch lease thì raise, tác động của nó rollback theo. `LeaseLost` là `Exception` thường → 500 và Sentry: request chạy quá 60 giây là bất thường thật; client gửi lại cùng key nhận kết quả của worker mới. Không thêm mã lỗi (chốt khi review, T2) |
| Scope | `"{METHOD} {path}\|{identity}"`: `path` là `request.path` (đã gồm ID/mã tài nguyên), bỏ `/` cuối. `identity` = `account:<pk>` khi `request.user.is_authenticated` (cùng cách `AccountThrottle`), ngược lại `cart:<sha256(X-Cart-Token)>`; không lưu token thô. Không có danh tính → `400 VALIDATION_ERROR` |
| `request_hash` | SHA-256 của `request.data` đã parse, chuẩn hoá bằng `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)`, encode UTF-8 với `surrogatepass`; tính trước serializer. Body không phải JSON (multipart, form) → `415 UNSUPPORTED_MEDIA_TYPE`, vì `QueryDict`/file không chuẩn hoá được (thêm khi review, B) |
| Thiếu / sai header | Thiếu `Idempotency-Key` hoặc không phải UUID → `400 VALIDATION_ERROR`, `details` trỏ `Idempotency-Key` (04 §1 bắt buộc key; 12 §2.4 đòi test thiếu key). Không có trong AC, thêm theo tài liệu |
| Endpoint mẫu | View trong `shared/tests/api_urls.py`, chỉ nạp qua `pytest.mark.urls` (tiền lệ ticket 16): đây là cách hiểu "chỉ có trong `config.settings.test`", không đụng `config/urls.py`. Tác động nghiệp vụ là một dòng ở bảng chỉ dùng cho test tạo bằng `schema_editor` (mẫu `HandlerEffect`, `shared/tests/test_models.py`); cờ trong body làm view raise sau khi ghi, cho AC4 |
| Purge | `purge_idempotency_keys() -> int` trong `shared/idempotency.py`; xoá theo lô `PURGE_BATCH = 1000` (`select_for_update().order_by("id")`) như `purge_old_outbox_events`; điều kiện `status=completed AND completed_at < now - 24h` (đúng mốc 24 giờ chưa xoá); log `idempotency_keys_purged` kèm `count`. Celery task `shared.purge_idempotency_keys` (queue `default`) trong `shared/tasks.py` chỉ gọi hàm này; `config/celery.py` lịch `crontab(hour=3, minute=45)` |
| Concurrency | Hai request đồng thời cùng key: test `django_db(transaction=True)` + thread + `threading.Barrier` (12 §2.2, §2.4): đúng một lần tác động, một `operation_id`, bên kia nhận 202 |
| Ngoài phạm vi | `claim.attach_resource()` (ghi `resource_id` và commit trước khi gọi gateway) và `202 PaymentStartDTO`: ticket Thanh toán M2 thêm. Gắn `Idempotency-Key` vào checkout, Thanh toán, kho: ticket của các module đó |

## Acceptance criteria

- [x] Cùng key, cùng body: lần hai trả nguyên status và body đã lưu, không chạy lại tác động.
- [x] Cùng key, khác body: `409 IDEMPOTENCY_CONFLICT`.
- [x] Cùng key khi lần đầu còn xử lý: `202 IdempotencyPendingDTO` kèm `Retry-After`.
- [x] Tác động nghiệp vụ rollback thì key không ở trạng thái `completed`.
- [x] Cùng key nhưng khác danh tính không thấy kết quả của nhau.
- [x] Purge không xoá key `in_progress`.
