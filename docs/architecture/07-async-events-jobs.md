# 07. Sự kiện và job chạy nền

> Trạng thái: **Đã chốt cho MVP** ([quy ước](../../README.md#trạng-thái-tài-liệu)). Quyết định nền tảng: [ADR 0007](../adr/0007-events-outbox-celery-no-kafka.md), [ADR 0003](../adr/0003-postgres-redis-celery.md).

## 1. Luồng sự kiện (Transactional Outbox)

```mermaid
sequenceDiagram
    participant S as Service (ví dụ checkout)
    participant DB as PostgreSQL
    participant RL as Outbox relay
    participant RD as Redis (Celery broker)
    participant W as Celery worker
    participant H as Handler (ví dụ notifications)

    S->>DB: BEGIN
    S->>DB: INSERT order …
    S->>DB: INSERT shared_outbox_event (OrderPlacedV1)
    S->>DB: COMMIT
    loop mỗi 1 giây
        RL->>DB: Tạo EventDelivery cho từng handler của outbox chưa lập danh sách, cùng transaction
        RL->>DB: Chọn delivery pending tới hạn, FOR UPDATE SKIP LOCKED; đặt hạn giao lại rồi COMMIT
        RL->>RD: dispatch_event(event_id, handler)
    end
    RD->>W: dispatch_event
    W->>DB: BEGIN; khoá EventDelivery; bỏ qua nếu đã kết thúc hoặc chưa tới hạn retry; parse payload (lỗi thì chuyển failed); tăng interrupted_runs; COMMIT
    W->>DB: BEGIN; khoá lại EventDelivery, kiểm tra lại trạng thái
    W->>H: Gọi handler trong savepoint của cùng transaction
    W->>DB: Chuyển delivery completed, đặt interrupted_runs = 0, cùng tác động handler; COMMIT
```

### 1.1. Bảo đảm

| Bảo đảm | Có được nhờ |
|---|---|
| Sự kiện được lưu bền vững | Sự kiện ghi cùng transaction với dữ liệu nghiệp vụ trong PostgreSQL |
| Tự giao lại khi mất task hoặc worker chết | `EventDelivery` lưu từng cặp sự kiện–handler; relay quét lại các delivery chưa kết thúc tới hạn. Handler làm worker chết 3 lần liên tiếp thì delivery chuyển `failed` thay vì giao lại mãi (mục 1.3) |
| Không lặp tác động DB của cùng cặp sự kiện–handler | Khoá dòng delivery; chuyển `completed`/`rejected` cùng transaction với tác động của handler. Delivery không còn `pending` thì consumer bỏ qua |
| Một handler lỗi không ảnh hưởng handler khác | Mỗi cặp (sự kiện, handler) là một Celery task riêng |
| Có thể phát lại | Bảng outbox giữ sự kiện **90 ngày** **[Giả định · kiểm chứng: dung lượng bảng outbox trên staging trước go-live]**; lệnh `manage.py replay_events --type … --since …` |

### 1.1.1. PostgreSQL quyết định công việc còn chờ

- `publish()` chỉ ghi `OutboxEvent`. Relay lập danh sách handler theo `event_type` và `schema_version`, tạo `EventDelivery` với `UNIQUE(event_id, handler)` rồi ghi `deliveries_created_at` trong cùng transaction. Marker này chỉ có nghĩa đã lập danh sách, không có nghĩa handler đã chạy. Không có handler thì ghi marker và log để tránh quét mãi.
- Relay chạy độc lập với Celery Beat, quét mỗi giây. Với delivery `pending` có cả `next_attempt_at` và `next_dispatch_at` tới hạn, relay khoá dòng bằng `select_for_update(skip_locked=True)`, đặt `next_dispatch_at = now + 3 phút` **[Giả định · kiểm chứng: thời gian xử lý handler p99 trên staging]**, commit rồi mới enqueue. Không giữ transaction DB khi gọi broker. Chết trước enqueue, Redis mất task hay worker chết trước commit đều khiến delivery được giao lại sau hạn này.
- Consumer xử lý trong hai transaction, mỗi transaction khoá dòng delivery. Transaction 1 (ngắn) kiểm tra trạng thái, `next_attempt_at`, handler và class sự kiện còn đăng ký, parse payload, rồi tăng `interrupted_runs` và commit trước khi gọi handler. Parse lỗi thì chuyển `failed` ngay; bộ đếm đã chạm ngưỡng cũng chuyển `failed` (mục 1.3). Lý do: worker bị kill giữa lúc handler chạy thì không còn ghi được gì, bộ đếm phải có sẵn trong DB. Transaction 2 khoá lại, kiểm tra lại trạng thái và `next_attempt_at`, chạy handler và lưu kết quả. Task trùng chờ khoá rồi thấy kết quả đã commit thì kết thúc; task trùng tới giữa hai transaction có thể tăng bộ đếm thêm 1, nhưng kết quả lưu sau đó đặt bộ đếm về 0. Rủi ro chấp nhận: task trùng chen vào khe giữa hai transaction đúng lúc bộ đếm vừa lên ngưỡng làm delivery `failed` sớm một lần; khe rất ngắn, có cảnh báo và mở lại được bằng `retry_failed_events`. Rủi ro chấp nhận: gián đoạn không do handler (cold shutdown khi deploy, DB failover, worker hết bộ nhớ vì task khác) cũng tính là lần chạy dở; delivery chỉ chuyển `failed` khi đủ 3 lần liên tiếp trên cùng delivery. Hạn giao lại dài hơn `task_time_limit` 120 giây; timeout không cho phép bỏ qua khoá DB. Task tới muộn vẫn phải kiểm tra trạng thái hiện tại.
- Trạng thái delivery `completed`/`rejected` được ghi cùng transaction với kết quả xử lý; đây cũng là dấu "đã xử lý", không có bảng riêng. Retry dùng `attempts`, `next_attempt_at` trong PostgreSQL; không dùng bộ đếm Celery làm nguồn quyết định. `last_dispatched_at` chỉ phục vụ quan sát. Broker không hoạt động thì relay giữ công việc trong DB và thử tiếp, không tính là handler thất bại.
- Chỉ purge sự kiện quá 90 ngày đã có `deliveries_created_at` và mọi delivery đã `completed` hoặc `rejected`, cùng các delivery của sự kiện đó; giữ cả sự kiện và delivery `pending`/`failed` cho tới khi được xử lý. Cảnh báo công việc tồn đọng; không âm thầm xoá khi hết thời gian lưu thông thường.
- API công khai `shared.events.delivery_lag()` trả tuổi của công việc giao sự kiện đáng lẽ hạ tầng đã phải xử lý, trả `timedelta` (`0` khi không tồn đọng), lấy lớn nhất giữa: `now − occurred_at` của sự kiện chưa có `deliveries_created_at` (bảng outbox không có cột giờ ghi; `occurred_at` ghi cùng transaction, xem ticket [28](../../.scratch/backend-bootstrap/issues/28-outbox-operations-hardening/spec.md) về chênh lệch khi transaction dài), và `now − next_attempt_at` của delivery `pending` có `next_attempt_at ≤ now`. Không tính delivery `failed`, `completed`, `rejected` hay `pending` đang chờ tới lượt retry. Lý do: hàm đo tồn đọng của relay, broker và worker cho job T4 (mục 3.2); một handler lỗi đã tự dời `next_attempt_at` về tương lai, nên không làm T4 ngừng huỷ đơn. Delivery `failed` có cảnh báo riêng ([10-nfr.md](./10-nfr.md) mục 4).
- API công khai `shared.events.get_delivery_outcomes(event_id, handler_names)` trả `dict` có đủ mọi handler được yêu cầu, giá trị là trạng thái delivery pending/completed/rejected/failed hoặc `None` khi chưa có delivery (missing). Không suy thành công từ danh sách rỗng. Ẩn danh dùng required_handlers đã chốt trên ErasureRequest; replay không tự mở rộng yêu cầu đã hoàn tất.
- `replay_events` bảo đảm delivery tồn tại cho handler được chọn, có thể thêm handler mới vào sự kiện cũ; không xoá dấu đã xử lý hay chạy lại cặp đã hoàn tất. Cặp `failed` cần lệnh `retry_failed_events` để mở lại có chủ đích. Lệnh chọn sự kiện có `deliveries_created_at ≥ --since` (lúc relay lập danh sách, không phải lúc sự kiện xảy ra), bỏ qua sự kiện relay chưa lập danh sách; `--since` không ghi múi giờ hiểu theo `TIME_ZONE`; `--handler` tuỳ chọn phải đăng ký cho đúng `--type`. Mỗi lô khoá sự kiện để purge chạy đồng thời không xoá sự kiện giữa chừng. Thêm handler mới cho một loại sự kiện đã có: sau deploy chạy `replay_events --type <sự kiện> --since <lúc bắt đầu deploy>`, vì trong lúc deploy relay bản cũ có thể đã lập danh sách delivery mà không biết handler mới.

### 1.2. Không bảo đảm

**Thứ tự.** Handler không tự kiểm tra thứ tự. Với Đơn hàng, các transition do sự kiện kích hoạt tự đối chiếu trạng thái hiện tại ([02-backend-structure.md](./02-backend-structure.md) mục 7.7, [05-order-lifecycle.md](../business/05-order-lifecycle.md) mục 4.2): sự kiện cho bước đơn đã qua thì không làm gì, sự kiện tới sớm thì báo consumer thử lại sau, sự kiện mâu thuẫn với trạng thái đơn thì bị từ chối.

**Gửi ra hệ thống ngoài đúng một lần.** Chống trùng bằng transaction chỉ bao phủ tác động trong PostgreSQL. Email hoặc request nhà cung cấp phải chạy ngoài transaction và có cơ chế khôi phục riêng; email vẫn có thể trùng khi nhà cung cấp đã nhận nhưng worker chết trước lúc lưu `sent`. Việc tự khôi phục đòi hỏi PostgreSQL và relay/worker hoạt động trở lại; delivery `failed` cần người vận hành xử lý.

### 1.3. Retry và lỗi

Handler báo kết quả cho consumer bằng cách kết thúc bình thường hoặc ném exception. Consumer quyết định theo bảng sau, nên tác giả handler không phải tự bắt lỗi:

| Handler kết thúc bằng | Consumer làm gì |
|---|---|
| Chưa chạy: payload không parse được bằng class sự kiện, gồm `pydantic.ValidationError` (ví dụ thêm field bắt buộc vào `…V1` trái quy tắc ở mục 2) và mọi lỗi khác lúc parse (validator của class ném `KeyError`, payload không phải object) | Chuyển delivery `failed` ngay, không retry vì parse lần nào cũng lỗi như nhau: ghi `failed_at`, `last_error` là tên class lỗi (ví dụ `"ValidationError"`), log `ERROR` `event_delivery_failed` để Sentry cảnh báo. `ValidationError` thì log kèm `invalid_fields`: danh sách `{field, type}` đã bỏ trùng, `field` là tên field đã khai báo, không có input; lỗi khác thì log kèm traceback. Không gọi handler nên `attempts` và `interrupted_runs` giữ nguyên. Retry vẫn parse bằng class của `schema_version` cũ, nên phải đưa `…V1` về hình dạng cũ hoặc cho field mới là tuỳ chọn (mục 2) rồi mới mở lại bằng `retry_failed_events`. `ValidationError` ném ra **trong** handler vẫn là "Exception khác" |
| Chạy xong | Commit tác động handler và delivery `completed` |
| `RetryLater`, ví dụ `TransitionNotYetValid` | Rollback savepoint handler; delivery giữ `pending`; tăng `attempts`, ghi `last_error` và lưu lịch retry trên delivery trong transaction ngoài |
| `DomainError` khác, ví dụ `InvalidTransition` | Rollback savepoint handler nhưng chuyển delivery `rejected`, không retry. Log `WARNING` `event_rejected` kèm `event_type`, `handler`, `code` |
| Exception khác | Rollback savepoint handler; lưu retry như `RetryLater`. Nếu kết nối DB hỏng, transaction chạy handler rollback, `interrupted_runs` đã commit vẫn còn; relay giao lại theo hạn đã lưu |
| Không kết thúc (worker bị kill do quá `task_time_limit` hoặc hết bộ nhớ) | Transaction chạy handler rollback; `interrupted_runs` đã commit vẫn còn; relay giao lại theo hạn đã lưu |

- Lịch retry lưu trong DB: sau lần đầu, thử lại tối đa **5 lần**, chờ lần lượt 10 giây, 1 phút, 5 phút, 15 phút, 30 phút **[Giả định · kiểm chứng: tỉ lệ delivery `failed` trên staging và tháng đầu production]**. `attempts` đếm lỗi handler đã lưu được; task bị mất không tiêu hao lượt retry. Mỗi lỗi đặt lại cả `next_attempt_at` và `next_dispatch_at` theo lịch này.
- Lần chạy dở: mỗi lần consumer sắp gọi handler, bộ đếm `interrupted_runs` tăng 1 và commit trước; mọi kết quả lưu được (`completed`, `rejected`, lịch retry, `failed` do hết retry) đặt nó về 0 cùng transaction. Đã có **3** lần chạy dở liên tiếp (`MAX_INTERRUPTED_RUNS`) thì lần giao thứ 4 chuyển delivery `failed` mà không gọi handler: ghi `failed_at`, `last_error = "HandlerInterrupted"`, log `ERROR` `event_delivery_failed` kèm `interrupted_runs` để Sentry cảnh báo như khi hết retry. Với hạn giao lại 3 phút, delivery dừng sau khoảng 10 phút; hết bộ nhớ thì Celery giao lại ngay (`task_reject_on_worker_lost`) nên nhanh hơn. `attempts` không đổi ý nghĩa: chỉ đếm lỗi handler đã lưu được. Task mất do Redis không tới consumer nên không tăng bộ đếm. Lý do không dùng `soft_time_limit`: không bắt được worker hết bộ nhớ; không đếm số lần relay giao: task mất do Redis sẽ bị tính.
- Hết số lần retry: chuyển delivery `failed`, ghi `failed_at` và `last_error` trên chính dòng delivery, gửi cảnh báo Sentry. Áp dụng cả cho `RetryLater`. `manage.py retry_failed_events` khoá delivery `failed`, đặt lại `pending`, `attempts` và `interrupted_runs` về 0, lịch về hiện tại, ghi `retried_at`; relay giao lại. Giữ `failed_at`, `last_error` làm dấu vết tới lần lỗi sau. Chọn bằng `--event-id`, `--handler`, `--type` (kết hợp được) hoặc `--all`; không có bộ lọc thì lệnh từ chối. Không mở lại delivery của handler không còn đăng ký (log `WARNING` `event_delivery_retry_skipped`), vì nó sẽ kẹt `pending`. Không tự mở lại delivery `completed`/`rejected`.
- Relay lỗi kết nối Redis: sự kiện vẫn nằm trong outbox, relay tự thử lại.
- `enqueue_on_commit` cho công việc có bản ghi DB bắt lỗi kết nối/enqueue broker, ghi log và cảnh báo mà không biến request đã commit thành lỗi API. Không xoá hay đánh dấu hoàn tất khi enqueue thất bại; relay/job quét sẽ khôi phục. Lỗi lập trình hoặc dữ liệu không được âm thầm bỏ qua.

## 2. Danh mục sự kiện

Tên theo dạng `<module>.<event>`, có `schema_version`. Class nằm trong `events.py` của module phát.

**Nâng version.** Thêm field tuỳ chọn thì giữ version. Đổi tên, bỏ field hoặc đổi nghĩa một field thì tạo class `V2`, và publisher chỉ phát V2. Handler giữ cả `@handles(..., version=1)` và `version=2` cho tới khi outbox không còn sự kiện V1 (sau 90 ngày), rồi mới bỏ handler V1.

**Payload không chứa secret hay PII.** Payload chỉ mang ID, Mã đơn, số tiền và mã trạng thái. Handler cần dữ liệu nhạy cảm thì hỏi `contracts` của module sở hữu ngay lúc xử lý, ví dụ `identity.contracts.issue_password_reset_link(account_id)`. Lý do: outbox giữ sự kiện 90 ngày, có thể bị phát lại, và nằm trong mọi bản backup; token hay số điện thoại để ở đây sẽ sống lâu hơn và lộ rộng hơn bản gốc.

| Sự kiện | Phát bởi | Dữ liệu chính | Handler |
|---|---|---|---|
| `identity.customer-registered` v1 | identity | `account_id`, `language` | notifications: tạo EmailLog xác thực; task cấp link và gửi ngoài transaction |
| `identity.verification-email-requested` v1 | identity | `account_id` | Phát khi gửi lại email xác thực, hoặc khi đăng ký lại bằng email của Khách hàng chưa xác thực. notifications: như `customer-registered` |
| `identity.registration-attempted` v1 | identity | `account_id` | Phát khi đăng ký bằng email đã thuộc Tài khoản đã xác thực hoặc Tài khoản nội bộ (US-501 AC2). notifications: email báo chủ email có người vừa thử đăng ký, không kèm link hay mật khẩu |
| `identity.email-verified` v1 | identity | `account_id` | Phát mỗi khi email chuyển sang đã xác thực, kể cả qua đăng nhập Google. ordering: gắn các Đơn hàng có `contact_email` khớp (không phân biệt hoa thường) và `customer_id` null vào Tài khoản (BR-ORD-08) |
| `identity.password-reset-requested` v1 | identity | `account_id` | notifications: tạo EmailLog reset; task cấp link và gửi ngoài transaction |
| `identity.customer-erased` v1 | identity | `erasure_request_id` | ordering: ẩn danh Đơn hàng, xoá Giỏ hàng, gọi `shipping.contracts.redact_provider_payloads` và `payments.contracts.redact_provider_payloads` theo `reference`; promotions: ẩn danh `phone` trong lượt dùng Voucher; notifications: ẩn danh `to_address`. Mọi handler lấy đối tượng cần ẩn danh qua `identity.contracts.get_erasure_subject` |
| `ordering.order-placed` v1 | ordering | `order_code`, `payment_method`, `total` | Phát khi đơn **vào** `PLACED` (T2, T3). notifications: COD gửi "Đặt đơn thành công", online gửi "Thanh toán thành công" |
| `ordering.order-cancelled` v1 | ordering | `order_code`, `reason`, `refund_required`, `previous_status` | notifications: email "Đơn đã huỷ", trừ khi `previous_status = PENDING_PAYMENT` (T4, T5: BR-NTF-01) |
| `ordering.unexpected-payment-received` v1 | ordering | `order_code`, `amount` | Phát cùng lúc gắn cờ `unexpected_payment` (BR-PAY-05). notifications: email báo tiền sẽ được hoàn; với đơn đã huỷ thì báo thêm đơn đã hết hạn ([05](../business/05-order-lifecycle.md) mục 4.1) |
| `ordering.order-shipped` v1 | ordering | `order_code`, `tracking_code` | notifications: email "Đang giao" |
| `ordering.order-delivered` v1 | ordering | `order_code` | notifications: email "Đã giao" |
| `payments.payment-succeeded` v1 | payments | `reference`, `payment_id`, `amount`, `gateway` | Chỉ phát cho Thanh toán online. ordering: T3, lưu payment_id dưới khoá Order. Đơn còn `PENDING_PAYMENT` nhưng đã quá `expires_at` (job chưa kịp huỷ): thử giữ lại hàng nếu Số lượng bán được còn đủ; không đủ thì chạy T4 rồi xử lý như đơn đã huỷ. Cùng payment_id đã dùng cho đơn thì bỏ qua; khoản trả thêm hoặc tiền tới sau huỷ: request_refund với payment_id từ sự kiện và request_key ổn định, gắn cờ unexpected_payment và phát ordering.unexpected-payment-received (BR-PAY-05) |
| `payments.payment-failed` v1 | payments | `reference`, `payment_id`, `reason`, `amount_received` | ordering: ghi nhận, cho phép thử lại; `reason = amount_mismatch` thì request_refund với payment_id từ sự kiện, amount_received và key ổn định và gắn cờ `payment_amount_mismatch` (BR-PAY-04) |
| `payments.refund-recorded` v1 | payments | `reference`, `refund_id`, `amount` | notifications: email "Đã hoàn tiền"; ordering: chuyển Đổi trả có `refund_id` khớp sang `refunded`, không khớp thì bỏ qua |
| `shipping.shipment-created` v1 | shipping | `reference`, `provider_order_code` | ordering: T10, gọi `inventory.contracts.dispatch_stock` để xoá Hàng chờ xuất. Nếu đơn đã `CANCELLED`: gọi `shipping.contracts.request_shipment_cancellation` và gắn cờ `shipment_after_cancel` |
| `shipping.shipment-creation-failed` v1 | shipping | `reference`, `reason` | ordering: gắn cờ `shipment_failed`, đơn giữ `PACKING` |
| `shipping.shipment-delivered` v1 | shipping | `reference`, `delivered_at` | ordering: T11 |
| `shipping.shipment-returned` v1 | shipping | `reference` | ordering: T12 |
| `shipping.shipment-exception` v1 | shipping | `reference`, `provider_status` | ordering: gắn cờ `shipment_exception`, đơn giữ `SHIPPING` cho tới khi Staff xử lý (T14) |

T1 (đơn online vào `PENDING_PAYMENT`) không phát sự kiện nào; Người mua chỉ nhận email khi thanh toán thành công. Không còn sự kiện `ordering.order-paid`: `order-placed` của đơn online đã mang ý nghĩa này.

Thanh toán COD (`start_cod_payment`, `record_cod_collected`, `cancel_cod_payment`) **không** phát sự kiện, vì `ordering` là bên gọi nên đã biết kết quả. Nếu `record_cod_collected` phát `payments.payment-succeeded`, handler của `ordering` sẽ thấy đơn `DELIVERED` không ở `PENDING_PAYMENT` và tạo Hoàn tiền nhầm theo BR-PAY-05.

## 3. Celery

### 3.1. Queue

| Queue | Dùng cho | Worker |
|---|---|---|
| `default` | Job theo lịch | Chung |
| `events` | `dispatch_event` | Chung |
| `emails` | Gửi email | Chung; tách riêng khi tải lớn |
| `integrations` | Gọi API VNPay, MoMo, GHN: Đối soát, tạo và huỷ Vận đơn (tạo và huỷ Vận đơn luôn chạy nền, xem [06-integrations.md](./06-integrations.md) mục 4) | Riêng, **đúng 1 instance** (`worker-integrations`, [09](./09-deployment-aws-target.md) mục 2). Celery tính `rate_limit` theo từng worker instance, nên chỉ khi có đúng 1 instance thì `rate_limit` của từng task mới là giới hạn chung, không vượt rate limit của nhà cung cấp. Không scale queue này bằng cách thêm instance |

Ở local, một worker nghe cả 4 queue ([08](./08-local-development.md) mục 7); vẫn chỉ có 1 instance nên quy tắc trên giữ nguyên.

Lần gọi nhà cung cấp ngay trong request API (tạo link thanh toán, báo giá GHN) không đi qua queue `integrations`, nên `rate_limit` không áp cho chúng. Tần suất của các lần gọi này được giới hạn gián tiếp bằng throttle theo Người mua ([05-auth-security.md](./05-auth-security.md) mục 5).

Code nghiệp vụ đẩy task bằng `shared.tasks.enqueue_on_commit`, không gọi `.delay()` trực tiếp ([13-python-django-coding-style.md](./13-python-django-coding-style.md) mục 4).

### 3.2. Lịch job (Celery Beat, lưu bằng `django-celery-beat`)

| Job | Tần suất | Module | Liên quan |
|---|---|---|---|
| `ordering.cancel_expired_pending_orders` | Mỗi phút | ordering | T4. Bỏ qua lượt chạy (log `WARNING` `cancel_skipped_delivery_backlog`) khi `shared.events.delivery_lag()` quá **60 giây**. Lý do: sau khi Redis, relay hoặc worker lỗi, `payments.payment-succeeded` còn chờ giao; nếu T4 chạy trước thì đơn đã trả đúng hạn bị huỷ và phải Hoàn tiền ([01](./01-system-context.md) mục 4). Không giới hạn số lượt bỏ: huỷ nhầm đơn đã trả tiền tệ hơn giữ hàng lâu thêm. Bỏ lượt liên tục quá **15 phút** thì báo Sentry `cancel_skipped_too_long`, vì lúc này Giữ hàng quá hạn đang khoá Số lượng bán được |
| `payments.reconcile_pending_payments` | Mỗi 5 phút | payments | T3, ADR 0005; Payment quá hạn link mà chưa thanh toán thì chuyển `expired` |
| `shipping.reconcile_shipments` | Mỗi 15 phút | shipping | T11, T12; chỉ hỏi GHN về Vận đơn không có cập nhật trong 6 giờ, tối đa 500 mỗi vòng theo mặc định ([06](./06-integrations.md) mục 4); query mã shop cho requested/creation_unknown hết lease, không retry create mù; thử huỷ lại cancel_requested quá 15 phút |
| `ordering.complete_delivered_orders` | Mỗi giờ | ordering | T13 |
| `ordering.compute_best_sellers` | Mỗi ngày 02:00 | ordering | BR-CAT-12; ghi kết quả vào `catalog` qua `catalog.contracts.set_best_seller_counts` |
| `ordering.purge_expired_guest_carts` | Mỗi ngày 03:00 | ordering | BR-CRT-02 |
| `notifications.recover_pending_emails` | Mỗi phút | notifications | Đẩy lại EmailLog `queued` tới hạn hoặc `sending` hết lease; xem mục 4 |
| `notifications.purge_old_emails` | Mỗi ngày 04:15 | notifications | EmailLog `sent`, `failed`, `cancelled` tạo quá 90 ngày: xoá `to_address` và `context`, giữ dòng để thống kê ([06-compliance.md](../business/06-compliance.md) mục 5) |
| `shared.purge_old_outbox_events` | Mỗi ngày 03:30 | shared | Chỉ xoá sự kiện quá 90 ngày đã hoàn tất mọi delivery; xoá delivery tương ứng |
| `shared.purge_idempotency_keys` | Mỗi ngày 03:45 | shared | Chỉ xoá key completed quá 24 giờ; giữ in_progress chưa rõ kết quả |
| `identity.purge_refresh_replays` | Mỗi phút | identity | Xoá ciphertext replay hết hạn; endpoint vẫn kiểm tra hạn và thu hồi trước decrypt, không chờ job |
| `identity.purge_expired_tokens` | Mỗi ngày 04:00 | identity | Refresh token, reset token hết hạn |
| `identity.reconcile_erasure_requests` | Mỗi phút | identity | Chỉ hoàn tất processing khi mọi handler bắt buộc completed; thiếu/failed/rejected thì giữ trạng thái và cảnh báo |
| `payments.recover_payment_initializations` | Mỗi phút | payments | Khôi phục prepared/unknown hết lease bằng cùng Payment và mã nhà cung cấp; không ghi đè IPN (06 mục 3.1) |

Tần suất "mỗi phút" của các job khôi phục là **[Giả định · kiểm chứng: tải DB của các truy vấn quét trên staging]**.

Mọi job đều **idempotent** và xử lý theo lô (ví dụ 200 đơn mỗi lần) để chạy lại an toàn.

**Nguồn lịch job.** Lịch ở bảng trên được khai báo trong code (`config/celery.py`), là nguồn chuẩn. Lệnh `manage.py sync_beat_schedule` tạo hoặc cập nhật `PeriodicTask` của `django-celery-beat` theo code, **tắt** (không xoá) job có trong DB mà không còn trong code và ghi log từng thay đổi. Lệnh idempotent, chạy sau mỗi lần `migrate`: ở local qua service `migrate` của `make up`, `make migrate` và `make db-reset` ([08](./08-local-development.md) mục 3), trên AWS trong cùng task migration ([09](./09-deployment-aws-target.md) mục 4). Không sửa lịch bằng tay trong DB, vì lần `sync_beat_schedule` sau sẽ ghi đè theo code.

Job Đối soát (`reconcile_pending_payments`, `reconcile_shipments`) chỉ quét rồi đẩy mỗi Thanh toán hoặc Vận đơn một task con lên queue `integrations`, không tự gọi nhà cung cấp trong task của job. Một lô 200 lần gọi, mỗi lần tới 13 giây (06 mục 1), sẽ vượt `task_time_limit` 120 giây.

### 3.3. Cấu hình quan trọng

| Thiết lập | Giá trị | Lý do |
|---|---|---|
| `task_acks_late` | `True` | Worker chết giữa chừng thì task được giao lại |
| `task_reject_on_worker_lost` | `True` | Như trên |
| `worker_prefetch_multiplier` | `1` | Không giữ nhiều task trong một worker |
| `task_time_limit` | 120 giây | Chặn task treo |
| `CELERY_TASK_ALWAYS_EAGER` | `True` chỉ trong `settings/test.py` | Test chạy đồng bộ |
| Kết quả task | Không lưu (`task_ignore_result = True`) | Không cần result backend |
| Redis `maxmemory-policy` | `noeviction` | Redis vừa là broker vừa là cache; nếu Redis tự đẩy key ra khi đầy thì có thể mất task. Vì vậy mọi key cache phải có TTL |

Các cấu hình ack hỗ trợ giao lại task nhưng không thay thế trạng thái công việc trong PostgreSQL; tác vụ vẫn phải chạy lại an toàn. Tham khảo [tài liệu Celery về task và acks_late](https://docs.celeryq.dev/en/stable/userguide/tasks.html).

### 3.4. Giám sát relay và job theo lịch

Dùng **Sentry Cron Monitors**, chỉ bật ở staging và production:

- Mỗi job ở mục 3.2 gửi check-in `in_progress` khi bắt đầu và `ok` hoặc `error` khi kết thúc, `monitor_slug` là tên job. Lịch của monitor lấy từ cùng khai báo trong code.
- Relay gửi check-in mỗi phút từ vòng lặp chính.
- Sentry cảnh báo khi check-in trễ quá **3 phút** hoặc job kết thúc lỗi. Lúc deploy beat ngừng vài chục giây ([09](./09-deployment-aws-target.md) mục 4), ngắn hơn ngưỡng này.

Lý do không ghi heartbeat vào DB rồi để một job Beat kiểm tra: khi chính Beat chết thì không còn ai báo. Sentry nằm ngoài hệ thống cần giám sát.

## 4. Email: hàng đợi bền vững trong PostgreSQL

- Handler gọi service tạo `EmailLog(status="queued")` cùng transaction với việc chuyển delivery `completed`, `UNIQUE(event_id, template)`; lưu ID nguồn (`account_id`, `order_code` hoặc `refund_id`) để dựng lại nội dung. `context` chỉ cho phép snapshot `amount`, `currency` từ sự kiện nếu template cần số tiền của đúng lần phát sinh, không phụ thuộc outbox còn giữ hay không. Không lưu token, link bí mật, raw payload hay HTML chứa PII trong hàng đợi. Sau commit chỉ enqueue `send_email(email_log_id)` để giảm độ trễ; DB là nguồn công việc còn chờ.
- Task mở transaction ngắn để khoá EmailLog, bỏ qua `sent`/`failed`/`cancelled`, `queued` chưa tới `next_attempt_at` hoặc `sending` có lease chưa hết; nhận lease bằng `lease_token` mới, `lease_expires_at = now + 3 phút` **[Giả định · kiểm chứng: thời gian gửi SES p99 trên staging]**, đặt `sending` và tăng `attempts`. Sau commit mới lấy dữ liệu qua contracts, cấp token xác thực/reset nếu cần, render và gửi email ngoài transaction. Link bí mật chỉ tồn tại trong bộ nhớ lúc gửi.
- Ghi kết quả trong transaction ngắn, chỉ khi `lease_token` còn khớp. Thành công → `sent`; lỗi → `queued` với `next_attempt_at` theo lịch 10 giây, 1 phút, 5 phút, 15 phút, 30 phút; sau lần gửi thứ 6 thất bại → `failed` và cảnh báo Sentry. Claim sau lease hết hạn vẫn tính một lần gửi để giới hạn các lần worker chết; quá giới hạn chuyển `failed` để kiểm tra thủ công. Timeout gửi phải ngắn hơn lease và task time limit.
- `recover_pending_emails` quét `queued` tới hạn và `sending` hết lease để đẩy lại task. Nếu task quét hoặc task gửi mất trong Redis, lần quét tiếp theo vẫn tìm thấy công việc. Không cần phát lại sự kiện đã xử lý. Lệnh `manage.py retry_failed_emails` mở lại các email `failed` được chọn, đặt lại bộ đếm, ghi log thao tác; không mở lại email `sent`/`cancelled`.
- `purge_old_emails` (mục 3.2) đặt `to_address = ''` và `context = {}` cho EmailLog đã kết thúc quá 90 ngày; không đụng email `queued`/`sending`. Email `failed` đã purge không mở lại được bằng `retry_failed_emails` vì không còn địa chỉ nhận.
- Nhà cung cấp đã nhận nhưng chưa lưu `sent` thì lần khôi phục có thể gửi trùng; `UNIQUE(event_id, template)` chỉ chống tạo hai EmailLog. Dùng Message-ID ổn định theo EmailLog để tra cứu, không coi đây là bảo đảm nhà cung cấp chống trùng.
- Trước khi gửi, kiểm tra nguồn còn hợp lệ: chuyển `cancelled` (chỉ khi lease còn khớp) cho email xác thực khi tài khoản đã xác thực, reset khi tài khoản không còn hoạt động hoặc nguồn không còn hợp lệ, và trường hợp không còn địa chỉ nhận; `customer-erased` chuyển email chưa gửi của đối tượng sang `cancelled`, xoá `to_address` và vô hiệu lease. Task lấy lại dữ liệu mới ngay trước khi gửi; việc gửi đã bắt đầu ở nhà cung cấp không thể thu hồi bằng transaction DB.

## 5. Kịch bản kiểm thử

Test đặt ở `shared/events/tests/` và `test_handlers_<chủ đề>.py` của module; nguyên tắc chung ở [12-testing-strategy.md](./12-testing-strategy.md) mục 2.3.

- Consumer (mục 1.3), test bằng handler giả: khoá delivery; thành công commit tác động và completed cùng nhau. RetryLater/exception rollback savepoint handler, delivery giữ pending, lưu bộ đếm, last_error và lịch DB; DomainError khác rollback savepoint nhưng chuyển rejected, không retry. Payload không parse được (ValidationError hoặc lỗi khác lúc parse) chuyển failed ngay, không gọi handler, attempts và interrupted_runs giữ nguyên; lỗi ném trong handler, kể cả ValidationError, vẫn retry theo lịch.
- Relay: tạo từng cặp event–handler và marker deliveries_created_at nguyên tử, không tạo trùng khi hai relay cùng chạy. Relay không phụ thuộc Beat. Chết sau khi lưu hạn giao lại nhưng trước enqueue: sau hạn, delivery được giao tiếp.
- Redis đã nhận rồi mất task hoặc worker chết trước commit: relay giao lại delivery pending tới hạn; tác động cuối cùng chỉ commit một lần. Test task giao trùng chạy đồng thời trên PostgreSQL thật; consumer phải kiểm tra trạng thái và next_attempt_at.
- Handler hết retry: delivery chuyển failed, ghi failed_at và last_error; retry_failed_events mở lại đúng cặp, reset lịch/bộ đếm và ghi retried_at; không mở lại completed/rejected. Retry dùng lịch DB, mất task không làm reset số lỗi handler.
- Handler chạy dở (worker bị kill) 3 lần liên tiếp: lần giao thứ 4 chuyển failed với last_error HandlerInterrupted và log ERROR, không gọi handler, attempts không đổi. Kết quả lưu được (completed, rejected, lịch retry, failed do hết retry) đặt interrupted_runs về 0. Task mất do Redis không tăng interrupted_runs hay attempts.
- Purge không xoá sự kiện có delivery pending/failed dù quá 90 ngày; chỉ xoá sự kiện đủ tuổi đã kết thúc mọi delivery. Replay không xoá dấu đã xử lý; thêm handler mới thì tạo delivery mới được.
- Email: handler commit EmailLog queued rồi process chết trước enqueue; job quét tìm lại và gửi được dù delivery đã completed. Mất task quét thì lần Beat tiếp theo vẫn phục hồi.
- Hai task cùng gửi một EmailLog: chỉ một task nhận lease; kết quả lease cũ không ghi đè lease mới. Nhà cung cấp nhận rồi worker chết trước lưu sent: cho phép gửi lại, không khẳng định chỉ gửi một email.
- Email queued lỗi theo backoff, sending hết lease được khôi phục; quá giới hạn chuyển failed và cảnh báo; retry_failed_emails chỉ mở lại failed được chọn. Email sent/cancelled không gửi lại. Email xác thực/reset không còn hợp lệ bị bỏ qua; không lưu token/link bí mật trong outbox hay EmailLog.
- customer-erased huỷ email chưa gửi, xoá người nhận và vô hiệu lease; worker đang giữ lease cũ không ghi đè kết quả sau đó.
- Job Celery Beat (mục 3.2): chạy 2 lần liên tiếp cho ra cùng kết quả.
- `sync_beat_schedule`: DB rỗng thì tạo đủ job theo code; chạy lần hai không đổi gì; job có trong DB nhưng không còn trong code bị tắt, không bị xoá; tần suất trong DB khác code thì được sửa theo code.
- `purge_old_emails`: chỉ xoá `to_address` và `context` của EmailLog `sent`/`failed`/`cancelled` quá 90 ngày, ở cả hai phía của mốc (time-machine); không đụng `queued`/`sending`; chạy lại không đổi gì.

| Kịch bản | Kỳ vọng |
|---|---|
| `delivery_lag()` với delivery không do hạ tầng chậm | Delivery `failed`, `completed`, `rejected` và `pending` có `next_attempt_at` trong tương lai không được tính; một handler lỗi đang chờ retry 30 phút không làm T4 bỏ lượt. Delivery `pending` tới hạn và sự kiện chưa có `deliveries_created_at` thì được tính (mục 1.1.1) |
| Xoá dữ liệu có một handler chưa xong, failed, rejected hoặc chưa có delivery | ErasureRequest giữ processing, completed_at null; không coi danh sách delivery rỗng là thành công |
| Tất cả handler ẩn danh bắt buộc completed | Job hoàn tất một lần; gọi lại không phát thêm sự kiện; subject còn lấy được trong processing và được làm sạch sau hoàn tất |

**Payload sự kiện không chứa secret hay PII** (mục 2): `backend/tests/test_event_payloads.py` duyệt mọi class `DomainEvent` đã đăng ký và fail nếu tên field **chứa** một từ trong danh sách cấm (`email`, `phone`, `address`, `name`, `token`, `password`) hoặc kết thúc bằng `_url`, nên `contact_name` hay `reset_token` cũng bị chặn. Test này chỉ bắt lỗi theo tên field; reviewer vẫn phải đọc payload của mọi sự kiện mới. Test đặt ở `backend/tests/` (không thuộc `root_packages`) vì cần nhìn thấy sự kiện của mọi module.
