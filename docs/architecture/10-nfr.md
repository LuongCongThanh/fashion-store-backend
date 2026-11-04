# 10. Yêu cầu phi chức năng

> Trạng thái: **Đã chốt cho MVP** ([quy ước](../../README.md#trạng-thái-tài-liệu)). Các con số là mục tiêu cho MVP với tải khoảng 500–5.000 đơn/ngày.

## 1. Hiệu năng

| Chỉ số | Mục tiêu **[Giả định · kiểm chứng: test tải k6 trên staging trước đợt khuyến mãi lớn đầu tiên, [12](./12-testing-strategy.md) mục 9]** |
|---|---|
| p95 thời gian phản hồi API đọc (danh sách, chi tiết Sản phẩm, giỏ) | ≤ 300 ms |
| p95 `POST /store/checkout` khi báo giá GHN đã có trong cache | ≤ 800 ms |
| Tải đỉnh khi có khuyến mãi | 50 request/giây vào API, 10 đơn/giây, không bán vượt Tồn kho |
| Thời gian từ IPN tới đơn chuyển `PLACED` | p95 ≤ 5 giây |
| Email gửi sau sự kiện | p95 ≤ 1 phút |

Cách đạt được:

- Không có N+1 query: `django-zeal` bật trong test, test fail nếu có.
- Danh sách Sản phẩm dùng `catalog_variant.is_available` (bản sao) để lọc "còn hàng" mà không phải join sang `inventory`.
- Cache trong Redis: cây danh mục (5 phút), báo giá GHN (10 phút), dữ liệu địa giới (1 ngày).
- Checkout không gọi HTTP ra ngoài bên trong transaction. Phí ship lấy từ cache báo giá (thường đã có từ bước `checkout/quote`) trước khi mở transaction, nên khoá dòng chỉ được giữ trong lúc ghi DB.
- Checkout tạo đơn mới khoá Cart → toàn bộ Tồn kho theo variant_id → toàn bộ Biến thể theo id → Voucher; mọi cart mutation/merge khoá Cart theo id, không lấy Cart sau Tồn kho. Transition của đơn đã có khoá Order → Tồn kho → Biến thể cần cập nhật → Voucher, không quay lại Cart. Xem [13 mục 4](./13-python-django-coding-style.md#4-service-transaction-và-tác-vụ-bên-ngoài) và [ADR 0012](../adr/0012-checkout-price-snapshot.md). Auth state back-office/private storefront đọc DB theo 05, không dùng cache để cấp quyền ghi; p95 phải đo với policy này.

## 2. Độ sẵn sàng và phục hồi

| Chỉ số | Mục tiêu **[Giả định · kiểm chứng: diễn tập khôi phục RDS PITR trên staging trước go-live; độ sẵn sàng đo từ tháng đầu production]** |
|---|---|
| Độ sẵn sàng của API (production) | 99,5% / tháng |
| RPO (dữ liệu tối đa có thể mất) | ≤ 5 phút (RDS PITR) |
| RTO (thời gian khôi phục) | ≤ 1 giờ |
| Khi GHN lỗi | Vẫn checkout được (phí ship dự phòng) |
| Khi VNPay/MoMo lỗi | Vẫn đặt được đơn COD |
| Khi Redis lỗi | API vẫn chạy, kể cả checkout: cache và throttle fail-open (chỉ còn rate limit thô của WAF), kiểm tra `token_version` đọc thẳng PostgreSQL, `Idempotency-Key` lưu ở PostgreSQL. Task đẩy sau commit (`enqueue_on_commit`) bị bỏ qua và ghi log, không làm request lỗi. Outbox/EventDelivery và EmailLog giữ công việc còn chờ trong PostgreSQL; relay/job quét khôi phục khi broker và worker hoạt động lại, kể cả task từng được enqueue rồi mất. `/readyz` chỉ kiểm tra PostgreSQL, nên ALB không rút task API khi Redis lỗi |

## 3. Bảo mật

Xem [05-auth-security.md](./05-auth-security.md). Thêm:

- Không lưu dữ liệu thẻ (thuộc phạm vi của VNPay, MoMo).
- Mã hoá khi truyền (TLS 1.2+) từ trình duyệt và nhà cung cấp tới CloudFront và ALB public. Trong VPC, Next.js gọi Django qua ALB nội bộ bằng HTTP; security group của ALB nội bộ chỉ nhận từ task Next.js. HTTPS nội bộ cần chứng chỉ riêng (ví dụ ACM Private CA) nên chưa dùng.
- Mã hoá khi lưu: RDS, S3, ElastiCache bật encryption at rest.
- Django API chỉ nhận request từ Next.js (BFF) qua ALB nội bộ; từ internet chỉ vào được `/api/v1/webhooks/*` ([ADR 0009](../adr/0009-nextjs-bff-django-private.md), [09](./09-deployment-aws-target.md)).
- Rà soát lỗ hổng phụ thuộc trong mỗi lần chạy CI.

## 4. Quan sát hệ thống (observability)

| Loại | Công cụ | Nội dung |
|---|---|---|
| Log | `structlog` → stdout (JSON) → CloudWatch | Mỗi dòng có `request_id`, `user_id` (nếu có), `order_code` (nếu có); che PII |
| Lỗi | Sentry | API, Celery task, relay |
| Health | `/healthz` (tiến trình sống), `/readyz` (kết nối được PostgreSQL) | Dùng cho ALB và ECS health check |
| Chỉ số nghiệp vụ cần cảnh báo | Sentry / CloudWatch | Outbox chưa lập delivery hoặc delivery pending tồn quá 1.000; `delivery_lag()` quá 60 giây (chỉ tính công việc đã tới hạn, [07](./07-async-events-jobs.md) mục 1.1.1; lúc này job T4 bắt đầu bỏ qua lượt chạy, mục 3.2); T4 bỏ lượt liên tục quá 15 phút (`cancel_skipped_too_long`); số Vận đơn quá 6 giờ chưa Đối soát tăng qua nhiều vòng liên tiếp (dấu hiệu webhook GHN đã chết); tuổi delivery pending cũ nhất; EmailLog queued/sending quá 5 phút hoặc failed; relay hoặc job theo lịch lỡ check-in quá 3 phút hoặc kết thúc lỗi (Sentry Cron Monitors, [07](./07-async-events-jobs.md) mục 3.4); ErasureRequest processing có handler thiếu/failed/rejected; Payment creation_status prepared/unknown quá lease; Thanh toán pending quá 30 phút; tỉ lệ đơn dùng Phí ship dự phòng > 10%; có delivery failed chưa xử lý; Cờ cần xử lý mở quá 24 giờ. Các ngưỡng là **[Giả định · kiểm chứng: chỉnh theo số liệu staging và tháng đầu production]** |

`request_id` lấy từ header `X-Request-ID` khi `X-BFF-Secret` đúng và giá trị khớp `[A-Za-z0-9._-]{1,64}`, ngược lại tự sinh (`common.api.request_id`); giá trị sai định dạng ghi log `request_id_invalid` kèm `reason`, không kèm giá trị header. Response không trả lại header này. `common.events.publish` chép giá trị này vào `correlation_id` của sự kiện, và consumer gắn lại vào context log khi chạy handler, để lần theo một luồng từ API tới email.

## 5. Khả năng mở rộng

| Khi | Làm gì |
|---|---|
| API chậm do CPU | Tăng số task ECS của API |
| Queue Celery dài | Tăng `worker`; tách worker riêng cho queue `emails`. Không tăng `worker-integrations`: queue này luôn đúng 1 instance để giữ rate limit nhà cung cấp ([07](./07-async-events-jobs.md) mục 3.1); queue này dài thì tăng `rate_limit` của task nếu nhà cung cấp cho phép |
| Tìm kiếm chậm hoặc cần tìm sai chính tả | Thêm Meilisearch (giai đoạn 2) |
| Cần phát lại sự kiện cho hệ thống mới, hoặc lưu lượng > 1.000 sự kiện/giây | Thêm adapter Kafka ([ADR 0007](../adr/0007-events-outbox-celery-no-kafka.md)) |
| Một module cần scale hoặc deploy độc lập | Tách module đó thành service. Ranh giới `contracts.py` và sự kiện đã có, nhưng trước đó phải bỏ các FK chéo module ([ADR 0006](../adr/0006-modular-monolith.md) cho phép) và tách bảng của module khỏi chuỗi migration chung |

## 6. Chất lượng code

Các cổng chặn trong CI (lint, type check, ranh giới module, test, coverage, OpenAPI, migration, lỗ hổng phụ thuộc) được định nghĩa một chỗ duy nhất ở [12-testing-strategy.md](./12-testing-strategy.md) mục 8.

## 7. Bản địa hoá

- Thời gian lưu UTC, hiển thị `Asia/Ho_Chi_Minh`.
- `error.message` và email dịch vi/en bằng `gettext`; mặc định `vi`.
- Nội dung Sản phẩm, danh mục chỉ tiếng Việt.
- Số tiền VND là số nguyên; định dạng hiển thị ("250.000 ₫") do Frontend lo.
