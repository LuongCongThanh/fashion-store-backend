# 12. Chiến lược test

> Trạng thái: **Đã chốt cho MVP** ([quy ước](../../README.md#trạng-thái-tài-liệu)). Phạm vi: chỉ backend Django. Frontend Next.js là repo riêng ([ADR 0001](../adr/0001-nextjs-frontend-django-api.md)) và tự có chiến lược test; ở đây chỉ nói phần backend cam kết với frontend (OpenAPI, mục 5).

Quy ước viết code test (factory, mock, thời gian) nằm ở [02-backend-structure.md](./02-backend-structure.md) mục 9.5. Cách chạy test ở máy local xem [08-local-development.md](./08-local-development.md) mục 5.

## 1. Nguyên tắc

- Test chạy trên **PostgreSQL thật** (`test_fashion`, do pytest-django tự tạo), không dùng SQLite và không mock ORM. Lý do: nghiệp vụ dựa vào `select_for_update`, `EXCLUDE`, `unaccent`.
- Chỉ giả lập **hệ thống bên ngoài**: Fake Gateway cho thanh toán và vận chuyển ([ADR 0005](../adr/0005-provider-adapters-fake-gateways.md)), `respx` cho `httpx`. Fake Gateway và `FakeShippingProvider` được bật bằng `FAKE_PROVIDERS_ENABLED=true` trong `settings/test.py` (cùng cờ với local), nên flow test gọi được trang và endpoint IPN của Fake Gateway. CI không gọi sandbox thật của VNPay, MoMo, GHN (mục 7).
- Celery chạy đồng bộ (`CELERY_TASK_ALWAYS_EAGER=True` trong `settings/test.py`); thời gian cố định bằng `time-machine`.
- Test chạy trong transaction không bao giờ commit, nên task đẩy bằng `shared.tasks.enqueue_on_commit` không tự chạy, và relay (một tiến trình riêng) không tự gửi sự kiện. Test service cần task chạy thì dùng `django_capture_on_commit_callbacks(execute=True)`; flow test dùng `drain_events()` (mục 2.7).
- Nghiệp vụ được test ở tầng **service**. Tầng API chỉ test những gì thuộc về HTTP, không test lại nghiệp vụ.
- Repo là public: dữ liệu mẫu phải là giá trị giả rõ ràng ([11-git-workflow.md](./11-git-workflow.md) mục 8).

## 2. Các loại test

Xếp theo số lượng, từ nhiều đến ít. Hàm thuần không cần DB (ví dụ `Money`, kiểm tra chữ ký) không có loại riêng, mà xếp vào loại của module chứa nó.

| # | Loại | Đặt ở | Kiểm tra gì |
|---|---|---|---|
| 1 | Service | `modules/<module>/tests/test_services_<chủ đề>.py` | Business rule, chuyển trạng thái, sự kiện ghi vào outbox |
| 2 | Concurrency | `modules/<module>/tests/test_concurrency_<chủ đề>.py` | Không bán vượt Tồn kho, không vượt lượt Voucher, không deadlock |
| 3 | Handler và outbox | `modules/<module>/tests/test_handlers_<chủ đề>.py`, `shared/events/tests/` | Mỗi sự kiện chỉ xử lý một lần, sự kiện tới sai thứ tự, consumer xử lý đúng từng loại lỗi, relay gửi đúng và gửi lại được |
| 4 | API | `modules/<module>/tests/test_api_<store\|backoffice\|webhooks>.py` | Phân quyền, `X-Lookup-Token`, định dạng lỗi, `Idempotency-Key`, throttle theo `X-Client-IP`, N+1 query |
| 5 | Bảo mật auth/JWT | `modules/identity/tests/test_services_tokens.py` | Theo OWASP JWT Cheat Sheet |
| 6 | Adapter nhà cung cấp | `modules/<payments\|shipping>/tests/test_providers_<tên>.py` | Chữ ký VNPay/MoMo, gọi HTTP lỗi, IPN bất thường |
| 7 | Flow xuyên module | `backend/tests/flows/test_<flow>_flow.py` | Một luồng nghiệp vụ đi hết từ đầu đến cuối qua HTTP |

Ngoài pytest, CI còn có các **cổng kiểm tra tĩnh** (mục 8).

### 2.1. Service

- Mỗi hàm service có ít nhất 1 test cho trường hợp chạy đúng và 1 test cho mỗi lỗi nghiệp vụ nó ném ra.
- Test nào kiểm tra một quy tắc trong [04-business-rules.md](../business/04-business-rules.md) thì gắn marker `br` (mục 3).
- Kiểm tra sự kiện: service ghi đúng sự kiện vào outbox, và khi service lỗi thì không có sự kiện nào được ghi (cùng transaction).
- Mốc thời gian (Giữ hàng 15 phút, Hoàn tất sau 7 ngày, Đổi trả trong 7 ngày) dùng `time-machine`, test cả hai phía của mốc.

```python
@pytest.mark.br("BR-INV-02")
def test_reserve_stock_fails_when_stock_is_insufficient(stock_item_factory):
    ...
```

Ngoài quy tắc chung, bắt buộc có các test service sau cho **kịch bản nghiệp vụ dễ sai**. Kịch bản kỹ thuật nằm ở tài liệu sở hữu hành vi đó (mục 2.8).

Selector tìm Sản phẩm cần test trên PostgreSQL thật theo BR-CAT-13: `ao thun`, `áo thun`, `ÁO THUN` và `  ao thun  ` cho cùng kết quả; `basic` khớp một phần tên; `ao thnu` và `thun ao` không khớp tên "Áo thun Basic cổ tròn". Kiểm tra thêm từ khoá rỗng/chỉ khoảng trắng, từ khoá 1–2 ký tự, `%`/`_`/ký tự escape được tìm như ký tự thường, Sản phẩm không `active` bị loại và bộ lọc/cách sắp xếp vẫn được áp dụng. Không kiểm tra việc luôn dùng GIN index vì execution plan phụ thuộc dữ liệu và độ dài từ khoá.

| Kịch bản | Kỳ vọng |
|---|---|
| Tổng tính lại khác `expected_total` (Giá khuyến mãi vừa hết hạn, Voucher vừa hết lượt) (BR-ORD-07) | Ném `PriceChanged` (`PRICE_CHANGED`) kèm bảng tính mới; không tạo đơn, không Giữ hàng, không tính lượt Voucher |
| Quote token gắn với báo giá Người mua đã xem | Token giả/sửa/chữ ký sai hoặc đổi subject/input → 400 INVALID_QUOTE; hết hạn → 409 QUOTE_EXPIRED. Giá/snapshot đổi giữa quote và checkout dù tổng không đổi → PRICE_CHANGED. Token không Giữ hàng, không cố định giá; quote mới dùng token/key mới |
| Hai checkout cùng giỏ | Cart được khoá trước StockItem; lần đầu tạo Order, xoá dòng đã mua và lưu idempotency cùng transaction. Cùng key replay trả cùng Order kể cả token đã hết hạn; key khác không đặt lại giỏ đã xoá; thêm/sửa/merge cart đồng thời không làm mất dòng mới hoặc dùng snapshot giỏ sai |
| Đơn có Tổng tiền đơn ≤ 0 (BR-ORD-09) | Cả quote và checkout, với COD và online, trả `422 ORDER_TOTAL_NOT_POSITIVE`; checkout không tạo Order, Payment, Giữ hàng, Hàng chờ xuất hay lượt dùng Voucher. Ghi Order có `total = 0` trực tiếp phải bị CHECK chặn; tổng 1đ vẫn hợp lệ ở quy tắc này |
| Làm tròn Voucher theo % (BR-VCH-10) | Tạm tính 1.001đ, giảm 10% → 100đ; sau đó mới áp mức giảm tối đa và giới hạn bằng Tạm tính; không dùng float |
| Phân bổ Voucher về Dòng đơn hàng (BR-ORD-02) | Sắp theo `variant_id`; dòng 500đ và 501đ, giảm 100đ → 49đ và 51đ; đảo thứ tự request không đổi kết quả. Ba dòng mỗi dòng 1đ, giảm 2đ → 0đ, 1đ, 1đ. Tổng phân bổ đúng số giảm và không vượt giá trị từng dòng |
| Hoàn tiền khi Đổi trả một phần có Voucher (BR-RET-07) | Đơn 3 × 200.000đ, Voucher giảm 60.000đ, được miễn phí ship; trả 1 áo → hoàn 180.000đ, không truy thu phí ship |
| Hoàn tiền có phần lẻ qua nhiều lần (BR-RET-07) | Dòng 3 × 100đ, Voucher phân bổ 1đ: trả từng sản phẩm → 99đ, 100đ, 100đ; trả cả dòng một lần → 299đ. Tính cả số lượng đã chấp nhận có Refund còn `requested`; không tính phần bị từ chối. Hai lần accept đồng thời được tuần tự hoá dưới khoá Order |
| Đổi trả có hàng được chấp nhận nhưng số hoàn bằng 0 (BR-RET-07) | Dòng 2 × 1đ được phân bổ Voucher 1đ: trả sản phẩm đầu → 0đ, yêu cầu `refunded` với `refund_id = NULL`, nhập kho đúng lựa chọn, không tạo Refund/sự kiện Hoàn tiền; lần trả sản phẩm còn lại → 1đ. Accept lặp không nhập kho lại; không chấp nhận sản phẩm nào vẫn `rejected` |
| Giới hạn lượt dùng Voucher mỗi người (BR-VCH-07) | Khách hàng đã dùng hết lượt rồi đặt tiếp như Khách vãng lai bằng cùng số điện thoại → Voucher bị từ chối |
| Staff huỷ đơn PACKING khi Vận đơn requested hoặc creation_unknown (T9) | Ném SHIPMENT_IN_PROGRESS, giữ PACKING; không cho bàn giao lại để tạo mã mới |
| Thanh toán của đơn COD | T2 tạo Thanh toán COD `pending`; T11 chuyển `succeeded`; huỷ đơn hoặc Hoàn hàng chuyển `cancelled`. Không thao tác nào ghi `payments.payment-succeeded` vào outbox, nên đơn COD giao xong không bị tạo Hoàn tiền |
| Hàng chờ xuất (BR-INV-10) | Đặt đơn COD: Tồn kho giảm, Hàng chờ xuất tăng đúng số lượng; T10 xoá Hàng chờ xuất; huỷ trước Bàn giao (T7, T9) trả Hàng chờ xuất về Tồn kho |
| Kiểm kê (BR-INV-12) | Tồn kho 7, Hàng chờ xuất 3, số đếm 10 → không điều chỉnh; số đếm 9 → điều chỉnh −1 loại `stock_count` |
| Điều chỉnh giảm vượt Số lượng bán được (BR-INV-11) | Ném `INSUFFICIENT_AVAILABLE`; Tồn kho không đổi |
| Giữ hàng đã quá `expires_at` nhưng job chưa giải phóng | `reserve_stock` của Người mua khác thành công; Giữ hàng cũ chuyển `released`, `reserved` giảm tương ứng |
| Job T4 khi `shared.events.delivery_lag()` quá 60 giây | Không huỷ đơn nào, log `cancel_skipped_delivery_backlog`; hết tồn đọng thì lượt sau huỷ bình thường. Bỏ lượt liên tục quá 15 phút thì phát cảnh báo `cancel_skipped_too_long` nhưng vẫn không huỷ |
| Bắt đầu Thanh toán online ở phút 6:59 và phút 7:00 kể từ khi đặt đơn (BR-INV-05) | 6:59 tạo được Thanh toán; 7:00 ném `PaymentWindowClosed` (`PAYMENT_WINDOW_CLOSED`) |
| `raise_flag` khi đơn đã có cờ cùng `kind` đang mở | Không tạo cờ thứ hai, `note` được nối thêm |
| `placed_at`, `cancelled_at`, `completed_at` | Được ghi đúng trong transition tương ứng (T2/T3, T4/T5/T7/T9/T14, T13); báo cáo Doanh thu lọc theo `completed_at` (BR-REV-01) |
| Staff huỷ đơn `SHIPPING` (T14) | Chỉ được khi đơn có cờ `shipment_exception` và bắt buộc lý do; Hoàn tiền toàn bộ nếu đã thanh toán online; không trả lượt Voucher |
| Nhập lại sau T12/T14 | T12 đặt `warehouse_return_required = true`; T14 thiếu xác nhận boolean bị từ chối, hàng chưa rời Kho đặt true nhưng chưa tăng tồn, hàng mất/hư đặt false. Endpoint nhập lại chỉ cho đơn có cờ; nhập kho và ghi mốc cùng transaction. Hai request đồng thời hoặc retry chỉ cộng tồn một lần; T7/T9 đã release allocation không được nhập thêm; danh sách chờ nhập gồm đúng T12/T14 cần xử lý |
| Chấp nhận Đổi trả một phần (BR-RET-08) | Chỉ phần `accepted_quantity` của dòng `restock = true` được cộng lại Tồn kho; Hoàn tiền tính trên số lượng được chấp nhận; không dòng nào được chấp nhận thì yêu cầu `rejected` |
| Doanh thu khi Người mua trả tiền hai lần (BR-REV-01) | Hoàn tiền theo BR-PAY-05 không bị trừ; Doanh thu của đơn bằng Tổng tiền đơn |
| Đặt đơn vãng lai bằng email của Tài khoản đã xác thực (BR-ORD-08) | Đơn có `customer_id` ngay khi tạo |
| Hạ Giá bán xuống ≤ Giá khuyến mãi đang hoặc sắp hiệu lực (BR-PRC-05) | Ném `LIST_PRICE_BELOW_SALE_PRICE`; Giá bán không đổi |
| Giá, snapshot, trạng thái bán hoặc SalePrice đổi sau lần đọc báo giá ngoài transaction | Checkout kiểm tra lại dưới khoá Variant; rollback Order, Giữ hàng và lượt Voucher; trả PRICE_CHANGED với quote mới dù tổng tiền tình cờ không đổi |

### 2.2. Concurrency

Test dùng `@pytest.mark.django_db(transaction=True)` và `@pytest.mark.concurrency`. Mỗi test chạy N thread, mỗi thread mở kết nối DB riêng, các thread xuất phát cùng lúc nhờ `threading.Barrier`, rồi kiểm tra bất biến sau khi tất cả kết thúc. Test chạy trong **mọi PR**, vì mỗi worker của `pytest-xdist` đã có DB riêng.

Bắt buộc có các test:

| Kịch bản | Bất biến |
|---|---|
| N khách cùng Giữ hàng hoặc trừ Tồn kho cho K cái cuối cùng của một Biến thể (N > K) | Đúng K lần thành công, N − K lần ném `OUT_OF_STOCK`, Tồn kho không âm |
| N khách cùng dùng một Voucher còn K lượt | Đúng K lượt được dùng, không vượt `usage_limit` |
| Hai Đơn hàng cùng chứa 2 Biến thể nhưng thứ tự Dòng đơn hàng ngược nhau, cùng dùng một Voucher | Cả hai hoàn tất, không deadlock (khoá dòng Tồn kho theo thứ tự `variant_id`, rồi toàn bộ Biến thể theo id để kiểm tra snapshot, rồi mới khoá Voucher) |
| Hai yêu cầu hoàn khác key đồng thời trên một Payment, tổng vượt tiền thực nhận | Chỉ các yêu cầu trong hạn mức thành công; tổng requested + completed không vượt amount_received |
| Hai yêu cầu hoàn cùng payment_id và request_key | Chỉ một Refund được tạo, cả hai trả cùng refund_id; khác tham số bị từ chối |
| Checkout song song với đổi Giá bán hoặc thêm/sửa/xoá SalePrice | Writer và checkout đều khoá Variant; đơn dùng snapshot đã xác thực hoặc rollback PRICE_CHANGED, không lọt giá đọc trước khi writer commit |
| Hai checkout chứa nhiều Biến thể, availability chỉ đổi ở các Biến thể khác nhau | Khoá toàn bộ StockItem rồi toàn bộ Variant theo id trước khi đổi availability; không có thứ tự khoá một phần Variant trước phần còn lại |
| T3 tới muộn của đơn có Giữ hàng vừa quá hạn và checkout của người khác cùng tranh phần hàng đó | Đúng một bên được hàng, Tồn kho không âm; bên thua nhận `OUT_OF_STOCK` hoặc đi nhánh Hoàn tiền |
| Người mua tự huỷ (T5) đúng lúc IPN thành công (T3) trên cùng một đơn | Chỉ một transition chạy trên trạng thái `PENDING_PAYMENT` (khoá dòng Đơn hàng); nếu T5 thắng thì tiền về được xử lý theo BR-PAY-05 |

### 2.3. Handler và outbox

- Mỗi handler: gọi 2 lần với cùng một sự kiện thì chỉ xử lý 1 lần (delivery đã `completed`).
- Kịch bản của hạ tầng sự kiện (consumer, relay, retry, purge, replay, email, xoá dữ liệu, `delivery_lag`, lịch job) và test payload không chứa PII nằm ở [07-async-events-jobs.md](./07-async-events-jobs.md) mục 5.

Bắt buộc có các test handler sau:

| Kịch bản | Kỳ vọng |
|---|---|
| `payments.payment-succeeded` của khoản trả thêm tới khi đơn đã `PLACED`, hoặc tiền tới khi đơn đã `CANCELLED` (BR-PAY-05) | Đơn giữ nguyên; Hoàn tiền gắn đúng payment_id của sự kiện và key ổn định, không suy từ Mã đơn; gắn cờ unexpected_payment và phát sự kiện |
| Sự kiện thành công mới mang cùng payment_id đã dùng đưa đơn vào PLACED | Không tạo Hoàn tiền, không phát thêm OrderPlaced hay UnexpectedPaymentReceived |
| Một đơn có hai Thanh toán online cùng số tiền qua hai gateway | Lưu đúng payment_id dùng cho đơn; Hoàn tiền khoản trả thêm gắn đúng khoản và gateway, không hoàn nhầm khoản ban đầu |
| `payments.payment-failed` với `reason = amount_mismatch` (BR-PAY-04) | Tạo yêu cầu Hoàn tiền đúng `amount_received`; gắn cờ `payment_amount_mismatch`; đơn giữ `PENDING_PAYMENT` |
| `payments.refund-recorded` cho Hoàn tiền không gắn Đổi trả nào | Không Đổi trả nào đổi trạng thái |
| `ordering.order-cancelled` với `previous_status = PENDING_PAYMENT` (T4, T5) | notifications không gửi email (BR-NTF-01) |
| `shipping.shipment-created` tới khi đơn đã `CANCELLED` | Gọi `shipping.contracts.request_shipment_cancellation` (Vận đơn `cancel_requested`); gắn Cờ cần xử lý `shipment_after_cancel` |
| `shipping.shipment-delivered` tới khi đơn còn `PACKING` (T10 chưa chạy) | Ném `TransitionNotYetValid`; đơn giữ nguyên |
| `shipping.shipment-delivered` tới khi đơn đã `DELIVERED` hoặc `COMPLETED` | Không làm gì, không ném lỗi |
| `shipping.shipment-delivered` tới khi đơn đã `RETURNED_TO_SENDER` | Ném `InvalidTransition`; đơn giữ nguyên |
| `payments.payment-succeeded` tới khi đơn còn `PENDING_PAYMENT`, Giữ hàng đã quá `expires_at`, Số lượng bán được còn đủ | Đơn vào `PLACED`; Tồn kho giảm và Hàng chờ xuất tăng đúng số lượng; không tạo Hoàn tiền |
| `payments.payment-succeeded` tới khi đơn còn `PENDING_PAYMENT`, Giữ hàng đã quá hạn và hàng đã bị người khác mua | `commit_reservation` ném `ReservationExpired`; chạy T4 (đơn `CANCELLED`) rồi tạo Hoàn tiền và gắn cờ `unexpected_payment` |
| `shipping.shipment-exception` | Gắn cờ `shipment_exception`; đơn giữ `SHIPPING` |
| `identity.email-verified` | Chỉ gắn các đơn có `contact_email` khớp (không phân biệt hoa thường) và chưa có `customer_id`; đơn đã thuộc Tài khoản khác không bị đổi |
| Đặt đơn online (T1) rồi IPN thành công (T3) | T1 không ghi sự kiện nào vào outbox; T3 ghi đúng một `ordering.order-placed` |

**Hoàn tiền:** test BR-REF-06 cho gọi lại cùng key/cùng tham số, key trùng khác tham số, vượt tiền thực nhận và hoàn tất lặp không phát thêm RefundRecorded. Callback IPN/đối soát trùng không cộng amount_received lần nữa.

### 2.4. API

- **Phân quyền**: mỗi endpoint thử với Guest, Customer, Staff, Admin (theo cột quyền trong [04-api-contract.md](./04-api-contract.md)); Khách hàng này không xem được Đơn hàng của Khách hàng khác.
- **`X-Lookup-Token`**: `GET orders/{code}`, `POST orders/{code}/payments`, `POST orders/{code}/cancel` của Khách vãng lai bị từ chối khi thiếu token, token hết hạn hoặc token của đơn khác. Checkout của Khách vãng lai trả về `lookup_token` dùng được ngay cho ba endpoint này.
- Kịch bản JWT, BFF và cache auth nằm ở [05](./05-auth-security.md) mục 9; ACK webhook, khởi tạo thanh toán và gọi HTTP ngoài transaction nằm ở [06](./06-integrations.md) mục 9.
- **Lỗi**: đúng mã HTTP và đúng định dạng lỗi chuẩn (400, 401, 403, 404, 409, 429), gồm `409 PRICE_CHANGED` (có bảng tính mới trong `details`) và `409 SHIPMENT_IN_PROGRESS`.
- **`Idempotency-Key`** cho `checkout`, `orders/{code}/payments`, `stock/inbound`, `stock/adjust`, `stock/count`: thiếu key; gửi lại cùng key thì nhận lại đúng kết quả cũ; cùng key nhưng body khác thì ra `IDEMPOTENCY_CONFLICT`. Key lưu ở `shared_idempotency_key` (PostgreSQL), nên vẫn đúng khi Redis không chạy.
- **Còn xử lý:** hai request đồng thời cùng key chỉ có một operation_id/Payment; request còn lại nhận 202 PAYMENT_INITIALIZING. Khác body luôn 409, kể cả khi key in_progress. Purge không xoá key chưa rõ kết quả. Checkout commit kết quả key cùng Order, rollback không để Order mồ côi.
- **Throttle**: endpoint có throttle chặt (ví dụ `orders/lookup`) trả `429` khi vượt ngưỡng. Throttle theo `X-Client-IP` chỉ khi `X-BFF-Secret` đúng; thiếu hoặc sai secret thì bỏ qua `X-Client-IP` và throttle theo IP của kết nối ([ADR 0009](../adr/0009-nextjs-bff-django-private.md)).
- **Redis lỗi**: cache và throttle fail-open, request vẫn được xử lý ([10-nfr.md](./10-nfr.md) mục 2).
- **N+1 query**: `django-zeal` bật cho toàn bộ test; test fail nếu có N+1.

### 2.5. Bảo mật auth/JWT

Kịch bản bắt buộc nằm ở [05-auth-security.md](./05-auth-security.md) mục 9; test đặt ở `modules/identity/tests/test_services_tokens.py` và test API của `identity`.

### 2.6. Adapter nhà cung cấp

Kịch bản bắt buộc (chữ ký, HTTP lỗi, IPN/webhook, khởi tạo thanh toán, tạo và huỷ Vận đơn, cache phí, observation key) nằm ở [06-integrations.md](./06-integrations.md) mục 9.

### 2.7. Flow xuyên module

Flow test gọi qua **HTTP** (`api_client`, `staff_client`, endpoint IPN của Fake Gateway), để đi qua đúng auth, `X-Lookup-Token`, `Idempotency-Key` và serializer như thực tế. Các bước do Celery Beat kích hoạt thì dùng `time-machine` để vượt mốc thời gian, rồi gọi thẳng task (ví dụ `ordering.cancel_expired_pending_orders`, `ordering.complete_delivered_orders`). Đánh dấu bằng `@pytest.mark.flow`.

Sau mỗi bước HTTP, flow test gọi `drain_events()` trong `shared/testing/events.py`. Hàm chạy các callback `on_commit` đang chờ, relay rồi handler (Celery chạy đồng bộ), và lặp tới khi không còn delivery tới hạn. Không chờ retry tương lai; test retry dùng time-machine tiến tới hạn rồi drain tiếp. Ví dụ sau IPN thành công, nó đưa `payments.payment-succeeded` tới handler của `ordering` để chạy T3; sau khi bàn giao, nó chạy task tạo Vận đơn và đưa `shipping.shipment-created` tới T10. Test riêng về mất task và worker dùng các điểm dừng/mô phỏng lỗi, không dựa vào eager mode để chứng minh broker bền vững.

Bắt buộc có 6 flow:

| Flow | Nội dung |
|---|---|
| `test_cod_checkout_flow.py` | Checkout COD → Thanh toán COD `pending` → bàn giao, Vận đơn được tạo → Đã giao, Thanh toán COD `succeeded` → Hoàn tất sau 7 ngày |
| `test_online_payment_success_flow.py` | Checkout online → Giữ hàng 15 phút, link thanh toán hết hạn sau 10 phút → IPN thành công → trừ Tồn kho, ghi `ordering.order-placed` → giao → Hoàn tất |
| `test_online_payment_failure_flow.py` | IPN thất bại, hoặc không ai trả tiền và Giữ hàng hết hạn sau 15 phút → đơn huỷ, Số lượng bán được và lượt Voucher được trả lại |
| `test_cancel_paid_order_flow.py` | Huỷ Đơn hàng đã thanh toán online → Hoàn tiền về đúng Cổng thanh toán đã nhận tiền |
| `test_returned_to_sender_flow.py` | Giao thất bại → Hoàn hàng → Staff xác nhận hàng về Kho → nhập lại Tồn kho; với đơn COD, Thanh toán COD chuyển `cancelled` |
| `test_return_refund_flow.py` | Đổi trả một phần được chấp nhận theo từng dòng (BR-RET-08) → Hoàn tiền đúng số tiền theo BR-RET-07 → Đổi trả chuyển `refunded` khi có `payments.refund-recorded`; Đơn hàng chỉ Hoàn tất khi không còn Đổi trả nào mở |

### 2.8. Kịch bản bắt buộc nằm ở đâu

12 giữ nguyên tắc, loại test, kịch bản nghiệp vụ dễ sai (mục 2.1, gắn marker `br`), concurrency, handler chuyển trạng thái đơn và flow. Kịch bản kỹ thuật nằm cạnh thiết kế của chúng, để khi đổi thiết kế thì sửa test cùng chỗ:

| Chủ đề | Nằm ở |
|---|---|
| Ràng buộc dữ liệu, thời gian, chuẩn hoá số điện thoại, consent, audit | [03-data-model.md](./03-data-model.md) mục 11 |
| JWT, refresh token, BFF, cache auth, redirect, throttle đăng nhập | [05-auth-security.md](./05-auth-security.md) mục 9 |
| Adapter, IPN/webhook, khởi tạo thanh toán, Vận đơn, cache phí | [06-integrations.md](./06-integrations.md) mục 9 |
| Outbox, consumer, relay, email, xoá dữ liệu, job theo lịch | [07-async-events-jobs.md](./07-async-events-jobs.md) mục 5 |

Ticket trong `.scratch/` trỏ về các mục này thay vì chép lại kịch bản.

## 3. Marker của pytest

Khai báo trong `pyproject.toml` (`--strict-markers`):

| Marker | Ý nghĩa | Dùng để |
|---|---|---|
| `br("BR-XXX-NN", ...)` | Test kiểm tra một hay nhiều business rule | Lọc test theo quy tắc; `make br-report` |
| `concurrency` | Test chạy nhiều thread, cần `transaction=True` | `pytest -m concurrency` |
| `flow` | Flow xuyên module | `pytest -m flow` |

`make br-report` liệt kê các mã `BR-xxx` trong `04-business-rules.md` chưa có test nào gắn marker `br`. Lệnh này chỉ để xem, **không** chặn CI, vì nhiều quy tắc chưa có code.

## 4. Dữ liệu test và ranh giới module

Khi bootstrap, kiểm tra cấu hình import-linter bằng các package mẫu tạm: import contracts đúng chiều qua; service import model module khác fail; FK giữa model đúng chiều qua; import cùng lớp hoặc ngược chiều fail. Generator phải liệt kê đủ phần nội bộ thực sự tồn tại và bắt cấu hình cũ trong CI. Không coi việc lint-imports chạy qua trên package rỗng là đã chứng minh ranh giới.

- Dữ liệu test tạo bằng `factory-boy`, không dùng fixture JSON.
- Test kiểm nội dung log (không lộ IP, email, secret) đọc output của chuỗi processor thật qua fixture `json_logging`; `structlog.testing.capture_logs` thay cả chuỗi nên bỏ qua `merge_contextvars` và không thấy key do middleware gắn.
- Fixture không cần nghiệp vụ (ví dụ `api_client`) ở `shared/testing/fixtures.py`. Fixture phải tạo Tài khoản (`customer_client`, `staff_client`, `admin_client`) ở `backend/conftest.py`, vì `shared` không được import `modules.identity`. Tới khi có JWT ở M1, `staff_client`/`admin_client` gọi `force_authenticate(user=…, token={"aud": "backoffice"})` để qua `IsStaff`/`IsAdmin`; `customer_client` thêm ở M6.
- Mỗi module để factory ở `modules/<module>/tests/factories.py`.
- Test trong một module chỉ dùng factory của chính module đó và của các module lớp dưới, theo đúng chiều phụ thuộc trong [02-backend-structure.md](./02-backend-structure.md) mục 4. Ví dụ test của `ordering` dùng được factory của `catalog` và `inventory`; test của `inventory` không dùng được factory của `ordering`.
- `backend/tests/flows/` được dùng factory của mọi module.
- Contract `layers` của `import-linter` đã giữ quy tắc này, không cần contract riêng: test của `inventory` import factory của `ordering` là import ngược lớp. `backend/tests/` không thuộc `root_packages` nên không bị kiểm tra.
- Muốn kiểm tra dữ liệu của module khác (ví dụ Tồn kho sau khi đặt Đơn hàng), test gọi `contracts` của module đó, **không** import `models`, `services`, `selectors` của module đó. Test tuân theo cùng ranh giới như code thật ([02-backend-structure.md](./02-backend-structure.md) mục 8).

## 5. Hợp đồng API với frontend (OpenAPI)

- Schema được commit tại `backend/openapi.yaml`, sinh bằng `manage.py spectacular --validate --file openapi.yaml`. Frontend sinh TS client từ file này.
- CI sinh lại schema và fail nếu khác file đã commit. Vì vậy mọi thay đổi API đều hiện trong diff của PR.
- Chưa dùng công cụ phát hiện breaking change (`oasdiff`). Reviewer tự đọc diff của `openapi.yaml`; diff có xoá field hay endpoint thì PR phải nêu rõ và báo cho frontend.

## 6. Migration

- Migration chỉ đổi schema: không cần test; `makemigrations --check` và kiểm tra trùng số trong CI là đủ.
- Data migration (có `RunPython`): bắt buộc có test bằng `django-test-migrations`, chạy migration trên dữ liệu mẫu rồi kiểm tra kết quả.

## 7. Sandbox thật của nhà cung cấp

CI không gọi sandbox thật, vì repo là public (không đưa secret sandbox vào CI) và sandbox của nhà cung cấp hay lỗi ngẫu nhiên. Kiểm tra với sandbox VNPay, MoMo, GHN là **checklist chạy tay trên staging trước mỗi release**, theo kịch bản ở [06-integrations.md](./06-integrations.md) mục 8.

## 8. Cổng chặn trong CI

Job `backend` trong `.github/workflows/ci.yml`:

| Cổng | Điều kiện để qua |
|---|---|
| `ruff check`, `ruff format --check` | Không lỗi |
| `mypy` | Không lỗi (`--strict` cho `services`, `selectors`, `contracts`) |
| `lint-imports` | Không vi phạm ranh giới module, kể cả quy tắc factory (mục 4) |
| `pytest` | Toàn bộ test qua, kể cả `concurrency` và `flow`. Chạy `pytest -n auto --cov=modules --cov=shared --cov-report=` (`pytest-cov` gom coverage từ các worker của `pytest-xdist`) |
| Coverage | Sau test, chạy `python scripts/check_module_coverage.py`: ≥ 80% **branch coverage riêng** (`[tool.coverage.run] branch = true`) cho nhóm `modules/<module>/services/**/*.py` + `modules/<module>/handlers.py` của **từng module**. Hạ tầng `shared/events/**/*.py` (bỏ các thư mục `tests`), `shared/api/idempotency.py`, `shared/tasks.py` là một nhóm riêng. Script đọc `.coverage` bằng API public `Coverage.branch_stats`, cộng số nhánh đã chạy/tổng số nhánh theo nhóm và so số nguyên với 80%; không dùng tỷ lệ gộp dòng + nhánh của `coverage report --fail-under`. Module chưa có target được bỏ qua, target không có nhánh được báo rõ và qua; file chưa chạy vẫn được phân tích. Thiếu dữ liệu hoặc dữ liệu chỉ đo statement là lỗi. Không tính `shared/geo`, `shared/health` và phần định dạng của `shared/api`, vì ít nhánh nghiệp vụ. **Không** đặt ngưỡng cho toàn repo, để không ai phải viết test chỉ để lấp số |
| Migration | `makemigrations --check`, không trùng số |
| OpenAPI | Schema sinh ra trùng với `backend/openapi.yaml` |
| `pip-audit` | Không có lỗ hổng |

## 9. Chưa làm ở MVP

| Việc | Khi nào làm |
|---|---|
| Test tải theo [10-nfr.md](./10-nfr.md) mục 1 (p95 300/800 ms, 50 request/giây khi khuyến mãi), chạy bằng k6 trên staging | Trước đợt khuyến mãi lớn đầu tiên |
| `oasdiff` phát hiện breaking change của OpenAPI | Khi API có client ngoài frontend của team (ví dụ mobile app) |
| E2E qua trình duyệt | Thuộc repo frontend |

Ở MVP, hiệu năng chỉ được bảo vệ bằng `django-zeal` (N+1 query) và test concurrency (mục 2.2).
