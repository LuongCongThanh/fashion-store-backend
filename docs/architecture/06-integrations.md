# 06. Tích hợp bên ngoài

> Trạng thái: **Đã chốt cho MVP** ([quy ước](../../README.md#trạng-thái-tài-liệu)). Quyết định nền tảng: [ADR 0005](../adr/0005-provider-adapters-fake-gateways.md).
> Adapter mỏng bằng `httpx` để tự sở hữu hợp đồng và kiểm thử tích hợp; không dùng SDK bên thứ ba. Mục **[Cần xác minh]** là điều kiện nghiệm thu, chưa được kiểm chứng trên sandbox.

## 1. Mô hình adapter

```mermaid
classDiagram
    class PaymentGateway {
        <<interface>>
        +create_payment_url(input) PaymentCreationResult
        +verify_ipn(request_data) PaymentObservation
        +query_transaction(payment) PaymentObservation
    }
    PaymentGateway <|.. VnpayGateway
    PaymentGateway <|.. MomoGateway
    PaymentGateway <|.. FakeGateway

    class ShippingProvider {
        <<interface>>
        +quote(input) ShippingQuoteResult
        +create_shipment(input) ShipmentCreationResult
        +get_status(provider_order_code) ShipmentObservation
        +find_by_client_code(shop_id, client_order_code) LookupResult
        +cancel_shipment(provider_order_code) CancelResult
    }
    ShippingProvider <|.. GhnProvider
    ShippingProvider <|.. FakeShippingProvider
```

Chọn adapter bằng cấu hình:

| Biến môi trường | Local (mặc định) | Nghiệm thu với sandbox | AWS |
|---|---|---|---|
| `PAYMENT_PROVIDER_VNPAY` | `fake` | `vnpay` (sandbox) | `vnpay` |
| `PAYMENT_PROVIDER_MOMO` | `fake` | `momo` (sandbox) | `momo` |
| `SHIPPING_PROVIDER` | `fake` hoặc `ghn` (sandbox, gọi ra được từ local) | `ghn` (sandbox) | `ghn` |
| `FAKE_PROVIDERS_ENABLED` | `true` | `false` | `false` (staging bật tạm khi test tải) |

`FAKE_PROVIDERS_ENABLED`:

- Quyết định có đăng ký trang Fake Gateway và lệnh giả lập GHN hay không.
- Bật ở local và trong `settings/test.py` (flow test gọi IPN qua Fake Gateway), không phụ thuộc `settings.local`.
- Chọn adapter `fake` khi cờ tắt → Django báo lỗi lúc khởi động.
- Staging chỉ bật tạm khi test tải bằng k6 ([12-testing-strategy.md](./12-testing-strategy.md) mục 9). `settings/production.py` từ chối khởi động nếu cờ bật khi `APP_ENV = production`.

Mọi adapter thật: timeout (kết nối 3 giây, đọc 10 giây), retry có giới hạn cho lỗi mạng (không retry tạo giao dịch nếu không chắc idempotent), log có `request_id`, che dữ liệu nhạy cảm.

Return URL:

- Backend dựng từ STOREFRONT_ORIGIN cấu hình và path /payment/return; API công khai không nhận URL này.
- Lưu URL đã dựng trong Payment.creation_input để retry cùng payload kể cả khi cấu hình domain đổi.
- Adapter vẫn nhận return_url nội bộ tin cậy; callback/IPN URL là cấu hình riêng.
- Trang return chỉ đọc trạng thái qua BFF, không xác nhận tiền từ query string (05 mục 6).

### 1.1. Hợp đồng kết quả adapter

- DTO là Pydantic frozen, cấm field lạ, chỉ dùng kiểu nội bộ dưới đây; không trả ORM model hoặc raw response cho service làm logic nghiệp vụ.
- Thời gian UTC; tiền/số lượng là số nguyên; giới hạn string theo 03.
- Raw payload đã xác thực chỉ chuyển riêng tới nơi ghi Event, không vào log/DTO public.
- Input versioned theo 03 mục 6.1/7.1; không đọc lại cấu hình để thay payload khi retry.

| DTO | Field bắt buộc / giá trị hợp lệ |
|---|---|
| `PaymentCreationResult` | `outcome` = ready/rejected/unknown; `redirect_url` chỉ có và bắt buộc khi ready, đã qua allowlist; `provider_code` string, `retryable` boolean. rejected = chắc chắn không tạo được giao dịch; timeout/mất response là unknown |
| `PaymentObservation` | `provider`, `merchant_scope` (ID cấu hình merchant/môi trường, không secret), `reference` (provider_txn_ref), `provider_transaction_id` nullable, `outcome` = pending/authorized/captured/failed/expired/not_found/unknown; `reported_amount` integer ≥ 0 hoặc NULL, `captured_amount` integer > 0 chỉ khi captured, NULL ở kết quả khác; `currency` = VND; `provider_codes` object có đúng các mã liệt kê ở mục 1.2; `occurred_at` timestamp hoặc NULL; `evidence` = verified_ipn/verified_query. Callback chưa xác thực không tạo DTO nghiệp vụ; query chỉ verified khi đã kiểm tính xác thực theo protocol và khớp merchant/reference |
| `ShippingQuoteResult` | `fee` integer ≥ 0, `source` = carrier/fallback, `reason` nullable (bắt buộc khi fallback), `request_fingerprint` string SHA-256; phí Người mua trả vẫn do ordering tính |
| `ShipmentCreationResult` | `outcome` = created/rejected/unknown, `provider_order_code` bắt buộc chỉ khi created; `fee` integer ≥ 0 hoặc NULL, `provider_code` string. Service chỉ phát creation-failed cho rejected |
| `ShipmentObservation` | `provider_order_code`, `reference`, `provider_status` string, `occurred_at` timestamp hoặc NULL; `mapped_status` thuộc bảng mục 4.1 hoặc unknown; `evidence` = verified_webhook/verified_query. Mã chưa biết là unknown, giữ trạng thái hiện tại và cảnh báo |
| `LookupResult` | `outcome` = found/not_found/unknown; `shipment` (ShipmentObservation) bắt buộc chỉ khi found. not_found không tự cấp phép retry create nếu chưa nghiệm thu tính nhất quán truy vấn |
| `CancelResult` | `outcome` = cancelled/rejected/unknown, `provider_code` string. rejected = provider từ chối, không tự biến Vận đơn thành cancelled; timeout là unknown, giữ ý định huỷ để đối soát |

- `provider_codes`: VNPay chỉ gồm `response_code`, `transaction_status`; MoMo chỉ gồm `result_code`; giá trị là string để giữ mã gốc.
- `provider_transaction_id` bắt buộc khi captured.
- `reference` ở DTO Payment là mã gửi gateway, không phải `Payment.reference` (Mã đơn); adapter resolve đúng Payment trước khi service đọc Mã đơn.

| Lỗi / kết quả | Quyết định của service |
|---|---|
| Chữ ký/merchant/reference/currency không hợp lệ | Không đổi tiền/trạng thái hoặc phát sự kiện; phản hồi theo mục 1.3, cảnh báo metadata không nhạy cảm |
| Timeout, mất response, body không parse/validate được | Unknown; không suy ra failed/not_found, không retry tạo mù |
| 429 hoặc 5xx ở thao tác đọc | Retry hữu hạn, tôn trọng Retry-After hợp lệ; hết ngân sách để job vòng sau xử lý |
| 4xx từ chối nghiệp vụ có ý nghĩa chắc chắn | rejected theo mapping của adapter; 4xx không nhận diện vẫn unknown |
| captured đã xác thực | Áp mục 1.2 dưới khoá Payment; HTTP ACK không đồng nghĩa Order đã PLACED |

Ngân sách mặc định **[Giả định · kiểm chứng: độ trễ thực tế khi nghiệm thu sandbox, mục 8]**, không thay thế lịch retry handler ở 07:

- Query/cancel: tối đa 3 lần HTTP mỗi lượt task, chờ 1 giây rồi 3 giây; timeout tổng < lease.
- Create: một lần mỗi lượt; mọi lần tạo lại phải qua query và điều kiện idempotency đã nghiệm thu.
- Báo giá GHN: deadline tổng 3 giây, không nhân thành nhiều lần retry; hết hạn dùng fallback.

### 1.2. Xác nhận tiền và chống trùng

Trình tự chung cho IPN và Đối soát: parse giới hạn kích thước → xác thực → đối chiếu merchant/reference/currency → tạo PaymentObservation → transaction khoá Payment → tạo/kiểm tra PaymentEvent → cập nhật tiền/trạng thái và outbox → commit → ACK.

- Không gọi query/gateway trong transaction.
- Payload sai chữ ký không ghi như sự kiện tin cậy; không coi `reported_amount` là tiền đã nhận.

| Provider / kết quả | Outcome nội bộ / tác động tiền |
|---|---|
| VNPay `vnp_ResponseCode = 00` **và** `vnp_TransactionStatus = 00` | captured; `vnp_Amount` phải chia hết cho 100, đổi về VND rồi đối chiếu. Khớp thì succeeded, ghi paid_at; sai số tiền nhưng thật sự captured thì failed/amount_mismatch, lưu đúng tiền thực nhận để ordering tạo Hoàn tiền |
| VNPay chưa hoàn tất hoặc trạng thái đảo/hoàn/nghi ngờ | Mapping rõ theo phiên bản API; chưa chứng minh capture thì pending/unknown, không tăng amount_received hay tự hoàn tiền. Chỉ failed cho mã thất bại cuối đã xác minh |
| MoMo `resultCode = 0` | captured với đúng sản phẩm thanh toán đã nghiệm thu; kiểm partnerCode/orderId/requestId/currency/amount trước khi áp cùng quy tắc số tiền |
| MoMo `resultCode = 9000` | authorized, chưa coi là captured; không PLACED hoặc tạo Hoàn tiền chỉ từ thông báo này. MVP không bật auth/capture hai bước nếu chưa đặc tả và nghiệm thu bước capture |
| MoMo thất bại/hủy, pending hoặc mã chưa nhận diện | failed/pending/unknown theo bảng mã của đúng sản phẩm tích hợp, không dùng amount trong thông báo làm amount_received |

Nguồn protocol: [VNPay PAY](https://sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay.html), [MoMo notification](https://developers.momo.vn/v3/docs/payment/api/result-handling/notification/). Fixture chữ ký, bảng mã và ACK ghi rõ phiên bản/sản phẩm đã nghiệm thu; mã chưa có mapping không được coi là thành công.

- `amount_received` được **gán** số captured đã xác nhận, không cộng dồn theo số callback/query.
- Đã xác nhận capture thì pending/failed tới muộn không xoá tiền hoặc hạ succeeded.
- Capture tới muộn cho Payment chưa có tiền vẫn được xử lý dù trước đó expired/cancelled/failed; ordering quyết định giữ đơn hay Hoàn tiền theo lifecycle.
- Payment đã có capture mà nhận captured khác transaction ID hoặc khác số tiền: lưu observation riêng để điều tra, giữ khoản đã xác nhận, cảnh báo `PROVIDER_RESULT_CONFLICT`; không cộng thêm, thay tiền hoặc tạo Hoàn tiền cho khoản chưa xác định. Đây không phải cách biểu diễn nhiều lần thử; lần thử khác phải có Payment khác.
- `provider_event_id = "obs:v1:" + sha256(canonical_json(observation_identity))`:
  - Canonical JSON UTF-8, key sort, separators không khoảng trắng, không float.
  - Identity gồm đúng `provider`, `merchant_scope`, `reference`, `provider_transaction_id` (hoặc NULL), `outcome`, `reported_amount`, `captured_amount`, `currency`, `provider_codes`. Không gồm source IPN/query, thời gian query/response, chữ ký hoặc message.
  - Key ≤ 128; không giả định provider có event ID độc lập.
- Identity chứa outcome/mã/số tiền nên query pending không che captured về sau; IPN/query cùng nội dung chuẩn hoá trùng key. Observation khác key vẫn qua khoá và quy tắc tiền trên, nên không phát lại PaymentSucceeded/PaymentFailed(amount_mismatch) cho cùng kết quả tiền. UNIQUE chỉ chống trùng quan sát, không thay idempotency của tác động nghiệp vụ.

### 1.3. Phản hồi webhook

- Webhook là ngoại lệ của error envelope 04.
- Chỉ ACK kết quả đã commit hoặc duplicate đã commit; DB lỗi/rollback không trả mã xác nhận thành công.
- Parse tối thiểu để kiểm chữ ký trước khi tin dữ liệu; giới hạn kích thước; không log query string VNPay hoặc body/header chứa chữ ký/token.

| Trường hợp | VNPay PAY | MoMo | GHN |
|---|---|---|---|
| Đã lưu/apply hoặc đã ghi pending/failed hợp lệ | HTTP 200, RspCode 00; captured sai số tiền dùng 04 sau khi lưu observation và tiền đúng | HTTP 204 sau commit | HTTP 200 sau commit |
| Duplicate đã commit | HTTP 200, RspCode 02 (hoặc 04 cho captured sai tiền đã ghi) | HTTP 204, không xử lý tiền lại | HTTP 200, không đổi terminal/phát lại sự kiện |
| Sai chữ ký/credentials | HTTP 200, RspCode 97 | HTTP 400, không mutation | HTTP 401/403 theo cơ chế credentials đã nghiệm thu, không mutation |
| Merchant/reference không khớp Payment/Shipment | HTTP 200, RspCode 01, không tạo PaymentEvent mồ côi | HTTP 400, không mutation | HTTP 400, không tạo ShipmentEvent mồ côi |
| Parse/schema/currency không hợp lệ | HTTP 400; không gán thành công | HTTP 400 | HTTP 400 |
| DB lỗi hoặc commit chưa thành công | HTTP 500 (không RspCode 00/02); lỗi xử lý dùng RspCode 99 nếu protocol phiên bản đã nghiệm thu yêu cầu HTTP 200 | HTTP 500, không 204 | HTTP 500, không 200 |

- Đây là chính sách của merchant; hành vi retry thực tế của MoMo/GHN và cơ chế xác thực GHN phải nghiệm thu trước production.
- Không trông chờ provider luôn gửi lại callback; Đối soát vẫn bắt buộc.
- ACK cho giao dịch thất bại chỉ xác nhận đã tiếp nhận kết quả, không phải đã thu tiền.
- IPN/Đối soát cùng pipeline nghiệp vụ; phản hồi HTTP chỉ thuộc adapter webhook.

## 2. VNPay

| Việc | Cách làm |
|---|---|
| Tạo thanh toán | Dựng URL có tham số `vnp_*`, ký **HMAC-SHA512** bằng `vnp_HashSecret`; `vnp_TxnRef` = `payments_payment.provider_txn_ref` (mỗi lần thử sinh mã mới); `vnp_Amount` = số tiền × 100 theo đặc tả VNPay |
| Hết hạn | `vnp_ExpireDate` = `payments_payment.expires_at` do `ordering` truyền: lúc đặt đơn + `PAYMENT_LINK_TTL` (phút thứ 10), giống nhau cho mọi lần thử. Link hết hạn sớm hơn Giữ hàng (phút thứ 15) 5 phút để IPN muộn vẫn kịp T3. Một vòng Đối soát (mỗi 5 phút) có thể kịp trước phút 15 nhưng không bảo đảm ([01](./01-system-context.md) mục 4) |
| IPN | `GET /api/v1/webhooks/vnpay/ipn`: xác thực, resolve Payment, ánh xạ **cả** response code/transaction status theo mục 1.2 trước khi kết luận tiền đã nhận; chống trùng dưới khoá Payment, commit rồi phản hồi theo mục 1.3. Chỉ captured sai tiền mới phát amount_mismatch và tạo nghĩa vụ Hoàn tiền |
| Đối soát | API truy vấn giao dịch (`querydr`) cho Payment `pending` quá 2 phút. Quá `expires_at` mà cổng báo chưa thanh toán thì chuyển `expired` |
| Hoàn tiền | MVP: Staff thao tác thủ công trên trang quản trị VNPay (BR-REF-03) |

## 3. MoMo

| Việc | Cách làm |
|---|---|
| Tạo thanh toán | Gọi API tạo giao dịch, ký **HMAC-SHA256** bằng `secretKey`, nhận `payUrl` |
| Hết hạn | Đặt hạn link theo cùng `expires_at` (phút thứ 10 kể từ khi đặt đơn) nếu API MoMo cho phép **[Cần xác minh tham số hạn link của MoMo]**. Nếu không, Đối soát chuyển Payment sang `expired` khi quá `expires_at`; tiền về muộn xử lý theo BR-PAY-05 |
| IPN | `POST /api/v1/webhooks/momo/ipn`: xác thực, kiểm partner/order/request ID; ánh xạ resultCode theo mục 1.2, không đồng nhất authorized với captured; commit rồi mới HTTP 204. Lỗi phản hồi theo mục 1.3, không trả 204 vô điều kiện |
| Đối soát | API truy vấn trạng thái giao dịch, cùng quy tắc `expired` như VNPay |
| Hoàn tiền | MVP: thủ công |

> Tham số, mã kết quả và định dạng chữ ký lấy theo **tài liệu chính thức mới nhất** của VNPay và MoMo khi bắt đầu code. Unit test chữ ký dùng dữ liệu mẫu từ chính tài liệu đó.

### 3.1. Khởi tạo thanh toán có thể khôi phục

Quy trình chung cho endpoint bắt đầu Thanh toán online:

1. **Chuẩn bị** (transaction ngắn): claim Idempotency-Key theo scope và request_hash, khoá Order để kiểm quyền, trạng thái, hạn thanh toán. ordering gọi payments.contracts.prepare_payment để ghi Payment prepared với provider_txn_ref, provider_request_id ổn định trong cùng transaction; gắn resource_id vào key rồi commit trước khi gọi gateway. ordering sở hữu kiểm tra Order; payments sở hữu Payment và dữ liệu tạo giao dịch. Cùng key dùng lại Payment cũ; key khác là lần thử mới.
2. **Gọi gateway**: sau commit, gọi payments.contracts.start_payment(payment_id, operation_id); claim lease thao tác tạo trong DB rồi commit. Mọi đường xử lý (request HTTP, job khôi phục) dùng cùng lease. Gọi gateway ngoài transaction.
   - VNPay: ký lại cùng bộ tham số đã lưu.
   - MoMo: lưu payload chuẩn hoá (amount, return_url do backend dựng từ origin/path đã cấu hình, expires_at, các ID ổn định) để retry không đổi dữ liệu.
   - Không lưu secret/chữ ký trong payload; adapter ký lúc gọi. Có thể lưu trong creation_input của Payment; chỉ field adapter cho phép, không sao chép request thô.
3. **Lưu kết quả**:
   - Chắc chắn tạo được link: khoá Payment/key, kiểm lease token, lưu redirect_url, creation_status=ready và response idempotency. Kết quả tạo tới sau IPN không ghi đè status/amount_received đã xác nhận.
   - Bị từ chối chắc chắn: creation_status=failed và kết quả lỗi cuối.
   - Timeout, mất kết nối, crash trước khi lưu: giữ prepared/unknown, không tạo Payment mới.
4. **Gọi lại / khôi phục**: cùng key khi chưa xong trả 202 PAYMENT_INITIALIZING với Retry-After; client thử lại cùng body/key. Job recover_payment_initializations quét prepared/unknown có lease hết hạn, truy vấn cùng mã giao dịch trước. Chỉ gọi lại thao tác tạo với cùng ID và payload khi adapter xác nhận thao tác idempotent theo đặc tả provider. Chưa phân biệt được "không tồn tại" với "chưa cập nhật" thì tiếp tục truy vấn và cảnh báo, không sinh ID mới.
5. **Lease và hạn**: lease khởi tạo 3 phút, quét mỗi phút **[Giả định · kiểm chứng: độ trễ thực tế khi nghiệm thu sandbox, mục 8]**; timeout tổng một lần gọi ngắn hơn lease, không retry HTTP vô hạn.
   - Quá hạn link không tạo/gia hạn link, nhưng vẫn đối soát tiền đã nhận bằng mã cũ.
   - Gateway báo đã trả hoặc đã hết hạn mà không có link: creation_status=closed, vô hiệu lease, lưu kết quả cuối cho key để client xem trạng thái Đơn hàng; response tạo cũ không mở lại closed.
   - Key in_progress chưa xác định kết quả không bị purge theo mốc 24 giờ.

MoMo: requestId dùng cho idempotency, API query tra theo orderId ([idempotency](https://developers.momo.vn/v3/vi/docs/payment/api/result-handling/idempotency/), [query](https://developers.momo.vn/v3/vi/docs/payment/api/payment-api/query/)).

- Adapter phải xác minh trong sandbox, cho đúng sản phẩm tích hợp: thời hạn giữ key, mã lỗi trùng, cách lấy lại payUrl, khả năng truy vấn.
- Query biết giao dịch tồn tại không có nghĩa lấy lại được link. Không có đường lấy lại link an toàn thì trả trạng thái cuối/đang xử lý, không hứa khôi phục payUrl bằng mọi giá.

## 4. GHN

| Việc | Cách làm |
|---|---|
| Báo giá | API tính phí theo địa chỉ giao, cân nặng, kích thước mặc định, giá trị hàng. Timeout **3 giây**; lỗi/quá thời gian trả Phí ship dự phòng (BR-SHP-02). `quote_fee` luôn trả phí GHN thật (hoặc Phí ship dự phòng); miễn phí ship theo ngưỡng do `ordering` áp khi tính tổng đơn |
| Cache báo giá | Cache phí GHN thật 10 phút theo hash request báo giá chuẩn hoá đầy đủ: môi trường/provider, ShopID và nơi gửi, service/service_type, địa chỉ GHN đích sau mapping, cân nặng và kích thước chính xác, giá trị khai báo/bảo hiểm, COD nếu gửi, mọi tham số tác động phí, config_revision, mapping_revision. Không đưa secret/header xác thực, thông tin liên hệ/địa chỉ đường phố vào key. Không gom weight_bucket trừ khi đã chứng minh tương đương phí. Không cache fallback chung với phí thật; lỗi thì trả fallback có reason/source, lần sau vẫn thử GHN |
| Tạo vận đơn | request_shipment ghi requested cùng snapshot creation_input và reference/client_order_code ổn định, enqueue sau commit. Task claim lease trong DB rồi gọi GHN ngoài transaction. Thành công chắc chắn: ghi mã GHN, phát ShipmentCreatedV1 một lần; từ chối chắc chắn: failed. Timeout/mất kết nối/crash chưa rõ kết quả không chuyển failed, giữ creation_unknown để query theo mã shop trước retry (mục 4.3) |
| Huỷ vận đơn | Dùng khi Vận đơn tạo xong cho đơn đã bị huỷ (cờ `shipment_after_cancel`). `ordering` gọi `shipping.contracts.request_shipment_cancellation`: ghi Vận đơn `cancel_requested`, đẩy task lên queue `integrations` sau commit. Task gọi `cancel_shipment` của adapter (API huỷ đơn GHN). Thành công: `cancelled`. Lỗi sau khi hết retry: giữ `cancel_requested`, báo Sentry; Staff xử lý tay theo Cờ cần xử lý đã gắn **[Cần xác minh API huỷ của GHN và trạng thái nào còn huỷ được]** |
| Webhook | `POST /api/v1/webhooks/ghn`: lưu `shipping_shipment_event`, đổi trạng thái GHN sang trạng thái nội bộ, phát sự kiện |
| Đối soát | Xem danh sách ngay dưới bảng |

Đối soát GHN:

- Mỗi 15 phút truy vấn theo mã GHN các Vận đơn chưa cuối **không có cập nhật nào (webhook hay Đối soát) trong 6 giờ**, ưu tiên Vận đơn lâu chưa cập nhật nhất. Đơn giao trong 1–4 ngày nên trạng thái chậm vài giờ không ảnh hưởng quyết định nào.
- Giới hạn mỗi vòng = một phần rate limit GHN × 15 phút **[Cần xác minh rate limit với GHN]**; tạm mặc định **500 Vận đơn mỗi vòng** (khoảng 2.000/giờ). Quét hết sẽ thành hàng chục nghìn lần gọi mỗi vòng, vượt rate limit; đa số đã có webhook.
- Webhook GHN chết lâu ở tải cao (khoảng 15.000 Vận đơn chưa cuối cần khoảng 2.500 lần hỏi/giờ) thì Đối soát không theo kịp; chấp nhận tồn đọng, cảnh báo khi số Vận đơn quá 6 giờ chưa Đối soát tăng liên tục ([10](./10-nfr.md)).
- requested/creation_unknown hết lease phải query bằng mã shop trước khi quyết định tạo lại.
- cancel_requested vẫn thử huỷ lại qua cùng mã; không tạo Vận đơn thay thế.

### 4.1. Ánh xạ trạng thái GHN

| Nhóm trạng thái GHN (ví dụ) | Trạng thái `shipping_shipment` | Sự kiện phát ra |
|---|---|---|
| (nội bộ: đã nhận yêu cầu, task chưa gọi GHN xong) | `requested` | — |
| (nội bộ: GHN tạo vận đơn thành công) | `created` | `ShipmentCreatedV1` |
| (nội bộ: timeout/kết quả tạo chưa rõ) | `creation_unknown` | — |
| (nội bộ: GHN từ chối chắc chắn, chưa tạo) | `failed` | `ShipmentCreationFailedV1` |
| (nội bộ: đã nhận yêu cầu huỷ, task chưa gọi GHN xong) | `cancel_requested` | — |
| `ready_to_pick`, `picking` | `picking` | — |
| `delivering`, `transporting` | `in_transit` | — |
| `delivered` | `delivered` | `ShipmentDeliveredV1` |
| `return`, `returning` | `returning` | — |
| `returned` | `returned` | `ShipmentReturnedV1` |
| `cancel`, có `cancellation_requested_at` đã lưu | `cancelled`, kể cả callback lặp khi đã cancelled | — |
| `cancel` không có ý định huỷ đã lưu, `lost`, `damage`, `exception` | `exception` (trừ khi terminal guard bên dưới từ chối) | `ShipmentExceptionV1` (`provider_status` giữ mã gốc của GHN); `ordering` gắn cờ `shipment_exception`, Staff xử lý theo [05](../business/05-order-lifecycle.md) mục 4.7 |

Danh sách mã trạng thái đầy đủ lấy theo tài liệu GHN khi code.

- Response tạo, webhook và query đi qua cùng một service dưới khoá Shipment.
- Ghi `cancellation_requested_at` trong transaction yêu cầu huỷ **trước HTTP**, giữ sau khi thành cancelled; gọi lặp không đổi mốc. Không dùng riêng trạng thái cancel_requested để suy ra có yêu cầu huỷ.

| Trạng thái hiện tại | Observation được áp dụng |
|---|---|
| requested/creation_unknown | Tìm thấy Vận đơn ngoài GHN: lưu mã, phát ShipmentCreated một lần bằng created_event_id, rồi áp trạng thái provider kể cả đã delivered/returned; không làm mất T10 trước T11/T12 |
| created/picking | Chỉ tiến picking → in_transit → delivered hoặc returning → returned; được bỏ bước trung gian. Có thể sang exception, hoặc cancelled khi đúng ý định huỷ; created tới muộn không ghi lùi |
| in_transit | delivered, returning, returned hoặc exception; cancel chỉ áp khi có ý định huỷ đã lưu và provider xác nhận, không suy ra từ timeout |
| returning | returned; picking/in_transit/delivered tới muộn không ghi lùi, mâu thuẫn thì cảnh báo |
| cancel_requested | cancelled khi provider xác nhận; provider không huỷ được thì vẫn ghi tiến trình giao/hoàn đã xác thực, giữ cancellation_requested_at và cảnh báo để ordering xử lý; không tự phát thành công huỷ |
| delivered/returned/cancelled | Duplicate cùng kết quả là no-op; observation lùi/mâu thuẫn chỉ ghi Event/metadata và cảnh báo, không đổi terminal hoặc phát sự kiện mới |
| exception | Duplicate cùng mã sự cố không phát lại sự kiện; chỉ phục hồi qua query verified cho thấy picking/in_transit/delivered/returning/returned. Shipping ghi thực tế provider và phát sự kiện, không đọc Order hoặc hỏi ordering. Ordering tự kiểm lifecycle, không hồi sinh Order đã huỷ; mâu thuẫn cần Staff xử lý |
| failed | Chỉ chuẩn bị tạo lại khi đã xác nhận chưa có Vận đơn ngoài GHN; query bất ngờ thấy mã thì cảnh báo, đi nhánh phát ShipmentCreated một lần, không tạo Vận đơn mới |

- Không lấy enum số/thứ tự chuỗi làm thứ tự trạng thái.
- ShipmentEvent vẫn ghi observation xác thực để tra cứu; khoá Shipment + so trạng thái/created_event_id bảo vệ tác động khi webhook lặp hoặc sai thứ tự.
- Không chờ đủ mọi bước mới xử lý kết quả cuối.

### 4.2. ⚠️ Rủi ro mở: địa chỉ 2 cấp và 3 cấp

Hệ thống dùng địa chỉ **2 cấp** (tỉnh/thành → phường/xã). [Tài liệu tạo đơn GHN](https://developer.ghn.vn/vi/docs/order/create) hiện mô tả is_new_to_address và bộ danh mục mới 2 cấp; đây mới là xác minh tài liệu, chưa phải nghiệm thu sandbox. Adapter phải xác định chế độ địa chỉ, mapping và tham số tương ứng của API báo giá/tạo đơn; đưa chế độ và mapping revision vào cache key.

- Bảng `shipping_ghn_location_mapping` ánh xạ `ward_code` của hệ thống sang ID của GHN.
- Dữ liệu ánh xạ nạp bằng management command từ API danh mục địa chỉ GHN.
- Phường/xã chưa có ánh xạ: dùng Phí ship dự phòng, gắn Cờ cần xử lý `ghn_ward_unmapped`. Admin chọn ID tỉnh, quận, phường GHN trên back-office (`settings/ghn-locations`, US-1004), rồi Staff bàn giao như bình thường và gỡ cờ. Có thể bỏ màn này nếu kiểm tra cho thấy GHN đã dùng địa chỉ 2 cấp.
- **Việc cần làm khi tích hợp GHN**: nghiệm thu sandbox đầy đủ một tuyến địa chỉ 2 cấp qua báo giá, tạo đơn và callback; cập nhật mapping theo kết quả. Không dùng district_id giả để vượt validation.

### 4.3. Khôi phục tạo Vận đơn chưa rõ kết quả

- **Snapshot**: request_shipment tạo một Shipment với client_order_code=reference duy nhất theo shop, lưu creation_input chính xác (địa chỉ nhận, hàng, COD, dịch vụ, mapping đã chọn). Payload có PII nên không log/audit/outbox; redaction xoá PII cả trong creation_input khi yêu cầu xoá dữ liệu đủ điều kiện. Retry cùng mã không tự thay payload theo cấu hình hay dữ liệu Đơn hàng mới hơn.
- **Lease**: mọi task create/recovery dùng cùng lease token trên Shipment, 3 phút **[Giả định · kiểm chứng: độ trễ thực tế khi nghiệm thu sandbox, mục 8]**, timeout tổng < lease. Snapshot và lease commit trước HTTP. requested hết lease xử lý như chưa rõ kết quả dù chưa kịp ghi creation_unknown. Kết quả cũ chỉ ghi nếu lease còn khớp; webhook đã đưa trạng thái xa hơn thì không ghi created đè, nhưng vẫn bảo đảm ShipmentCreatedV1 được ghi một lần để ordering áp T10.
- **Lookup**: find_by_client_code(shop_id, client_order_code) trả found/not_found/unknown; timeout/response không hợp lệ là unknown. Found thì gắn đúng mã GHN, không gọi create thêm. Not_found chỉ cho create lại cùng mã và payload khi đã xác minh cơ chế chống trùng và độ nhất quán truy vấn của GHN; một lần query chưa thấy không chứng minh chưa tạo.
- **Chưa xác định**: giữ creation_unknown, next_recovery_at và cảnh báo; hết retry lỗi mạng không thành failed. Staff không được huỷ Đơn hàng hoặc bàn giao lại khi requested/creation_unknown. Chỉ retry failed khi biết chắc chưa có Vận đơn ngoài GHN; không sinh client_order_code mới để né lỗi trùng.
- **Nghiệm thu**: GHN có [tra theo mã shop](https://developer.ghn.vn/vi/docs/order/info-by-client-code) và mô tả client_order_code duy nhất theo shop trong [API tạo](https://developer.ghn.vn/vi/docs/order/create). Nghiệm thu sandbox với đúng ShopID/môi trường: tạo thành công nhưng mất response, query ngay/lặp lại, create trùng, response tới muộn. Chưa xác minh thì không bật retry tạo tự động sau timeout. FakeShippingProvider phải mô phỏng các trường hợp này.

### 4.4. ⚠️ Rủi ro mở: đối chiếu tiền COD

Thanh toán COD ghi `succeeded` khi GHN báo đã giao (T11), nhưng tiền thật về tài khoản cửa hàng khi GHN chuyển thu hộ, thường vài ngày sau và theo đợt. MVP **không** đối chiếu khoản chuyển này với từng Đơn hàng: kế toán đối chiếu bằng báo cáo GHN và file `reports/paid-orders.csv`. Đây không phải Đối soát theo nghĩa trong [GLOSSARY.md](../../GLOSSARY.md).

## 5. Google OAuth

- Frontend (NextAuth) lấy `id_token` từ Google, server Next.js gửi sang `POST /api/v1/store/auth/google`.
- Django xác minh bằng `google.oauth2.id_token.verify_oauth2_token` (xem [05-auth-security.md](./05-auth-security.md)).
- Liên kết Tài khoản theo email đã xác minh (US-502). Tài khoản khớp chưa xác thực email thì xoá mật khẩu cũ, tăng `token_version`, thu hồi mọi refresh token ([05-auth-security.md](./05-auth-security.md) mục 3), để chặn kẻ gian đăng ký trước bằng email nạn nhân.
- Local dùng redirect URI `http://localhost:3000/…`; Google cho phép `localhost`.

## 6. Email

| Môi trường | Backend gửi | Ghi chú |
|---|---|---|
| Local | SMTP tới **Mailpit**: worker trong Compose gửi tới `mailpit:1025`; API và tiến trình khác chạy trên máy gửi tới `localhost:1025` ([08](./08-local-development.md) mục 2.3). Giao diện xem mail `http://localhost:8025` | Không email nào ra ngoài |
| Test | `locmem` | Kiểm tra nội dung email trong test |
| AWS | **Amazon SES** | Cần xác minh domain (SPF, DKIM, DMARC) và xin thoát sandbox SES |

- EmailLog tạo trong PostgreSQL cùng transaction với handler. Task nhận ID log, claim bằng lease, gửi ngoài transaction; job mỗi phút khôi phục email chờ gửi hoặc lease hết hạn. Retry không cần phát lại sự kiện.
- Email có thể trùng nếu nhà cung cấp đã nhận nhưng worker chưa ghi `sent`; không bảo đảm đúng một lần.
- Token xác thực/reset chỉ cấp lúc gửi, không lưu trong outbox hay EmailLog. Xem [07 mục 4](./07-async-events-jobs.md#4-email-hàng-đợi-bền-vững-trong-postgresql).

## 7. Fake Gateway (local và test)

Chỉ có khi `FAKE_PROVIDERS_ENABLED = true` (mục 1). Đây là ngoại lệ duy nhất trình duyệt gọi thẳng Django, chỉ ở local, thay trang thanh toán của cổng thật.

```
1. Client gọi POST /store/orders/{code}/payments {gateway: "vnpay"}
2. FakeGateway trả redirect_url = http://localhost:8000/dev/fake-gateway/{provider_txn_ref}
3. Trang giả lập hiện: số tiền, mã đơn, các nút
     [Thanh toán thành công] [Thất bại] [Thành công nhưng sai số tiền] [Không gửi IPN]
4. Bấm nút → Fake gọi nội bộ vào đúng luồng xử lý IPN (có chữ ký giả hợp lệ)
5. Chuyển về return_url như cổng thật
```

Nút "Không gửi IPN" để thử job Đối soát: `FakeGateway.query_transaction` trả kết quả đã chọn.

`FakeShippingProvider` mặc định báo giá cố định theo cân nặng, tạo và huỷ thành công; có lệnh `manage.py fake_shipment_status <code> delivered`. Đây là chế độ mặc định, không phải hành vi duy nhất. Fake có state giao dịch riêng với model nghiệp vụ để phát hiện create trùng; kịch bản cấu hình xác định trong test, không sleep/ngẫu nhiên:

- Chắc chắn từ chối trước tạo, timeout trước tạo, tạo xong nhưng mất response; query found/not_found/unknown, kể cả chưa thấy ngay rồi thấy sau.
- Create trùng cùng client code, callback lặp hoặc đảo thứ tự, response tạo tới sau delivered/returned, cancel lặp sau cancelled và cancel không do cửa hàng yêu cầu.
- Huỷ thất bại/unknown, query xác nhận đã huỷ hoặc vẫn đang giao; các bước điều khiển bằng test hook và time-machine.
- FakeGateway có cùng chế độ lỗi khởi tạo, captured/authorized/failed và số tiền sai; callback và query dùng cùng thuật toán observation key. Test đếm giao dịch ở fake, không chỉ đếm dòng Payment/Shipment.

## 8. Nghiệm thu với sandbox thật (trước khi lên AWS)

Dùng **Cloudflare Tunnel** để VNPay, MoMo, GHN gọi được vào máy local:

1. Tạo tunnel có tên miền cố định, ingress chỉ cho path `/api/v1/webhooks/*` tới `http://localhost:8000`, path khác trả 404. Không dùng `cloudflared tunnel --url` vì lệnh này mở cả API local ra internet.
2. Khai báo URL IPN và webhook với sandbox VNPay, MoMo, GHN.
3. Đổi adapter sang bản thật (mục 1).
4. Chạy kịch bản: thanh toán thành công, thất bại, link hết hạn sau 10 phút, IPN đến muộn, trả tiền hai lần cho cùng đơn, tạo Vận đơn, huỷ Vận đơn, giao thành công, Hoàn hàng.
5. Ghi kết quả vào biên bản nghiệm thu.

## 9. Kịch bản kiểm thử

Test adapter bên thứ ba đặt ở `infrastructure/<payment|shipping|google>/tests/test_<tên>.py`; test webhook API ở `apps/<payments|shipping>/tests/api/webhooks/test_views.py`. Nguyên tắc chung ở [12-testing-strategy.md](./12-testing-strategy.md).

| Kịch bản | Kỳ vọng |
|---|---|
| Snapshot JSON tích hợp | DTO creation_input từ chối field lạ/secret/PII không được phép, kiểm schema_version, dữ liệu khớp Payment/Shipment, giữ nguyên URL/mapping/dịch vụ khi retry. Redaction Shipment không để lại PII và không dùng snapshot đã redaction để tạo lại |
| Tiền yêu cầu không phải tiền thực nhận | Callback chữ ký đúng nhưng failed/pending/authorized và amount khác không tăng amount_received hoặc tạo Hoàn tiền. VNPay phải có cả response_code/transaction_status thành công; MoMo 9000 không coi là capture; chỉ captured sai số tiền mới phát amount_mismatch |
| Observation key IPN/Đối soát | Cùng normalized result từ hai nguồn có cùng obs:v1 hash; responseTime/message đổi không sinh tác động tiền. Pending và captured khác key; succeeded/captured không bị kết quả muộn ghi lùi; capture xung đột transaction/số tiền bị cảnh báo, không cộng/hoàn tự động |
| Capture ID bền vững | Capture đầu ghi captured_transaction_id cùng amount_received; sau redaction raw_payload vẫn so được capture mới. Online có tiền nhưng thiếu ID hoặc COD có ID bị CHECK chặn; ID không đổi do pending/failed tới muộn |
| GHN huỷ theo yêu cầu nhận callback lặp | cancellation_requested_at ghi trước HTTP, giữ sau cancelled. Cancel đầu chuyển cancelled; cancel lặp không thành exception hay phát thêm sự kiện. Cancel không do shop yêu cầu đi nhánh exception; callback lùi sau delivered/returned/cancelled không đổi terminal |
| Timestamp provider bị thiếu | ShipmentObservation thiếu occurred_at vẫn ghi Event với occurred_at=NULL, created_at là lúc nhận; không bịa thời điểm GHN. Query hợp lệ không đổi trạng thái vẫn cập nhật Shipment.updated_at cho lịch Đối soát |

- **ACK webhook**: ép rollback/lỗi commit không trả ACK thành công; callback trùng đã commit trả ACK riêng provider, không tác động lại. Sai chữ ký/merchant/currency và observation chưa xác minh không tạo tác động tiền. Kiểm response VNPay 00/02/04/97/01 và HTTP 204 MoMo đúng nhánh theo mục 1.3.
- **Phục hồi khởi tạo**: gateway đã tạo nhưng response timeout/process chết trước khi lưu; cùng key và job phục hồi giữ Payment, provider_txn_ref, provider_request_id. Query trước; chỉ retry create khi adapter có hợp đồng idempotency đã xác minh. Fake provider đếm giao dịch ngoài DB để phát hiện tạo trùng.
- **Kết quả tới muộn**: IPN succeeded đến trước response tạo link; lưu response không hạ status/amount_received. Lease cũ không ghi đè lease mới. Quá hạn link không tạo/gia hạn link; gateway không cung cấp lại link thì API trả đang xử lý hoặc trạng thái cuối, không bịa redirect_url.
- **HTTP ngoài transaction**: spy/mock transport xác nhận không có transaction atomic khi gọi gateway/GHN; lấy lại quote sau PRICE_CHANGED chỉ chạy sau rollback. Time-machine vượt lease rồi chạy job, không sleep.
- **Chữ ký VNPay (HMAC-SHA512) và MoMo (HMAC-SHA256)**: unit test với dữ liệu mẫu từ tài liệu provider: chữ ký đúng, sai một ký tự, thiếu field. Fake Gateway không kiểm chữ ký nên đây là nơi duy nhất bảo vệ phần đó.
- **Gọi HTTP** bằng respx: timeout, 5xx, response sai định dạng; GHN báo giá lỗi dùng fallback; chỉ phát shipment-creation-failed khi xác nhận bị từ chối/chưa tạo. Timeout tạo là creation_unknown và được đối soát; test cancel_shipment riêng.
- **Tạo Vận đơn mất response**: FakeShippingProvider đếm Vận đơn ngoài DB. Query theo shop/client code tìm lại cùng Vận đơn; hai task claim cùng lease không gọi tạo song song; stale result không ghi đè lease mới hoặc trạng thái xa hơn. ShipmentCreatedV1 chỉ ghi một lần kể cả khi webhook/query phát hiện trước response tạo.
- **Chưa rõ kết quả**: query timeout/not_found chưa chắc chắn giữ unknown, không đổi reference/payload, không tạo lại mù. Staff huỷ/bàn giao lại bị chặn. Sandbox phải kiểm trùng client code và độ trễ truy vấn trước khi bật retry tạo tự động; lỗi mạng hết retry không chuyển failed.
- **Cache phí**: cùng request chuẩn hoá thì hit; đổi shop/nơi gửi, service, địa chỉ đã mapping, cân nặng/kích thước, giá trị khai báo/COD hoặc revision thì miss. Hai cân nặng cùng bucket cũ không dùng chung phí. Fallback không lấp cache GHN thật; GHN phục hồi thì request sau lấy được phí thật. Không có secret hay PII liên hệ trong cache key/log.
- **IPN và webhook**: gọi trùng, sai chữ ký, sai số tiền, đến muộn sau khi đơn đã bị huỷ.
