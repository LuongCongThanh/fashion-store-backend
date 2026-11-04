# 12. Chiến lược test

> Trạng thái: **Đã chốt cho MVP** ([quy ước](../../README.md#trạng-thái-tài-liệu)). Phạm vi: chỉ backend Django. Frontend Next.js là repo riêng ([ADR 0001](../adr/0001-nextjs-frontend-django-api.md)) và tự có chiến lược test; ở đây chỉ nói phần backend cam kết với frontend (OpenAPI, mục 5).

Quy ước viết code test (factory, mock, thời gian) nằm ở [13-python-django-coding-style.md](./13-python-django-coding-style.md) mục 9. Cách chạy test ở máy local xem [08-local-development.md](./08-local-development.md) mục 5.

## 1. Nguyên tắc

- Test chạy trên **PostgreSQL thật** (`test_fashion`, pytest-django tự tạo); không SQLite, không mock ORM, vì nghiệp vụ dựa vào `select_for_update`, `EXCLUDE`, `unaccent`.
- Chỉ giả lập **hệ thống bên ngoài**: Fake Gateway cho thanh toán và vận chuyển ([ADR 0005](../adr/0005-provider-adapters-fake-gateways.md)), `respx` cho `httpx`.
- `settings/test.py` bật `FAKE_PROVIDERS_ENABLED=true` (cùng cờ với local) cho Fake Gateway và `FakeShippingProvider`, nên flow test gọi được trang và endpoint IPN của Fake Gateway. CI không gọi sandbox thật VNPay, MoMo, GHN (mục 7).
- Celery chạy đồng bộ (`CELERY_TASK_ALWAYS_EAGER=True` trong `settings/test.py`); thời gian cố định bằng `time-machine`.
- Transaction của test không bao giờ commit: task đẩy bằng `shared.tasks.enqueue_on_commit` không tự chạy, relay (tiến trình riêng) không tự gửi sự kiện. Test service cần task chạy dùng `django_capture_on_commit_callbacks(execute=True)`; flow test dùng `drain_events()` (mục 2.7).
- Nghiệp vụ test ở tầng **service**; tầng API chỉ test phần thuộc HTTP, không test lại nghiệp vụ.
- Repo là public: dữ liệu mẫu phải là giá trị giả rõ ràng ([11-git-workflow.md](./11-git-workflow.md) mục 8).

## 2. Các loại test

- Bảng xếp theo số lượng, nhiều đến ít. Hàm thuần không cần DB (ví dụ `Money`, kiểm tra chữ ký) xếp vào loại của module chứa nó.
- Test nằm trong `tests/` của app sở hữu, **đường dẫn test soi gương đường dẫn code**, thêm `test_` trước tên file ([02 mục 4.4](./02-backend-structure.md#44-test-đặt-ở-đâu-tên-là-gì)); cột "Đặt ở" áp quy tắc này.

| # | Loại | Đặt ở | Kiểm tra gì |
|---|---|---|---|
| 1 | Service | `apps/<module>/tests/test_services.py` hoặc `tests/services/test_<file>.py` | Business rule, chuyển trạng thái, sự kiện ghi vào outbox |
| 2 | Concurrency | `apps/<module>/tests/concurrency/test_<chủ đề>.py` | Không bán vượt Tồn kho, không vượt lượt Voucher, không deadlock |
| 3 | Handler và outbox | `apps/<module>/tests/test_handlers.py`, `common/tests/events/` | Mỗi sự kiện chỉ xử lý một lần, sự kiện tới sai thứ tự, consumer xử lý đúng từng loại lỗi, relay gửi đúng và gửi lại được |
| 4 | API | `apps/<module>/tests/api/<store\|backoffice\|webhooks>/test_views.py` | Phân quyền, `X-Lookup-Token`, định dạng lỗi, `Idempotency-Key`, throttle theo `X-Client-IP`, N+1 query |
| 5 | Bảo mật auth/JWT | `apps/identity/tests/auth/test_tokens.py` | Theo OWASP JWT Cheat Sheet |
| 6 | Adapter nhà cung cấp | `infrastructure/tests/<payment\|shipping\|google>/test_<tên>.py` | Chữ ký VNPay/MoMo, gọi HTTP lỗi, IPN bất thường |
| 7 | Flow xuyên module | `tests/flows/test_<flow>_flow.py` | Một luồng nghiệp vụ đi hết từ đầu đến cuối qua HTTP |

Ngoài pytest, CI còn có **cổng kiểm tra tĩnh** (mục 8).

### 2.1. Service

- Mỗi public service function có bằng chứng cho happy path và từng hành vi lỗi contract công bố. Ưu tiên service test; dùng flow test khi đó là cấp duy nhất chứng minh đúng hành vi mà không lặp setup lớn.
- Test kiểm một quy tắc trong [04-business-rules.md](../business/04-business-rules.md) gắn marker `br` (mục 3).
- Service ghi đúng sự kiện vào outbox; service lỗi thì không sự kiện nào được ghi (cùng transaction).
- Mốc thời gian (Giữ hàng 15 phút, Hoàn tất sau 7 ngày, Đổi trả trong 7 ngày) dùng `time-machine`, test cả hai phía mốc.

```python
@pytest.mark.br("BR-INV-02")
def test_reserve_stock_fails_when_stock_is_insufficient(stock_item_factory):
    ...
```

Bắt buộc có các test service sau cho **kịch bản nghiệp vụ dễ sai**; kịch bản kỹ thuật ở tài liệu sở hữu hành vi đó (mục 2.8).

Selector tìm Sản phẩm (BR-CAT-13, PostgreSQL thật):

- `ao thun`, `áo thun`, `ÁO THUN`, `  ao thun  ` cho cùng kết quả; `basic` khớp một phần tên; `ao thnu` và `thun ao` không khớp "Áo thun Basic cổ tròn".
- Từ khoá rỗng/chỉ khoảng trắng, 1–2 ký tự; `%`/`_`/ký tự escape tìm như ký tự thường; Sản phẩm không `active` bị loại; bộ lọc/sắp xếp vẫn áp dụng.
- Không kiểm việc luôn dùng GIN index (execution plan phụ thuộc dữ liệu và độ dài từ khoá).

| Kịch bản | Kỳ vọng |
|---|---|
| Tổng tính lại khác `expected_total` (Giá khuyến mãi vừa hết hạn, Voucher vừa hết lượt) (BR-ORD-07) | `PriceChanged` (`PRICE_CHANGED`) kèm bảng tính mới; không tạo đơn, Giữ hàng hay lượt Voucher |
| Quote token gắn với báo giá Người mua đã xem | Token giả/sửa/sai chữ ký/đổi subject hoặc input → 400 INVALID_QUOTE; hết hạn → 409 QUOTE_EXPIRED; giá/snapshot đổi dù tổng không đổi → PRICE_CHANGED. Token không Giữ hàng, không cố định giá; quote mới dùng token/key mới |
| Hai checkout cùng giỏ | Khoá Cart trước StockItem; lần đầu tạo Order, xoá dòng đã mua, lưu idempotency cùng transaction. Cùng key replay trả cùng Order kể cả token hết hạn; key khác không đặt lại giỏ đã xoá; thêm/sửa/merge cart đồng thời không mất dòng mới, không dùng snapshot giỏ sai |
| Tổng tiền đơn ≤ 0 (BR-ORD-09) | Quote và checkout, COD và online, trả `422 ORDER_TOTAL_NOT_POSITIVE`; không tạo Order, Payment, Giữ hàng, Hàng chờ xuất, lượt Voucher. Ghi trực tiếp `total = 0` bị CHECK chặn; 1đ vẫn hợp lệ |
| Làm tròn Voucher theo % (BR-VCH-10) | Tạm tính 1.001đ, giảm 10% → 100đ; rồi mới áp mức giảm tối đa và giới hạn bằng Tạm tính; không float |
| Phân bổ Voucher về Dòng đơn hàng (BR-ORD-02) | Sắp theo `variant_id`; 500đ và 501đ, giảm 100đ → 49đ, 51đ, đảo thứ tự request không đổi. Ba dòng 1đ, giảm 2đ → 0đ, 1đ, 1đ. Tổng phân bổ đúng số giảm, không vượt từng dòng |
| Hoàn tiền khi Đổi trả một phần có Voucher (BR-RET-07) | Đơn 3 × 200.000đ, Voucher giảm 60.000đ, được miễn phí ship; trả 1 áo → hoàn 180.000đ, không truy thu phí ship |
| Hoàn tiền có phần lẻ qua nhiều lần (BR-RET-07) | Dòng 3 × 100đ, Voucher phân bổ 1đ: trả từng cái → 99đ, 100đ, 100đ; cả dòng một lần → 299đ. Tính cả số đã chấp nhận có Refund còn `requested`, không tính phần bị từ chối. Hai accept đồng thời tuần tự hoá dưới khoá Order |
| Đổi trả được chấp nhận nhưng hoàn 0đ (BR-RET-07) | Dòng 2 × 1đ, Voucher phân bổ 1đ: trả cái đầu → 0đ, yêu cầu `refunded` với `refund_id = NULL`, nhập kho đúng lựa chọn, không Refund/sự kiện Hoàn tiền; cái còn lại → 1đ. Accept lặp không nhập kho lại; không chấp nhận cái nào vẫn `rejected` |
| Giới hạn lượt dùng Voucher mỗi người (BR-VCH-07) | Khách hàng đã dùng hết lượt rồi đặt tiếp như Khách vãng lai bằng cùng số điện thoại → Voucher bị từ chối |
| Staff huỷ đơn PACKING khi Vận đơn requested hoặc creation_unknown (T9) | Ném SHIPMENT_IN_PROGRESS, giữ PACKING; không cho bàn giao lại để tạo mã mới |
| Thanh toán của đơn COD | T2 tạo `pending`; T11 → `succeeded`; huỷ đơn hoặc Hoàn hàng → `cancelled`. Không ghi `payments.payment-succeeded` vào outbox, nên đơn COD giao xong không bị tạo Hoàn tiền |
| Hàng chờ xuất (BR-INV-10) | Đặt đơn COD: Tồn kho giảm, Hàng chờ xuất tăng đúng số lượng; T10 xoá; huỷ trước Bàn giao (T7, T9) trả về Tồn kho |
| Kiểm kê (BR-INV-12) | Tồn kho 7, Hàng chờ xuất 3, số đếm 10 → không điều chỉnh; số đếm 9 → điều chỉnh −1 loại `stock_count` |
| Điều chỉnh giảm vượt Số lượng bán được (BR-INV-11) | Ném `INSUFFICIENT_AVAILABLE`; Tồn kho không đổi |
| Giữ hàng quá `expires_at` nhưng job chưa giải phóng | `reserve_stock` của Người mua khác thành công; Giữ hàng cũ `released`, `reserved` giảm tương ứng |
| Job T4 khi `shared.events.delivery_lag()` quá 60 giây | Không huỷ đơn, log `cancel_skipped_delivery_backlog`; hết tồn đọng thì lượt sau huỷ bình thường. Bỏ lượt liên tục quá 15 phút → cảnh báo `cancel_skipped_too_long`, vẫn không huỷ |
| Bắt đầu Thanh toán online ở phút 6:59 và phút 7:00 kể từ khi đặt đơn (BR-INV-05) | 6:59 tạo được Thanh toán; 7:00 ném `PaymentWindowClosed` (`PAYMENT_WINDOW_CLOSED`) |
| `raise_flag` khi đơn đã có cờ cùng `kind` đang mở | Không tạo cờ thứ hai, `note` được nối thêm |
| `placed_at`, `cancelled_at`, `completed_at` | Ghi đúng ở transition tương ứng (T2/T3, T4/T5/T7/T9/T14, T13); báo cáo Doanh thu lọc theo `completed_at` (BR-REV-01) |
| Staff huỷ đơn `SHIPPING` (T14) | Chỉ khi có cờ `shipment_exception`, bắt buộc lý do; Hoàn tiền toàn bộ nếu đã thanh toán online; không trả lượt Voucher |
| Nhập lại sau T12/T14 | T12 đặt `warehouse_return_required = true`; T14 thiếu xác nhận boolean bị từ chối, hàng chưa rời Kho → true nhưng chưa tăng tồn, hàng mất/hư → false. Endpoint nhập lại chỉ cho đơn có cờ; nhập kho và ghi mốc cùng transaction. Request đồng thời hoặc retry chỉ cộng tồn một lần; T7/T9 đã release allocation không nhập thêm; danh sách chờ nhập gồm đúng T12/T14 cần xử lý |
| Chấp nhận Đổi trả một phần (BR-RET-08) | Chỉ `accepted_quantity` của dòng `restock = true` cộng lại Tồn kho; Hoàn tiền tính trên số được chấp nhận; không dòng nào được chấp nhận → `rejected` |
| Doanh thu khi Người mua trả tiền hai lần (BR-REV-01) | Hoàn tiền theo BR-PAY-05 không bị trừ; Doanh thu của đơn bằng Tổng tiền đơn |
| Đặt đơn vãng lai bằng email của Tài khoản đã xác thực (BR-ORD-08) | Đơn có `customer_id` ngay khi tạo |
| Hạ Giá bán xuống ≤ Giá khuyến mãi đang hoặc sắp hiệu lực (BR-PRC-05) | Ném `LIST_PRICE_BELOW_SALE_PRICE`; Giá bán không đổi |
| Giá, snapshot, trạng thái bán hoặc SalePrice đổi sau lần đọc báo giá ngoài transaction | Checkout kiểm lại dưới khoá Variant; rollback Order, Giữ hàng, lượt Voucher; trả PRICE_CHANGED với quote mới dù tổng tình cờ không đổi |

### 2.2. Concurrency

- Dùng `@pytest.mark.django_db(transaction=True)` và `@pytest.mark.concurrency`: N thread, mỗi thread một kết nối DB, xuất phát cùng lúc bằng `threading.Barrier`, kiểm bất biến khi tất cả kết thúc (mẫu ở mục 2.9.3).
- Chạy trong **mọi PR**, vì mỗi worker `pytest-xdist` có DB riêng.
- Test cần Redis thật (failure ledger đăng nhập) dùng fixture `ledger_redis` của identity: lấy `REDIS_URL` chuyển sang DB 15, key ngẫu nhiên theo test nên xdist không đụng nhau và không flush DB.
- Thiếu Redis thì test fail rõ, không skip; CI có service Redis. Chạy trên máy thì `REDIS_URL` trỏ Redis của Compose (`redis://localhost:6380/0`, 08 mục 2.3).

Bắt buộc có các test:

| Kịch bản | Bất biến |
|---|---|
| N khách cùng Giữ hàng hoặc trừ Tồn kho K cái cuối của một Biến thể (N > K) | Đúng K thành công, N − K `OUT_OF_STOCK`, Tồn kho không âm |
| N khách cùng dùng một Voucher còn K lượt | Đúng K lượt được dùng, không vượt `usage_limit` |
| Hai Đơn hàng cùng 2 Biến thể, thứ tự Dòng đơn hàng ngược nhau, cùng một Voucher | Cả hai hoàn tất, không deadlock (khoá Tồn kho theo `variant_id`, rồi toàn bộ Biến thể theo id để kiểm snapshot, rồi mới khoá Voucher) |
| Hai yêu cầu hoàn khác key đồng thời trên một Payment, tổng vượt tiền thực nhận | Chỉ yêu cầu trong hạn mức thành công; requested + completed không vượt amount_received |
| Hai yêu cầu hoàn cùng payment_id và request_key | Chỉ một Refund được tạo, cả hai trả cùng refund_id; khác tham số bị từ chối |
| Checkout song song đổi Giá bán hoặc thêm/sửa/xoá SalePrice | Writer và checkout đều khoá Variant; đơn dùng snapshot đã xác thực hoặc rollback PRICE_CHANGED, không lọt giá đọc trước khi writer commit |
| Hai checkout nhiều Biến thể, availability đổi ở các Biến thể khác nhau | Khoá toàn bộ StockItem rồi toàn bộ Variant theo id trước khi đổi availability; không khoá một phần Variant trước phần còn lại |
| T3 tới muộn (Giữ hàng vừa quá hạn) tranh hàng với checkout của người khác | Đúng một bên được hàng, Tồn kho không âm; bên thua nhận `OUT_OF_STOCK` hoặc đi nhánh Hoàn tiền |
| N request đăng nhập sai đồng thời cùng email (N > 5) | Failure ledger không cấp quá 5 suất, còn lại `429` (05 mục 5). Chạy Lua trên Redis thật |
| Người mua tự huỷ (T5) đúng lúc IPN thành công (T3) cùng đơn | Chỉ một transition chạy trên `PENDING_PAYMENT` (khoá dòng Đơn hàng); T5 thắng thì tiền về xử lý theo BR-PAY-05 |

### 2.3. Handler và outbox

- Mỗi handler: gọi 2 lần cùng một sự kiện chỉ xử lý 1 lần (delivery đã `completed`).
- Kịch bản hạ tầng sự kiện (consumer, relay, retry, purge, replay, email, xoá dữ liệu, `delivery_lag`, lịch job) và test payload không chứa PII: [07-async-events-jobs.md](./07-async-events-jobs.md) mục 5.

Bắt buộc có các test handler sau:

| Kịch bản | Kỳ vọng |
|---|---|
| `payments.payment-succeeded` của khoản trả thêm khi đơn đã `PLACED`, hoặc khi đơn đã `CANCELLED` (BR-PAY-05) | Đơn giữ nguyên; Hoàn tiền gắn đúng payment_id của sự kiện, key ổn định không suy từ Mã đơn; gắn cờ unexpected_payment và phát sự kiện |
| Sự kiện thành công mới mang cùng payment_id đã dùng đưa đơn vào PLACED | Không tạo Hoàn tiền, không phát thêm OrderPlaced hay UnexpectedPaymentReceived |
| Đơn có hai Thanh toán online cùng số tiền qua hai gateway | Lưu đúng payment_id của đơn; Hoàn tiền khoản trả thêm đúng khoản và gateway, không hoàn nhầm khoản ban đầu |
| `payments.payment-failed` với `reason = amount_mismatch` (BR-PAY-04) | Tạo yêu cầu Hoàn tiền đúng `amount_received`; gắn cờ `payment_amount_mismatch`; đơn giữ `PENDING_PAYMENT` |
| `payments.refund-recorded` cho Hoàn tiền không gắn Đổi trả nào | Không Đổi trả nào đổi trạng thái |
| `ordering.order-cancelled` với `previous_status = PENDING_PAYMENT` (T4, T5) | notifications không gửi email (BR-NTF-01) |
| `shipping.shipment-created` tới khi đơn đã `CANCELLED` | Gọi `shipping.contracts.request_shipment_cancellation` (Vận đơn `cancel_requested`); gắn Cờ cần xử lý `shipment_after_cancel` |
| `shipping.shipment-delivered` tới khi đơn còn `PACKING` (T10 chưa chạy) | Ném `TransitionNotYetValid`; đơn giữ nguyên |
| `shipping.shipment-delivered` tới khi đơn đã `DELIVERED` hoặc `COMPLETED` | Không làm gì, không ném lỗi |
| `shipping.shipment-delivered` tới khi đơn đã `RETURNED_TO_SENDER` | Ném `InvalidTransition`; đơn giữ nguyên |
| `payments.payment-succeeded` khi đơn `PENDING_PAYMENT`, Giữ hàng quá `expires_at`, Số lượng bán được còn đủ | Đơn vào `PLACED`; Tồn kho giảm, Hàng chờ xuất tăng đúng số lượng; không Hoàn tiền |
| `payments.payment-succeeded` khi đơn `PENDING_PAYMENT`, Giữ hàng quá hạn, hàng đã bị người khác mua | `commit_reservation` ném `ReservationExpired`; chạy T4 (`CANCELLED`) rồi tạo Hoàn tiền, gắn cờ `unexpected_payment` |
| `shipping.shipment-exception` | Gắn cờ `shipment_exception`; đơn giữ `SHIPPING` |
| `identity.email-verified` | Chỉ gắn đơn có `contact_email` khớp (không phân biệt hoa thường) và chưa có `customer_id`; đơn của Tài khoản khác không bị đổi |
| Đặt đơn online (T1) rồi IPN thành công (T3) | T1 không ghi sự kiện nào vào outbox; T3 ghi đúng một `ordering.order-placed` |

**Hoàn tiền (BR-REF-06):** test gọi lại cùng key/cùng tham số, key trùng khác tham số, vượt tiền thực nhận, hoàn tất lặp không phát thêm RefundRecorded. Callback IPN/đối soát trùng không cộng amount_received lần nữa.

### 2.4. API

- **Phân quyền**: mỗi endpoint thử Guest, Customer, Staff, Admin (cột quyền trong [04-api-contract.md](./04-api-contract.md)); Khách hàng không xem được Đơn hàng của Khách hàng khác.
- **`X-Lookup-Token`**: `GET orders/{code}`, `POST orders/{code}/payments`, `POST orders/{code}/cancel` của Khách vãng lai bị từ chối khi thiếu token, token hết hạn hoặc của đơn khác. `lookup_token` trả từ checkout của Khách vãng lai dùng được ngay cho ba endpoint này.
- JWT, BFF, cache auth: [05](./05-auth-security.md) mục 9. ACK webhook, khởi tạo thanh toán, gọi HTTP ngoài transaction: [06](./06-integrations.md) mục 9.
- **Lỗi**: đúng mã HTTP và định dạng lỗi chuẩn (400, 401, 403, 404, 409, 429), gồm `409 PRICE_CHANGED` (bảng tính mới trong `details`) và `409 SHIPMENT_IN_PROGRESS`.
- **`Idempotency-Key`** cho `checkout`, `orders/{code}/payments`, `stock/inbound`, `stock/adjust`, `stock/count`: thiếu key; cùng key trả đúng kết quả cũ; cùng key khác body ra `IDEMPOTENCY_CONFLICT`. Key lưu ở `shared_idempotency_key` (PostgreSQL), nên vẫn đúng khi Redis không chạy.
- **Còn xử lý:** hai request đồng thời cùng key chỉ có một operation_id/Payment, request kia nhận 202 PAYMENT_INITIALIZING. Khác body luôn 409, kể cả key in_progress. Purge không xoá key chưa rõ kết quả. Checkout commit kết quả key cùng Order; rollback không để Order mồ côi.
- **Throttle**: endpoint throttle chặt (ví dụ `orders/lookup`) trả `429` khi vượt ngưỡng. Chỉ throttle theo `X-Client-IP` khi `X-BFF-Secret` đúng; thiếu/sai secret thì throttle theo IP kết nối ([ADR 0009](../adr/0009-nextjs-bff-django-private.md)).
- **Redis lỗi**: cache và throttle fail-open, request vẫn xử lý ([10-nfr.md](./10-nfr.md) mục 2).
- **N+1 query**: `django-zeal` bật cho toàn bộ test; có N+1 thì fail.

### 2.5. Bảo mật auth/JWT

Kịch bản: [05-auth-security.md](./05-auth-security.md) mục 9. Test đặt ở `apps/identity/tests/auth/test_tokens.py` và test API của `identity`.

### 2.6. Adapter nhà cung cấp

Kịch bản (chữ ký, HTTP lỗi, IPN/webhook, khởi tạo thanh toán, tạo và huỷ Vận đơn, cache phí, observation key): [06-integrations.md](./06-integrations.md) mục 9.

### 2.7. Flow xuyên module

- Gọi qua **HTTP** (`api_client`, `staff_client`, endpoint IPN của Fake Gateway) để đi qua đúng auth, `X-Lookup-Token`, `Idempotency-Key` và serializer. Đánh dấu `@pytest.mark.flow`.
- Bước do Celery Beat kích hoạt: dùng `time-machine` vượt mốc rồi gọi thẳng task (ví dụ `ordering.cancel_expired_pending_orders`, `ordering.complete_delivered_orders`).
- Sau mỗi bước HTTP gọi `drain_events()` (`common/events/testing.py`): chạy callback `on_commit` đang chờ, relay rồi handler (Celery đồng bộ), lặp tới khi hết delivery tới hạn. Ví dụ sau IPN thành công nó đưa `payments.payment-succeeded` tới handler `ordering` chạy T3; sau bàn giao nó chạy task tạo Vận đơn và đưa `shipping.shipment-created` tới T10.
- `drain_events()` không chờ retry tương lai; test retry dùng time-machine tiến tới hạn rồi drain tiếp.
- Test mất task/worker dùng điểm dừng/mô phỏng lỗi, không dựa vào eager mode để chứng minh broker bền vững.

Bắt buộc có 6 flow:

| Flow | Nội dung |
|---|---|
| `test_cod_checkout_flow.py` | Checkout COD → Thanh toán COD `pending` → bàn giao, Vận đơn được tạo → Đã giao, Thanh toán COD `succeeded` → Hoàn tất sau 7 ngày |
| `test_online_payment_success_flow.py` | Checkout online → Giữ hàng 15 phút, link thanh toán hết hạn sau 10 phút → IPN thành công → trừ Tồn kho, ghi `ordering.order-placed` → giao → Hoàn tất |
| `test_online_payment_failure_flow.py` | IPN thất bại, hoặc không trả tiền và Giữ hàng hết hạn sau 15 phút → đơn huỷ, trả lại Số lượng bán được và lượt Voucher |
| `test_cancel_paid_order_flow.py` | Huỷ Đơn hàng đã thanh toán online → Hoàn tiền về đúng Cổng thanh toán đã nhận tiền |
| `test_returned_to_sender_flow.py` | Giao thất bại → Hoàn hàng → Staff xác nhận hàng về Kho → nhập lại Tồn kho; với đơn COD, Thanh toán COD chuyển `cancelled` |
| `test_return_refund_flow.py` | Đổi trả một phần chấp nhận theo dòng (BR-RET-08) → Hoàn tiền đúng BR-RET-07 → Đổi trả `refunded` khi có `payments.refund-recorded`; Đơn hàng chỉ Hoàn tất khi không còn Đổi trả mở |

### 2.8. Kịch bản bắt buộc nằm ở đâu

12 giữ nguyên tắc, loại test, kịch bản nghiệp vụ dễ sai (mục 2.1, marker `br`), concurrency, handler chuyển trạng thái đơn và flow. Kịch bản kỹ thuật nằm cạnh thiết kế để đổi thiết kế thì sửa test cùng chỗ:

| Chủ đề | Nằm ở |
|---|---|
| Ràng buộc dữ liệu, thời gian, chuẩn hoá số điện thoại, consent, audit | [03-data-model.md](./03-data-model.md) mục 11 |
| JWT, refresh token, BFF, cache auth, redirect, throttle đăng nhập | [05-auth-security.md](./05-auth-security.md) mục 9 |
| Adapter, IPN/webhook, khởi tạo thanh toán, Vận đơn, cache phí | [06-integrations.md](./06-integrations.md) mục 9 |
| Outbox, consumer, relay, email, xoá dữ liệu, job theo lịch | [07-async-events-jobs.md](./07-async-events-jobs.md) mục 5 |

Ticket trong `.scratch/` trỏ về các mục này thay vì chép lại kịch bản.

### 2.9. Mẫu test chuẩn

Mẫu minh hoạ cấu trúc và assertion bắt buộc; tên service/model có thể chưa tồn tại. Implementation khác mẫu thì giữ semantics test, dùng API thật của module. Đặt tên, factory, `pytest.raises`, thời gian: [13 mục 9](./13-python-django-coding-style.md#9-test).

#### 2.9.1. Service: chứng minh kết quả và rollback

```python
@pytest.mark.django_db
@pytest.mark.br("BR-INV-02")
def test_reserve_stock_rejects_quantity_above_available(stock_item: StockItem) -> None:
    with pytest.raises(OutOfStock):
        reserve_stock(order_id=uuid7(), variant_id=stock_item.variant_id,
                      quantity=stock_item.on_hand + 1,
                      expires_at=timezone.now() + timedelta(minutes=15))

    stock_item.refresh_from_db()
    assert stock_item.reserved == 0
    assert not StockReservation.objects.exists()
    assert not OutboxEvent.objects.filter(event_type="inventory.stock-reserved").exists()
```

- Chứng minh: đúng domain exception, mọi thay đổi DB rollback, sự kiện không thoát khỏi transaction thất bại.
- Happy path assert giá trị trả về, state bền vững và payload sự kiện, không chỉ "không ném lỗi". Không cần HTTP hay Celery worker.
- Không assert từng lời gọi ORM hay thứ tự helper private: khoá test vào implementation mà không chứng minh thêm hành vi quan sát được.

#### 2.9.2. `on_commit`, task và outbox

Task enqueue sau commit: callback chưa chạy trong transaction, chạy đúng một lần sau commit, bị bỏ khi rollback.

```python
@pytest.mark.django_db
def test_enqueue_runs_only_after_commit(django_capture_on_commit_callbacks: CaptureOnCommit) -> None:
    with (
        mock.patch.object(app.tasks[TASK_NAME], "apply_async") as apply_async,
        django_capture_on_commit_callbacks(execute=True),
        transaction.atomic(),
    ):
        enqueue_on_commit(TASK_NAME, order_id="order-1")
        apply_async.assert_not_called()

    apply_async.assert_called_once_with(kwargs={"order_id": "order-1"})


@pytest.mark.django_db
def test_enqueue_is_discarded_on_rollback(django_capture_on_commit_callbacks: CaptureOnCommit) -> None:
    with (
        mock.patch.object(app.tasks[TASK_NAME], "apply_async") as apply_async,
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(OutOfStock),
    ):
        with transaction.atomic():
            enqueue_on_commit(TASK_NAME, order_id="order-1")
            raise OutOfStock

    assert callbacks == []
    apply_async.assert_not_called()
```

- Service phát domain event: assert dòng `OutboxEvent` trong cùng transaction.
- Chỉ test helper `enqueue_on_commit` mới patch `apply_async` để quan sát broker boundary.
- Handler test chạy consumer thật; flow test dùng `drain_events()`.
- Eager task không phải bằng chứng callback chỉ chạy sau commit.

#### 2.9.3. Concurrency với connection riêng

```python
@pytest.mark.django_db(transaction=True)
@pytest.mark.concurrency
def test_two_reservations_cannot_oversell(stock_item: StockItem) -> None:
    barrier = threading.Barrier(2, timeout=5)
    outcomes: list[str] = []
    errors: list[BaseException] = []

    def run() -> None:
        close_old_connections()
        try:
            barrier.wait()
            reserve_stock(order_id=uuid7(), variant_id=stock_item.variant_id, quantity=1,
                          expires_at=timezone.now() + timedelta(minutes=15))
            outcomes.append("reserved")
        except OutOfStock:
            outcomes.append("out_of_stock")
        except BaseException as exc:
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=run) for _ in range(2)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=10)

    assert not any(t.is_alive() for t in threads)
    assert errors == []
    assert sorted(outcomes) == ["out_of_stock", "reserved"]
    stock_item.refresh_from_db()
    assert stock_item.on_hand - stock_item.reserved == 0
```

- Factory tạo đúng một đơn vị Số lượng bán được.
- `transaction=True` để thread khác thấy dữ liệu setup đã commit; `close_old_connections()` buộc mỗi thread lấy connection riêng; `Barrier` tạo tranh chấp thật.
- Luôn có timeout và thu exception từ thread, nếu không test có thể treo hoặc xanh dù worker đã chết.
- Không dùng `sleep()` để giả định thứ tự; cần điểm dừng xác định thì dùng `Barrier`/`Event`.

#### 2.9.4. Handler và giao sự kiện lặp

```python
@pytest.mark.django_db
def test_payment_succeeded_handler_is_idempotent(
    pending_order: Order, payment_succeeded_event: PaymentSucceededV1
) -> None:
    with transaction.atomic():
        publish(payment_succeeded_event)
    drain_events()

    delivery = EventDelivery.objects.get(
        event_id=payment_succeeded_event.event_id,
        handler="ordering.handle_payment_succeeded",
    )
    dispatch_event.apply_async(args=(str(payment_succeeded_event.event_id), delivery.handler), queue="events")

    pending_order.refresh_from_db()
    delivery.refresh_from_db()
    assert pending_order.status == OrderStatus.PLACED
    assert delivery.status == DeliveryStatus.COMPLETED
    assert Order.objects.filter(id=pending_order.id).count() == 1
    assert OutboxEvent.objects.filter(event_type="ordering.order-placed").count() == 1
```

- Lần giao đầu tạo effect và hoàn tất delivery; lần giao lặp không chạy nghiệp vụ lần nữa.
- Test riêng cho `RetryLater`, `DomainError`, exception bất ngờ assert state nghiệp vụ rollback, trạng thái delivery, `attempts`, `next_attempt_at` và log không chứa PII. Ma trận lỗi: [07 mục 5](./07-async-events-jobs.md#5-kịch-bản-kiểm-thử).

#### 2.9.5. API permission và error contract

```python
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("client_fixture", "expected_status"),
    [
        ("api_client", status.HTTP_401_UNAUTHORIZED),
        ("customer_client", status.HTTP_403_FORBIDDEN),
        ("staff_client", status.HTTP_200_OK),
        ("admin_client", status.HTTP_200_OK),
    ],
)
def test_stock_list_permissions(
    request: pytest.FixtureRequest, client_fixture: str, expected_status: int
) -> None:
    response = request.getfixturevalue(client_fixture).get("/api/v1/backoffice/inventory/stock/")
    assert response.status_code == expected_status
```

- Permission class có unit test cho toàn bộ ma trận `kind`/`aud`; mỗi endpoint vẫn cần integration test chứng minh gắn đúng permission.
- Response lỗi: assert `status`, `code` và shape chuẩn; không snapshot toàn bộ message đã dịch.
- Không lặp lại nhánh nghiệp vụ service test đã chứng minh.

#### 2.9.6. Flow HTTP và `drain_events()`

```python
@pytest.mark.django_db
@pytest.mark.flow
def test_cod_checkout_flow(
    api_client: APIClient, staff_client: APIClient, fake_shipping_provider: FakeShippingProvider
) -> None:
    checkout = api_client.post(
        "/api/v1/store/checkout",
        CHECKOUT_PAYLOAD | {"payment_method": "cod"},
        headers={"Idempotency-Key": "00000000-0000-7000-8000-000000000001"},
        format="json",
    )
    assert checkout.status_code == status.HTTP_201_CREATED
    order_code = checkout.json()["code"]

    drain_events()
    assert get_order_for_test(code=order_code).status == OrderStatus.PLACED

    hand_over = staff_client.post(f"/api/v1/backoffice/orders/{order_code}/hand-over")
    assert hand_over.status_code == status.HTTP_202_ACCEPTED
    drain_events()

    assert get_order_for_test(code=order_code).status == OrderStatus.SHIPPING
    assert fake_shipping_provider.created_references == [order_code]
```

- Đi qua HTTP ở entry point; gọi `drain_events()` sau bước có thể phát event/task.
- Assert mốc nghiệp vụ quan trọng, không chép mọi assertion của service test.
- Đọc module khác qua public test helper/contract (mục 4); không import model nội bộ chỉ vì flow nằm ở `tests/flows/`.

#### 2.9.7. Data migration và database constraint

Data migration test từ state ngay trước migration sang state cần kiểm:

```python
@pytest.mark.django_db(transaction=True)
def test_shipping_settings_data_migration(migrator: Migrator) -> None:
    before = migrator.apply_initial_migration(("modules", "0008_create_shipping_settings"))
    OldSettings = before.apps.get_model("modules", "ShippingSettings")
    assert not OldSettings.objects.exists()

    after = migrator.apply_tested_migration(("modules", "0009_seed_shipping_settings"))
    ShippingSettings = after.apps.get_model("modules", "ShippingSettings")
    settings = ShippingSettings.objects.get(singleton=1)

    assert settings.fallback_fee == 35_000
```

- Tên migration là placeholder; test thật dùng đúng node trong migration graph.
- Dùng model từ `state.apps`, không import model hiện hành.
- Test dữ liệu cũ, giá trị NULL/không hợp lệ, và tính idempotent nếu migration được phép chạy lại.
- Constraint phức tạp cần model/database test ghi trực tiếp dữ liệu sai ([03 mục 0.10.6](./03-data-model.md#0106-test-constraint-tại-database)).
- Đổi type, backfill, raw SQL, extension/function, expand/contract cần test upgrade/reverse theo rủi ro, ngoài `makemigrations --check`. Schema migration thông thường: mục 6.

## 3. Marker của pytest

Khai báo trong `pyproject.toml` (`--strict-markers`):

| Marker | Ý nghĩa | Dùng để |
|---|---|---|
| `br("BR-XXX-NN", ...)` | Test kiểm tra một hay nhiều business rule | Lọc test theo quy tắc; `make br-report` |
| `concurrency` | Test chạy nhiều thread, cần `transaction=True` | `pytest -m concurrency` |
| `flow` | Flow xuyên module | `pytest -m flow` |

`make br-report` liệt kê mã `BR-xxx` trong `04-business-rules.md` chưa có test gắn marker `br`; chỉ để xem, **không** chặn CI vì nhiều quy tắc chưa có code.

## 4. Dữ liệu test và ranh giới module

- Khi bootstrap, kiểm cấu hình import-linter bằng package mẫu tạm: import contracts đúng chiều qua; service import model module khác fail; FK đúng chiều qua; import cùng lớp hoặc ngược chiều fail. Generator liệt kê đủ phần nội bộ thực sự tồn tại và bắt cấu hình cũ trong CI. `lint-imports` qua trên package rỗng không chứng minh ranh giới.
- Dữ liệu test tạo bằng `factory-boy`, không fixture JSON.
- Test nội dung log (không lộ IP, email, secret) đọc output chuỗi processor thật qua fixture `json_logging`. Không dùng `structlog.testing.capture_logs`: nó thay cả chuỗi, bỏ qua `merge_contextvars` và key do middleware gắn. Gọi `logging.config.dictConfig(json_logging)` trong thân test, không ở setup của fixture khác, để `capsys` bắt stderr ở pha call.
- Fixture dùng chung (`api_client`, `customer_client`, `staff_client`, `admin_client`…) ở `conftest.py` gốc repo, nằm ngoài mọi package nên import được cả `common` lẫn `apps.identity`. `customer_client` thêm ở M6.
- `staff_client`/`admin_client` dùng fixture `jwt_keyring` (keyring Ed25519 tạm) và gắn `Authorization: Bearer` bằng access token back-office thật, đi qua `JWTAuthentication` như request thật; không dùng `force_authenticate` để chứng minh JWT.
- Factory module ở `apps/<module>/tests/factories.py`; factory nền (outbox…) ở `common/tests/factories.py`; `drain_events()` ở `common/events/testing.py`.
- Test của module chỉ dùng factory của chính nó và module lớp dưới ([02](./02-backend-structure.md) mục 3): `ordering` dùng được factory `catalog`, `inventory`; `inventory` không dùng được factory `ordering`. `tests/flows/` dùng được factory mọi module.
- Contract `layers` của `import-linter` đã giữ quy tắc trên (import ngược lớp), không cần contract riêng. `tests/` gốc không thuộc `root_packages` nên không bị kiểm.
- Code ngoài `tests` (service, API…) không import factory module khác; `scripts/gen_importlinter.py` sinh contract `forbidden` cho quy tắc này ([02](./02-backend-structure.md) mục 6).
- Kiểm dữ liệu module khác (ví dụ Tồn kho sau khi đặt Đơn hàng) qua `contracts` của module đó, **không** import `models`, `services`, `selectors`; test theo cùng ranh giới như code thật ([02](./02-backend-structure.md) mục 6).

## 5. Hợp đồng API với frontend (OpenAPI)

- Schema commit tại `backend/openapi.yaml`, đọc qua Swagger UI. Frontend chưa sinh TS client, nên `operationId` để drf-spectacular tự sinh; mở ticket đặt tên khi chuyển sang sinh client.
- `make openapi` sinh lại bằng `scripts/gen_openapi.py`: gọi `manage.py spectacular --validate --fail-on-warn` với `config.settings.test` khi chưa đặt `DJANGO_SETTINGS_MODULE` (cùng settings với CI). Cần `--fail-on-warn` vì warning (serializer không đoán được, enum trùng tên) làm schema thiếu mà lệnh vẫn exit 0.
- `scripts/gen_openapi.py --check` chạy trong `make lint` và bước Lint của CI (mục 8), exit 1 khi:
  - schema sai chuẩn OpenAPI hoặc có warning;
  - luật chú thích (hàm thuần `quality_violations` trên schema vừa render, chạy trước bước so drift) thấy operation dưới `/api/v1/` thiếu `summary`, ví dụ request/2xx, ví dụ `ErrorDTO` cho lỗi tự khai, tag sai dạng hoặc chữ tiếng Việt có dấu; in `<operationId>: <thiếu gì>` ([04](./04-api-contract.md) mục 5.6);
  - file đã commit lệch với code: in diff, nhắc chạy `make openapi`.
- Đổi API thì chạy `make openapi` và commit `backend/openapi.yaml` cùng PR, để mọi thay đổi API hiện trong diff.
- `backend/openapi.yaml` là file sinh, không sửa tay. Hook pre-commit `trailing-whitespace`, `end-of-file-fixer` bỏ qua nó để không lệch output generator; SonarCloud cũng bỏ qua (`.sonarcloud.properties`), issue báo ở code Python sinh ra nó.
- Chưa dùng `oasdiff` phát hiện breaking change: reviewer tự đọc diff; xoá field hay endpoint phải nêu rõ và báo frontend.

## 6. Migration

- Schema migration thông thường (`AddField`, `AddIndex`...) không cần migration test riêng; constraint vẫn cần model/database test. Đổi model thì chạy `python manage.py makemigrations --check --dry-run` để phát hiện migration thiếu.
- Data migration (`RunPython`), raw SQL, extension/function, đổi type có dữ liệu, chuỗi expand/contract bắt buộc có migration test bằng `django-test-migrations` (mẫu mục 2.9.7).
- Chưa có gate migration trong `.github/workflows/ci.yml`; chưa tính là required status check cho tới khi có script và job. Khi thêm gate kiểm migration lệch và trùng leaf node, cập nhật đồng thời bảng mục 8 và [11 mục 3.5](./11-git-workflow.md#35-ci-trên-github-actions).

## 7. Sandbox thật của nhà cung cấp

CI không gọi sandbox thật: repo public (không đưa secret sandbox vào CI) và sandbox hay lỗi ngẫu nhiên. Sandbox VNPay, MoMo, GHN là **checklist chạy tay trên staging trước mỗi release**, theo [06-integrations.md](./06-integrations.md) mục 8.

## 8. Cổng chặn trong CI

Job `backend` trong `.github/workflows/ci.yml`:

| Cổng | Điều kiện để qua |
|---|---|
| `ruff check`, `ruff format --check` | Không lỗi |
| `mypy` | Không lỗi (`--strict` cho `services`, `selectors`, `contracts`) |
| `python scripts/gen_importlinter.py --check` | Vùng contract `forbidden` sinh tự động trong `pyproject.toml` khớp cây `modules/`; sửa tay hoặc quên sinh lại thì exit 1 kèm diff ([02](./02-backend-structure.md) mục 6) |
| `lint-imports` | Không vi phạm ranh giới module, kể cả quy tắc factory (mục 4) |
| `python scripts/gen_openapi.py --check` | `backend/openapi.yaml` khớp code, schema hợp lệ, không warning, mọi operation `/api/v1/` đủ chú thích (mục 5) |
| `pytest` | Toàn bộ test qua, kể cả `concurrency` và `flow`: `pytest -n auto --cov=modules --cov=shared --cov-report=` (`pytest-cov` gom coverage từ worker `pytest-xdist`) |
| Coverage | `python scripts/check_module_coverage.py` ≥ 80% **branch coverage riêng** (`[tool.coverage.run] branch = true`) cho từng nhóm, chi tiết bên dưới |
| `pip-audit` | Không có lỗ hổng |

Cổng coverage:

- Nhóm: `modules/<module>/services/**/*.py` + `modules/<module>/handlers.py` của **từng module**; hạ tầng `shared/events/**/*.py`, `shared/idempotency/**/*.py` (bỏ thư mục `tests`) và `shared/tasks.py` là một nhóm riêng.
- Thư mục Django app ở gốc `modules/` (`management`, `migrations`, `templates`, ADR 0006) không phải module.
- Không tính `shared/geo`, `shared/health` và phần định dạng của `shared/api` (ít nhánh nghiệp vụ). **Không** đặt ngưỡng toàn repo, để không ai viết test chỉ để lấp số.
- Script đọc dữ liệu và cấu hình coverage của project (`COVERAGE_FILE`, `[tool.coverage]` trong `pyproject.toml`, mặc định `.coverage`) qua API public `Coverage.branch_stats`, cộng nhánh đã chạy/tổng nhánh theo nhóm, so số nguyên với 80%; không dùng tỷ lệ gộp dòng + nhánh của `coverage report --fail-under`.
- Module chưa có target bị bỏ qua; target không có nhánh được báo rõ và qua; file chưa chạy vẫn được phân tích. Thiếu dữ liệu hoặc chỉ đo statement là lỗi.

Gate migration (mục 6) **chưa hoạt động** trong workflow hiện tại.

## 9. Chưa làm ở MVP

| Việc | Khi nào làm |
|---|---|
| Test tải theo [10-nfr.md](./10-nfr.md) mục 1 (p95 300/800 ms, 50 request/giây khi khuyến mãi), chạy bằng k6 trên staging | Trước đợt khuyến mãi lớn đầu tiên |
| `oasdiff` phát hiện breaking change của OpenAPI | Khi API có client ngoài frontend của team (ví dụ mobile app) |
| E2E qua trình duyệt | Thuộc repo frontend |

Ở MVP, hiệu năng chỉ được bảo vệ bằng `django-zeal` (N+1 query) và test concurrency (mục 2.2).
