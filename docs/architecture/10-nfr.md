# 10. Yêu cầu phi chức năng

> Trạng thái: **Đã chốt cho MVP** ([quy ước](../../README.md#trạng-thái-tài-liệu)). Con số là mục tiêu MVP với tải ~500–5.000 đơn/ngày.

## 1. Hiệu năng

| Chỉ số | Mục tiêu **[Giả định · kiểm chứng: test tải k6 trên staging trước đợt khuyến mãi lớn đầu tiên, [12](./12-testing-strategy.md) mục 9]** |
|---|---|
| p95 API đọc (danh sách, chi tiết Sản phẩm, giỏ) | ≤ 300 ms |
| p95 `POST /store/checkout` khi báo giá GHN có trong cache | ≤ 800 ms |
| Tải đỉnh khi khuyến mãi | 50 request/giây vào API, 10 đơn/giây, không bán vượt Tồn kho |
| IPN → đơn `PLACED` | p95 ≤ 5 giây |
| Email sau sự kiện | p95 ≤ 1 phút |

Cách đạt:

- Không N+1 query: `django-zeal` bật trong test, có N+1 thì test fail.
- Lọc "còn hàng" bằng `catalog_variant.is_available` (bản sao), không join sang `inventory`.
- Cache Redis: cây danh mục 5 phút, báo giá GHN 10 phút, địa giới 1 ngày.
- Checkout không gọi HTTP ra ngoài trong transaction; phí ship lấy từ cache báo giá (thường có từ `checkout/quote`) trước khi mở transaction, nên khoá dòng chỉ giữ lúc ghi DB.
- Thứ tự khoá ([13 mục 4](./13-python-django-coding-style.md#4-service-transaction-và-tác-vụ-bên-ngoài), [ADR 0012](../adr/0012-checkout-price-snapshot.md)):
  - Checkout tạo đơn: Cart → Tồn kho theo variant_id → Biến thể theo id → Voucher.
  - Cart mutation/merge khoá Cart theo id; không lấy Cart sau Tồn kho.
  - Transition đơn đã có: Order → Tồn kho → Biến thể cần cập nhật → Voucher; không quay lại Cart.
- Auth state back-office/private storefront đọc DB theo 05, không dùng cache để cấp quyền ghi; p95 phải đo với policy này.

## 2. Độ sẵn sàng và phục hồi

| Chỉ số | Mục tiêu **[Giả định · kiểm chứng: diễn tập khôi phục RDS PITR trên staging trước go-live; độ sẵn sàng đo từ tháng đầu production]** |
|---|---|
| Độ sẵn sàng API (production) | 99,5% / tháng |
| RPO | ≤ 5 phút (RDS PITR) |
| RTO | ≤ 1 giờ |
| GHN lỗi | Vẫn checkout (phí ship dự phòng) |
| VNPay/MoMo lỗi | Vẫn đặt đơn COD |
| Redis lỗi | API vẫn chạy, kể cả checkout (chi tiết dưới) |

Khi Redis lỗi:

- Cache và throttle fail-open; chỉ còn rate limit thô của WAF.
- Kiểm tra `token_version` đọc thẳng PostgreSQL; `Idempotency-Key` lưu ở PostgreSQL.
- Task đẩy sau commit (`enqueue_on_commit`) bị bỏ qua và ghi log, không làm request lỗi.
- Outbox/EventDelivery và EmailLog giữ việc chờ trong PostgreSQL; relay/job quét khôi phục khi broker và worker sống lại, kể cả task đã enqueue rồi mất.
- `/readyz` chỉ kiểm tra PostgreSQL, nên ALB không rút task API.

## 3. Bảo mật

Xem [05-auth-security.md](./05-auth-security.md). Thêm:

- Không lưu dữ liệu thẻ (phạm vi VNPay, MoMo).
- TLS 1.2+ từ trình duyệt và nhà cung cấp tới CloudFront và ALB public. Trong VPC, Next.js gọi Django qua ALB nội bộ bằng HTTP; security group ALB nội bộ chỉ nhận từ task Next.js. Chưa dùng HTTPS nội bộ (cần chứng chỉ riêng, ví dụ ACM Private CA).
- Encryption at rest: RDS, S3, ElastiCache.
- Django API chỉ nhận request từ Next.js (BFF) qua ALB nội bộ; từ internet chỉ vào `/api/v1/webhooks/*` ([ADR 0009](../adr/0009-nextjs-bff-django-private.md), [09](./09-deployment-aws-target.md)).
- Rà lỗ hổng phụ thuộc mỗi lần chạy CI.

## 4. Quan sát hệ thống (observability)

| Loại | Công cụ | Nội dung |
|---|---|---|
| Log | `structlog` → stdout (JSON) → CloudWatch | Mỗi dòng có `request_id`, `user_id`/`order_code` (nếu có); che PII |
| Lỗi | Sentry | API, Celery task, relay |
| Health | `/healthz` (tiến trình sống), `/readyz` (kết nối PostgreSQL) | ALB và ECS health check |
| Cảnh báo nghiệp vụ | Sentry / CloudWatch | Danh sách dưới |

Cảnh báo nghiệp vụ (ngưỡng **[Giả định · kiểm chứng: chỉnh theo số liệu staging và tháng đầu production]**):

- Outbox chưa lập delivery hoặc delivery pending tồn > 1.000.
- `delivery_lag()` > 60 giây (chỉ tính việc đã tới hạn, [07](./07-async-events-jobs.md) mục 1.1.1; lúc này job T4 bắt đầu bỏ lượt, mục 3.2).
- T4 bỏ lượt liên tục > 15 phút (`cancel_skipped_too_long`).
- Số Vận đơn quá 6 giờ chưa Đối soát tăng qua nhiều vòng liên tiếp (dấu hiệu webhook GHN chết).
- Tuổi delivery pending cũ nhất; có delivery failed chưa xử lý.
- EmailLog queued/sending > 5 phút hoặc failed.
- Relay hoặc job theo lịch lỡ check-in > 3 phút hoặc kết thúc lỗi (Sentry Cron Monitors, [07](./07-async-events-jobs.md) mục 3.4).
- ErasureRequest processing có handler thiếu/failed/rejected.
- Payment creation_status prepared/unknown quá lease; Thanh toán pending > 30 phút.
- Tỉ lệ đơn dùng Phí ship dự phòng > 10%.
- Cờ cần xử lý mở > 24 giờ.

`request_id`:

- Lấy từ header `X-Request-ID` khi `X-BFF-Secret` đúng và giá trị khớp `[A-Za-z0-9._-]{1,64}`; ngược lại tự sinh (`common.api.request_id`).
- Sai định dạng: ghi log `request_id_invalid` kèm `reason`, không kèm giá trị header. Response không trả header này.
- `common.events.publish` chép vào `correlation_id` của sự kiện; consumer gắn lại vào context log khi chạy handler, để lần theo luồng từ API tới email.

## 5. Khả năng mở rộng

| Khi | Làm gì |
|---|---|
| API chậm do CPU | Tăng số task ECS của API |
| Queue Celery dài | Tăng `worker`; tách worker riêng cho queue `emails`. Không tăng `worker-integrations` (luôn đúng 1 instance để giữ rate limit nhà cung cấp, [07](./07-async-events-jobs.md) mục 3.1); queue này dài thì tăng `rate_limit` của task nếu nhà cung cấp cho phép |
| Tìm kiếm chậm hoặc cần tìm sai chính tả | Thêm Meilisearch (giai đoạn 2) |
| Cần phát lại sự kiện cho hệ thống mới, hoặc > 1.000 sự kiện/giây | Thêm adapter Kafka ([ADR 0007](../adr/0007-events-outbox-celery-no-kafka.md)) |
| Một module cần scale/deploy độc lập | Tách thành service. Ranh giới `contracts.py` và sự kiện đã có, nhưng trước đó phải bỏ FK chéo module ([ADR 0006](../adr/0006-modular-monolith.md) cho phép) và tách bảng module khỏi chuỗi migration chung |

## 6. Chất lượng code

Cổng chặn CI (lint, type check, ranh giới module, test, coverage, OpenAPI, migration, lỗ hổng phụ thuộc) định nghĩa duy nhất ở [12-testing-strategy.md](./12-testing-strategy.md) mục 8.

## 7. Bản địa hoá

- Thời gian lưu UTC, hiển thị `Asia/Ho_Chi_Minh`.
- `error.message` và email dịch vi/en bằng `gettext`; mặc định `vi`.
- Nội dung Sản phẩm, danh mục chỉ tiếng Việt.
- Tiền VND là số nguyên; định dạng hiển thị ("250.000 ₫") do Frontend lo.
