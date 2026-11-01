# 04. API contract

> Trạng thái: **Đã chốt cho MVP** ([quy ước](../../README.md#trạng-thái-tài-liệu)). File này chốt hợp đồng dữ liệu và hành vi; khi có backend, OpenAPI được sinh bằng `drf-spectacular` tại `/api/schema/`, Swagger UI tại `/api/docs/` (chỉ local và staging nội bộ). Hiện chưa có backend hoặc `backend/openapi.yaml`; không coi bảng endpoint là bằng chứng API đã triển khai.
>
> Mọi request của storefront và back-office đi qua Next.js BFF ([ADR 0009](../adr/0009-nextjs-bff-django-private.md)). Từ internet chỉ có `/api/v1/webhooks/` gọi thẳng vào Django.

## 1. Quy ước chung

| Chủ đề | Quy ước |
|---|---|
| Gốc URL | `/api/v1/store/` (storefront), `/api/v1/backoffice/` (Staff/Admin), `/api/v1/webhooks/` (VNPay, MoMo, GHN) |
| Phiên bản | Ghi trên URL (`v1`). Thay đổi làm gãy client thì tạo `v2` chạy song song |
| Định dạng | JSON, field `snake_case` tiếng Anh |
| Tiền | `MoneyDTO = {"amount": 250000, "currency": "VND"}` ở cả body và response; `amount` là integer VND, không nhận float/string. Query `price_min`, `price_max` là integer VND vì query string không mang object |
| Thời gian | ISO 8601 có múi giờ, ví dụ `2026-10-25T10:15:00+07:00` |
| ID | UUID. Riêng Đơn hàng dùng `code` trên URL storefront |
| Ngôn ngữ | Header `Accept-Language: vi` (mặc định) hoặc `en`; chỉ ảnh hưởng `error.message` và nhãn hiển thị, không dịch nội dung Sản phẩm |
| Xác thực | `Authorization: Bearer <access_token>` ([05-auth-security.md](./05-auth-security.md)) |
| Giỏ của Khách vãng lai | Header `X-Cart-Token` (Frontend lưu trong cookie `cart_token`) |
| Đơn của Khách vãng lai | Header `X-Lookup-Token`: token 30 phút gắn với đúng một đơn, do `POST checkout` (với Khách vãng lai) hoặc `POST orders/lookup` cấp. Next.js cất token trong session |
| IP người dùng | Django đọc `X-Client-IP` do BFF gửi kèm `X-BFF-Secret` ([05-auth-security.md](./05-auth-security.md) mục 5) |
| Chống tạo trùng | Header `Idempotency-Key` UUID bắt buộc với checkout, bắt đầu Thanh toán và `stock/inbound`, `stock/adjust`, `stock/count`. Scope = method + endpoint chuẩn hoá (gồm ID tài nguyên) + danh tính Tài khoản hoặc guest cart token ổn định; thao tác kho dùng account_id Staff. Thiếu key hoặc key không phải UUID trả `400 VALIDATION_ERROR`; body phải là JSON, khác thì `415 UNSUPPORTED_MEDIA_TYPE`. Cùng key khác body chuẩn hoá trả `409 IDEMPOTENCY_CONFLICT`; còn xử lý trả `202 IdempotencyPendingDTO`, riêng tạo Payment trả `202 PaymentStartDTO`; kèm `Retry-After: 3`. Key completed trả nguyên status/body đã lưu. Giữ completed 24 giờ, không purge in_progress chưa rõ kết quả. Auth/quyền sở hữu vẫn kiểm tra trước khi replay; replay completed trước khi kiểm hạn quote mới, không chạy lại side effect. Body thay đổi, quote mới hoặc lần thử Payment mới dùng key mới |

Các transition không yêu cầu key trừ khi bảng endpoint ghi rõ. Transition lặp mặc định trả `409 INVALID_TRANSITION`; ngoại lệ được chỉ rõ: ghi nhận Hoàn tiền cùng dữ liệu, xác nhận nhập lại kho và bắt đầu/hoàn tất ẩn danh trả kết quả đã có. Không suy ra mọi POST đều idempotent. Mọi response lỗi thông thường theo `ErrorDTO` mục 3; webhook dùng ACK riêng tại mục 4.3 và 06.

## 2. Phân trang

```json
GET /api/v1/store/products?page=2&page_size=24
{
  "count": 135,
  "next": "…?page=3&page_size=24",
  "previous": "…?page=1&page_size=24",
  "results": [ … ]
}
```

`page_size` mặc định 24, tối đa 100: lớn hơn 100 thì giới hạn ở 100; nhỏ hơn 1 hoặc không phải số nguyên trả `400 VALIDATION_ERROR`. `page` nhỏ hơn 1 hoặc không phải số nguyên cũng trả `400 VALIDATION_ERROR` (kèm `details.fields.page`); trang vượt quá cuối trả `404 NOT_FOUND`.

## 3. Định dạng lỗi

Mọi lỗi trả cùng một định dạng (`shared/api/exception_handler.py`):

```json
HTTP 409
{
  "error": {
    "code": "OUT_OF_STOCK",
    "message": "Một số sản phẩm không đủ hàng.",
    "details": {
      "items": [{"sku": "TSHIRT-BASIC-WHT-M", "requested": 3, "available": 1}]
    },
    "request_id": "01JB…"
  }
}
```

| HTTP | Khi nào | Ví dụ `code` |
|---|---|---|
| 400 | Dữ liệu vào sai định dạng | `VALIDATION_ERROR` (kèm `details.fields`), `INVALID_QUOTE`, `INVALID_RETURN_URL`; `PARSE_ERROR` khi body không parse được (JSON hỏng); `BAD_REQUEST` khi request hỏng ngoài DRF, không gắn được field (ví dụ `SuspiciousOperation`, `handler400`) |
| 401 | Chưa đăng nhập, token hết hạn | `NOT_AUTHENTICATED`, `TOKEN_EXPIRED` |
| 403 | Không đủ quyền | `PERMISSION_DENIED` |
| 404 | Không tìm thấy | `NOT_FOUND`, `ORDER_NOT_FOUND` |
| 405 | Endpoint không nhận method này; header `Allow` liệt kê method được nhận | `METHOD_NOT_ALLOWED` |
| 415 | Body không phải JSON ở endpoint chỉ nhận JSON, ví dụ endpoint cần `Idempotency-Key` | `UNSUPPORTED_MEDIA_TYPE` |
| 409 | Xung đột với trạng thái hiện tại của hệ thống | `OUT_OF_STOCK`, `INVALID_TRANSITION`, `REFRESH_SUPERSEDED`, `IDEMPOTENCY_CONFLICT`, `PRICE_CHANGED`, `QUOTE_EXPIRED`, `SHIPMENT_IN_PROGRESS`, `PAYMENT_WINDOW_CLOSED`, `INSUFFICIENT_AVAILABLE` |
| 422 | Yêu cầu không thoả quy tắc nghiệp vụ | `VOUCHER_NOT_FOUND`, `VOUCHER_EXPIRED`, `VOUCHER_USAGE_LIMIT_REACHED`, `VOUCHER_BUYER_LIMIT_REACHED`, `VOUCHER_MIN_ORDER_NOT_MET`, `COD_LIMIT_EXCEEDED`, `LIST_PRICE_BELOW_SALE_PRICE`, `ORDER_TOTAL_NOT_POSITIVE`, `DATA_PROCESSING_CONSENT_REQUIRED`, `PAYMENT_CREATION_REJECTED` |
| 429 | Vượt giới hạn tần suất | `THROTTLED` |
| 500 | Lỗi hệ thống | `INTERNAL_ERROR` (không lộ chi tiết) |
| 503 | Không thể xác minh trạng thái auth bắt buộc từ DB | `AUTH_STATE_UNAVAILABLE`; không fallback chấp nhận token từ cache cho thao tác nhạy cảm (05 mục 2.2) |

Chọn 409 hay 422 cho mã mới:

- **409**: kết quả phụ thuộc trạng thái hệ thống, và trạng thái đó có thể đã đổi từ lúc client xem (Tồn kho, trạng thái đơn, giá, idempotency). Client nên tải lại dữ liệu rồi thử lại.
- **422**: chính yêu cầu không thoả quy tắc (Voucher không áp được cho đơn này, vượt Hạn mức COD, giá không hợp lệ). Gửi lại y nguyên vẫn lỗi.

Các mã Voucher là lớp con của `VoucherNotApplicable` trong `promotions`, mỗi lý do một mã để Frontend báo đúng lý do (US-304 AC2).

Frontend dịch theo `code`; `message` chỉ là bản dịch mặc định theo `Accept-Language`.

Các field số điện thoại được chuẩn hoá E.164 Việt Nam theo 03 mục 0.6 trước khi ghi hoặc tra cứu. Ví dụ `0901234567` và `+84 901 234 567` có cùng định danh; đầu vào không hợp lệ trả `400 VALIDATION_ERROR` kèm field tương ứng. Không dùng chuỗi gốc để kiểm giới hạn Voucher, lookup đơn hoặc xác định đối tượng yêu cầu xoá.

Các mã cần Frontend xử lý riêng:

- `PRICE_CHANGED`: tổng tiền khác expected_total hoặc snapshot/phiên bản trong quote_token không khớp dữ liệu xác thực trong transaction, kể cả tổng tiền không đổi (BR-ORD-07). Rollback trước khi dựng báo giá mới ngoài transaction; `details.quote` là `QuoteDTO` mục 5, dòng không bán được có `available = false`, giá NULL, `quote_token = null`, `checkout_allowed = false`. Client sửa giỏ hoặc xác nhận quote mới bằng key mới; không tạo đơn.
- `QUOTE_EXPIRED`: token đã hết hạn nhưng chữ ký hợp lệ; trả 409, lấy quote mới và dùng key mới. Chữ ký sai, khác danh tính hoặc body không khớp token trả 400 `INVALID_QUOTE` và không tiết lộ phần binding nào sai.
- `PAYMENT_INITIALIZING` (202): trả `PaymentStartDTO` có `state = initializing`, `redirect_url = null`, kèm Retry-After; thử lại cùng endpoint/body/key. Kết quả cuối không còn link trả `state = terminal` để client xem trạng thái đơn; không tạo/gia hạn link mới.
- `SHIPMENT_IN_PROGRESS`: Staff huỷ đơn khi Vận đơn đang được tạo ở GHN. Chờ kết quả tạo Vận đơn rồi xử lý tiếp.
- `PAYMENT_WINDOW_CLOSED`: Người mua bắt đầu Thanh toán online từ phút thứ 7 kể từ khi đặt đơn, khi link mới còn quá ít thời gian để trả tiền (BR-INV-05). Đơn sẽ bị huỷ khi Giữ hàng hết hạn; Người mua phải đặt đơn mới.

## 4. Danh sách endpoint

### 4.1. Storefront: `/api/v1/store/`

| Method | Path | Module | Quyền | Mô tả | User story |
|---|---|---|---|---|---|
| GET | `categories` | catalog | Công khai | Cây danh mục | US-101 |
| GET | `products` | catalog | Công khai | Danh sách có lọc `category`, `size`, `color` (theo mã trong danh sách size và bảng màu), `price_min`, `price_max`, `in_stock`, `q`, `ordering` (`newest`, `price`, `-price`, `best_selling`). `q` tìm chuỗi con trong tên, không dấu/không phân biệt hoa thường; trim đầu/cuối, rỗng thì bỏ lọc; không sửa lỗi gõ hay xếp hạng gần đúng (BR-CAT-13). `q` không thay cách sắp xếp đã chọn | US-101 → 103 |
| GET | `products/{slug}` | catalog | Công khai | Chi tiết, các màu, ảnh, Biến thể kèm giá và còn hàng | US-104 |
| GET | `geo/provinces` | shared | Công khai | Danh sách tỉnh/thành | US-301 |
| GET | `geo/provinces/{code}/wards` | shared | Công khai | Phường/xã của một tỉnh/thành | US-301 |
| GET | `cart` | ordering | Guest / Customer | Giỏ hàng kèm giá hiện tại và cảnh báo | US-202 |
| POST | `cart/items` | ordering | Guest / Customer | Thêm Biến thể. Khách vãng lai chưa có giỏ (không gửi `X-Cart-Token`) thì tạo giỏ mới và trả `cart_token` | US-201 |
| PATCH | `cart/items/{id}` | ordering | Guest / Customer | Đổi số lượng | US-202 |
| DELETE | `cart/items/{id}` | ordering | Guest / Customer | Xoá | US-202 |
| POST | `cart/merge` | ordering | Customer, kèm `X-Cart-Token` | Gộp giỏ vãng lai vào giỏ của Tài khoản (BR-CRT-03). Next.js gọi ngay sau khi đăng nhập thành công | US-204 |
| POST | `checkout/quote` | ordering | Guest / Customer | `QuoteInput` → `200 QuoteDTO` gồm tiền, dòng hàng và quote_token ký cho báo giá Người mua đã xem (mục 5). Làm tròn theo BR-VCH-10; tổng ≤ 0 trả `422 ORDER_TOTAL_NOT_POSITIVE` | US-303, 304 |
| POST | `checkout` | ordering | Guest / Customer | `CheckoutInput` gồm QuoteInput, quote_token và expected_total dạng MoneyDTO, cần Idempotency-Key. Xác minh token và kiểm tra lại dưới khoá; lệch trả `409 PRICE_CHANGED`, hết hạn trả `409 QUOTE_EXPIRED`; tổng ≤ 0 trả `422 ORDER_TOTAL_NOT_POSITIVE`. Thành công `201 CheckoutCreatedDTO`; lookup_token = null với Khách hàng, có JWT với Khách vãng lai | US-301 → 307 |
| POST | `orders/{code}/payments` | ordering | Customer chủ đơn, hoặc Guest có `X-Lookup-Token` | Bắt đầu một lần Thanh toán online (cần `Idempotency-Key`), gọi `payments.contracts.start_payment`. Body `{gateway: "vnpay" \| "momo"}`; backend tự dựng URL quay về, gửi `return_url` bị từ chối `400 INVALID_RETURN_URL`. Sẵn sàng thì trả `redirect_url`, chưa xong thì `202 PAYMENT_INITIALIZING`. Mọi link của đơn hết hạn ở phút thứ 10 kể từ khi đặt đơn (BR-INV-05); từ phút thứ 7 không tạo link mới mà trả `PAYMENT_WINDOW_CLOSED`. Gọi lại cùng key thì tiếp tục hoặc trả kết quả của Payment cũ ([06](./06-integrations.md) mục 3.1) | US-306 |
| POST | `orders/lookup` | ordering | Công khai (throttle chặt) | Khách vãng lai tra cứu bằng `code` + `phone`, nhận `lookup_token` | US-401 |
| GET | `orders` | ordering | Customer | Lịch sử đơn | US-402 |
| GET | `orders/{code}` | ordering | Customer chủ đơn, hoặc Guest có `X-Lookup-Token` | Chi tiết đơn | US-402 |
| POST | `orders/{code}/cancel` | ordering | Customer chủ đơn, hoặc Guest có `X-Lookup-Token` | Tự huỷ đơn | US-403 |
| POST | `auth/register` | identity | Công khai (throttle) | Đăng ký; luôn trả `202` như nhau dù email đã tồn tại hay chưa (US-501 AC2) | US-501 |
| POST | `auth/verify-email` | identity | Công khai | Xác thực email bằng token trong link | US-501 |
| POST | `auth/verify-email/resend` | identity | Công khai (throttle) | Gửi lại email xác thực; luôn trả `202` như nhau dù email có tồn tại hay không | US-501 |
| POST | `auth/login` | identity | Công khai | Đăng nhập email + mật khẩu | US-502 |
| POST | `auth/google` | identity | Công khai | Đổi `id_token` Google lấy JWT | US-502 |
| POST | `auth/refresh` | identity | Có refresh token | Xoay refresh token: request trùng trong 10 giây trả chính cặp đã cấp, không tạo nhánh; successor đã dùng thì `409 REFRESH_SUPERSEDED` ([05](./05-auth-security.md) mục 2.1) | — |
| POST | `auth/logout` | identity | Có refresh token đúng audience | Thu hồi family hiện tại; không yêu cầu access token còn hạn | — |
| POST | `auth/password/forgot` | identity | Công khai | Gửi link đặt lại mật khẩu; luôn trả `202` như nhau | US-503 |
| POST | `auth/password/reset` | identity | Công khai | Đặt lại mật khẩu bằng token trong link | US-503 |
| GET | `me` | identity | Customer | Hồ sơ | US-505, 506 |
| PATCH | `me` | identity | Customer | Sửa họ tên, số điện thoại, ngôn ngữ, và lựa chọn nhận email marketing (`marketing_opt_in`, mỗi lần đổi ghi một Consent mới, CMP-03). Không đổi được email ở MVP | US-505, 506 |
| GET | `me/addresses` | identity | Customer | Sổ địa chỉ | US-504 |
| POST | `me/addresses` | identity | Customer | Thêm địa chỉ | US-504 |
| PATCH | `me/addresses/{id}` | identity | Customer | Sửa địa chỉ, đặt làm mặc định | US-504 |
| DELETE | `me/addresses/{id}` | identity | Customer | Xoá địa chỉ | US-504 |
| POST | `me/erasure-request` | identity | Customer | Gửi Yêu cầu xoá dữ liệu | US-1101 |

`checkout` (với Khách vãng lai) và `orders/lookup` trả về một `lookup_token` JWT Ed25519 gắn với đúng một đơn, hết hạn sau 30 phút. Claims bắt buộc: `iss` theo cấu hình, `aud = order_lookup`, `token_use = lookup`, `sub = Mã đơn`, `iat`, `exp`; header có `kid`. Cấp và xác minh qua `identity.contracts` (02 mục 7.1), không lưu token vào DB. `IsOrderOwner` kiểm tra token hợp lệ và Mã đơn khớp URL; không chấp nhận access/refresh token thay thế. Lookup token cũng không được dùng như access token ở endpoint khác. Token không thu hồi sớm được; hạn 30 phút là đánh đổi đã chọn. Next.js cất token trong session và gửi qua header `X-Lookup-Token` (05 mục 2).

Gộp giỏ là endpoint riêng của `ordering` thay vì nằm trong `auth/login`, vì `identity` ở lớp dưới không được gọi `ordering` ([02-backend-structure.md](./02-backend-structure.md) mục 4).

### 4.2. Back-office: `/api/v1/backoffice/`

| Method | Path | Module | Quyền | Mô tả |
|---|---|---|---|---|
| POST | `auth/login` | identity | Công khai | Đăng nhập của Staff/Admin (tách khỏi storefront) |
| POST | `auth/refresh` | identity | Có refresh token | Lấy access token mới, xoay vòng refresh token |
| POST | `auth/logout` | identity | Có refresh token đúng audience | Thu hồi family hiện tại; không yêu cầu access token còn hạn |
| POST | `auth/password/forgot` | identity | Công khai | Staff/Admin quên mật khẩu, cùng cơ chế với storefront (05 mục 3) |
| POST | `auth/password/reset` | identity | Công khai | Đặt lại mật khẩu bằng token trong link |
| GET | `orders` | ordering | Staff | Lọc theo trạng thái, Phương thức thanh toán, ngày, Cờ cần xử lý (`flag=<kind>`), Khách hàng (`customer_id`); tìm theo Mã đơn, số điện thoại (tìm theo số điện thoại thì ghi log truy cập, CMP-07) |
| GET | `orders/{id}` | ordering | Staff | Chi tiết đơn, lịch sử trạng thái, Cờ cần xử lý (ghi log truy cập, CMP-07) |
| POST | `orders/{id}/flags/{flag_id}/resolve` | ordering | Staff | Gỡ Cờ cần xử lý sau khi xử lý xong (ghi lịch sử) |
| POST | `orders/{id}/confirm` | ordering | Staff | Xác nhận đơn (T6) |
| POST | `orders/{id}/start-packing` | ordering | Staff | Bắt đầu đóng gói (T8) |
| POST | `orders/{id}/cancel` | ordering | Staff | Huỷ đơn (T7, T9, T14), bắt buộc lý do. Trả `409 SHIPMENT_IN_PROGRESS` khi Vận đơn `requested` hoặc `creation_unknown`; đơn `SHIPPING` chỉ huỷ được khi Vận đơn gặp sự cố (T14). Riêng T14 bắt buộc boolean `warehouse_return_required`: true chỉ khi Staff xác nhận hàng chưa rời Kho, false khi mất/hư; các nhánh huỷ khác không cho đặt true |
| POST | `orders/{id}/hand-over` | ordering | Staff | Bàn giao GHN (T10), chạy nền: trả `202`, đơn sang `SHIPPING` khi GHN tạo Vận đơn xong; lỗi thì gắn cờ `shipment_failed`. Chỉ dùng lại Vận đơn cũ sau `shipment_failed` đã xác nhận chưa tạo bên GHN; `creation_unknown` phải đối soát trước |
| POST | `orders/bulk/confirm` | ordering | Staff | Xác nhận hàng loạt (US-602) |
| POST | `orders/bulk/hand-over` | ordering | Staff | Bàn giao hàng loạt (US-603) |
| POST | `orders/{id}/returned-to-warehouse` | ordering | Staff | Xác nhận nhập lại cho đơn `RETURNED_TO_SENDER` hoặc `CANCELLED` có `warehouse_return_required = true`; khoá Order, nhập kho và ghi `returned_to_warehouse_at` cùng transaction. Gọi lại trả kết quả đã ghi, không cộng tồn lần nữa; đơn không thuộc diện này trả `409 INVALID_TRANSITION` |
| GET | `returns` | ordering | Staff | Danh sách Đổi trả |
| POST | `returns` | ordering | Staff | Ghi nhận yêu cầu Đổi trả cho một đơn Đã giao (US-606) |
| POST | `returns/{id}/receive` | ordering | Staff | Xác nhận đã nhận hàng gửi trả; Tồn kho chưa được cộng lại |
| POST | `returns/{id}/accept` | ordering | Staff | Chấp nhận theo từng dòng, body `{lines: [{return_line_id, accepted_quantity, restock}]}` (BR-RET-08); tính số hoàn lũy kế theo BR-RET-07. Tổng > 0 tạo yêu cầu Hoàn tiền; có hàng được chấp nhận nhưng tổng = 0 thì khép lại `refunded`, `refund_id = null`, không tạo Hoàn tiền |
| POST | `returns/{id}/reject` | ordering | Staff | Từ chối, kèm ghi chú việc gửi lại hàng (BR-RET-09) |
| GET | `refunds` | payments | Staff | Danh sách Hoàn tiền kèm `payment_id`, gateway và số tiền, lọc theo trạng thái |
| POST | `refunds/{id}/complete` | payments | Staff | Ghi nhận đã hoàn: mã giao dịch hoàn, ngày hoàn (BR-REF-03). Gọi lại cùng dữ liệu trả kết quả cũ, không phát thêm sự kiện; khác dữ liệu đã ghi thì từ chối |
| GET | `stock` | inventory | Staff | Tồn kho, Giữ hàng, Hàng chờ xuất và Số lượng bán được theo Biến thể; SKU và tên lấy qua `catalog.contracts`. Lọc tồn thấp bằng `available_lt=<n>` (mặc định 5, US-702) |
| POST | `stock/inbound` | inventory | Staff | Nhập kho, bắt buộc số phiếu nhập (cần `Idempotency-Key`) |
| POST | `stock/adjust` | inventory | Staff | Điều chỉnh, bắt buộc lý do, cần `Idempotency-Key`. Giảm quá Số lượng bán được thì `409 INSUFFICIENT_AVAILABLE` (BR-INV-11) |
| POST | `stock/count` | inventory | Staff | Kiểm kê (cần `Idempotency-Key`): gửi số đếm theo Biến thể, hệ thống điều chỉnh theo chênh lệch với Tồn kho + Hàng chờ xuất (US-703) |
| GET | `customers` | identity | Staff | Danh sách Khách hàng |
| GET | `customers/{id}` | identity | Staff | Chi tiết Khách hàng (ghi log truy cập, CMP-07). Lịch sử đơn lấy bằng `GET orders?customer_id=` |
| GET | `erasure-requests` | ordering | Staff | Danh sách Yêu cầu xoá dữ liệu (đọc qua `identity.contracts`) |
| POST | `erasure-requests` | ordering | Staff | Tạo yêu cầu cho Khách vãng lai sau khi xác minh qua kênh hỗ trợ |
| POST | `erasure-requests/{id}/complete` | ordering | Staff | Kiểm tra mọi đơn liên quan ở trạng thái cuối và không còn Hoàn tiền chờ xử lý (CMP-05), chuyển yêu cầu sang `processing` rồi trả `202` kèm `request_id` và `status`. Gọi lại không phát thêm sự kiện; đã `completed` thì trả kết quả hiện tại. `completed_at` chỉ có khi mọi bước ẩn danh bắt buộc thành công |
| GET | `categories` | catalog | Admin | Cây danh mục |
| POST | `categories` | catalog | Admin | Tạo Danh mục |
| PATCH | `categories/{id}` | catalog | Admin | Sửa, đổi Danh mục cha, đổi thứ tự |
| DELETE | `categories/{id}` | catalog | Admin | Chỉ khi không còn Sản phẩm hay Danh mục con |
| GET | `products` | catalog | Admin | Danh sách, mọi trạng thái |
| POST | `products` | catalog | Admin | Tạo Sản phẩm ở trạng thái `draft` |
| GET | `products/{id}` | catalog | Admin | Chi tiết |
| PATCH | `products/{id}` | catalog | Admin | Sửa thông tin |
| DELETE | `products/{id}` | catalog | Admin | Chỉ Sản phẩm `draft`: chưa từng bán nên chưa có trong đơn (BR-CAT-09) |
| POST | `products/{id}/publish` | catalog | Admin | `draft` → `active` |
| POST | `products/{id}/archive` | catalog | Admin | Ngừng bán (`archived`) |
| POST | `products/{id}/variants` | catalog | Admin | Tạo Biến thể, hoặc sinh ma trận size × màu (US-802) |
| PATCH | `products/{id}/variants/{variant_id}` | catalog | Admin | Sửa Giá bán, trạng thái. Hạ Giá bán xuống ≤ Giá khuyến mãi đang hoặc sắp hiệu lực thì `422 LIST_PRICE_BELOW_SALE_PRICE` (BR-PRC-05) |
| POST | `products/{id}/images` | catalog | Admin | Upload ảnh theo màu |
| PATCH | `products/{id}/images/{image_id}` | catalog | Admin | Đổi thứ tự ảnh |
| DELETE | `products/{id}/images/{image_id}` | catalog | Admin | Xoá ảnh |
| GET | `sizes` | catalog | Admin | Danh sách size |
| POST | `sizes` | catalog | Admin | Thêm size (US-805) |
| PATCH | `sizes/{id}` | catalog | Admin | Sửa, ẩn bằng `is_active = false`; không có DELETE |
| GET | `colors` | catalog | Admin | Bảng màu |
| POST | `colors` | catalog | Admin | Thêm màu (US-805) |
| PATCH | `colors/{id}` | catalog | Admin | Sửa, ẩn bằng `is_active = false`; không có DELETE |
| GET | `sale-prices` | catalog | Admin | Danh sách Giá khuyến mãi |
| POST | `sale-prices` | catalog | Admin | Tạo cho một Biến thể hoặc mọi Biến thể của một Sản phẩm (US-804) |
| PATCH | `sale-prices/{id}` | catalog | Admin | Sửa giá, thời gian; kết thúc sớm bằng cách sửa `ends_at` |
| DELETE | `sale-prices/{id}` | catalog | Admin | Chỉ khi chưa bắt đầu |
| GET | `vouchers` | promotions | Admin | Danh sách kèm số lượt đã dùng |
| POST | `vouchers` | promotions | Admin | Tạo Voucher |
| PATCH | `vouchers/{id}` | promotions | Admin | Sửa, vô hiệu (`is_active = false`). Không có DELETE vì Voucher có Lượt dùng |
| GET | `staff` | identity | Admin | Danh sách Tài khoản Staff |
| POST | `staff` | identity | Admin | Tạo Tài khoản Staff (Tài khoản Admin chỉ tạo bằng lệnh) |
| PATCH | `staff/{id}` | identity | Admin | Sửa, vô hiệu (`is_active = false`, mọi phiên mất hiệu lực ngay) |
| GET | `settings/ordering` | ordering | Admin | Ngưỡng miễn phí ship, Hạn mức COD |
| PATCH | `settings/ordering` | ordering | Admin | Sửa hai giá trị trên |
| GET | `settings/shipping` | shipping | Admin | Phí ship dự phòng |
| PATCH | `settings/shipping` | shipping | Admin | Sửa Phí ship dự phòng |
| GET | `settings/ghn-locations` | shipping | Admin | Phường/xã chưa có ánh xạ sang GHN (US-1004) |
| PATCH | `settings/ghn-locations/{ward_code}` | shipping | Admin | Gán ID tỉnh, quận, phường của GHN cho một phường/xã |
| GET | `reports/revenue` | ordering | Admin | Báo cáo Doanh thu (BR-REV-01, BR-REV-02) |
| GET | `reports/paid-orders.csv` | ordering | Admin | Danh sách đơn đã thu tiền theo ngày, để gửi cho kế toán |

**Module sở hữu endpoint.** Mỗi endpoint nằm trong `api/` của đúng một module (cột Module). Màn cần dữ liệu của nhiều module thì Frontend gọi nhiều endpoint, hoặc endpoint đặt ở module cao nhất trong số đó và lấy phần còn lại qua `contracts` của module lớp dưới. Ví dụ `stock` (`inventory`) lấy SKU và tên qua `catalog.contracts`; còn chi tiết Khách hàng (`identity`) không đọc được Đơn hàng, nên Frontend lấy lịch sử đơn bằng `GET orders?customer_id=`.

### 4.3. Webhook: `/api/v1/webhooks/`

| Method | Path | Module | Xác thực | Phản hồi |
|---|---|---|---|---|
| GET | `vnpay/ipn` | payments | Chữ ký HMAC-SHA512 | JSON `{"RspCode": "00", "Message": "Confirm Success"}` theo đặc tả VNPay |
| POST | `momo/ipn` | payments | Chữ ký HMAC-SHA256 | HTTP 204 |
| POST | `ghn` | shipping | Token bí mật trong header + IP allow-list **[Cần xác minh cơ chế GHN hỗ trợ]** | HTTP 200 |

Webhook không dùng ErrorDTO/envelope chung khi provider có ACK riêng. Chỉ ACK đã xử lý sau khi xác minh, lưu observation/cập nhật Payment hoặc Shipment và outbox cần thiết đã commit; thông báo trùng đã commit có thể ACK ngay. Sai chữ ký, không khớp giao dịch hoặc DB rollback dùng bảng phản hồi riêng ở 06 mục 1.3; không trả thành công để che lỗi lưu. ACK xác nhận tiếp nhận/xử lý, không tự có nghĩa giao dịch thanh toán thành công. Nghiệp vụ Order tiếp tục qua sự kiện. Đây là phần duy nhất của Django mở ra internet (ngoại lệ Fake Gateway local tại 06).

### 4.4. Vận hành

| Path | Mô tả |
|---|---|
| `/healthz` | Tiến trình còn sống |
| `/readyz` | Kết nối được PostgreSQL. Không kiểm tra Redis, để API vẫn phục vụ khi Redis lỗi ([10-nfr.md](./10-nfr.md) mục 2) |
| `/api/schema/`, `/api/docs/` | OpenAPI và Swagger UI (chỉ local và staging nội bộ, tắt trên production) |
| `/dev/fake-gateway/…` | Trang Fake Gateway (chỉ có khi `FAKE_PROVIDERS_ENABLED = true`, tức local và test) |

## 5. Schema dữ liệu và báo giá đã ký

### 5.1. Quy ước schema

- Các tên schema ở mục này là hợp đồng để viết serializer và OpenAPI, không phải các class đã tồn tại. Mọi object từ chối key lạ; serializer chỉ liệt kê field tường minh, không dùng `fields = "__all__"`. Không tự expose field DB khi model được thêm cột.
- Ký hiệu `x?` là key có thể bỏ qua, `T hoặc null` là key có thể mang NULL. Key không có `?` bắt buộc có mặt trong response; field chỉ có default ở request thì có thể bỏ qua để dùng default đó. UUID/timestamp biểu diễn bằng string chuẩn; enum, max_length và ràng buộc nghiệp vụ theo [03](./03-data-model.md). Mọi số tiền dùng MoneyDTO trừ phần trăm Voucher và query số; các count/quantity là integer.
- PATCH chỉ thay field được gửi; bỏ qua là giữ nguyên, `null` chỉ hợp lệ với field được ghi nullable. Object lồng được thay toàn bộ nếu được gửi, không deep-merge ngầm. PATCH rỗng hoặc field read-only/key lạ trả `400 VALIDATION_ERROR`; không mặc định bỏ qua field lạ.
- GET không nhận body. Lệnh không có dữ liệu đầu vào chấp nhận body vắng mặt hoặc `{}`. DELETE thành công trả 204 không body. Object trả trực tiếp, danh sách phân trang dùng `Page<T> = {count: integer >= 0, next: URL hoặc null, previous: URL hoặc null, results: T[]}`; cây địa giới/Danh mục dùng array không phân trang như registry. Không bọc thêm `data`.
- `ErrorDTO = {error: {code: string, message: string, details: object, request_id: string}}`; `details` chỉ dùng schema theo code: validation có `fields: {field_path: string[]}`, PRICE_CHANGED có `quote: QuoteDTO`, thiếu hàng có `items: [{variant_id: UUID, requested: integer, available: integer}]`; code không có chi tiết dùng `{}`. Lỗi object không thuộc chủ sở hữu trả 404, không tiết lộ đối tượng tồn tại.
- Danh sách phân trang luôn có thứ tự ổn định: ordering đã chọn rồi thêm `id` làm tie-break; mặc định mới nhất (`created_at` giảm dần, `id` giảm dần). Query page sai kiểu/ngoài miền và `page_size` sai kiểu/nhỏ hơn 1 trả 400 (`page_size` lớn hơn 100 bị giới hạn ở 100), trang vượt phạm vi trả 404. Query thời gian dùng ISO 8601 có múi giờ, khoảng báo cáo `[from, to)`, ngày hiển thị/báo cáo theo Asia/Ho_Chi_Minh.

### 5.2. Schema dùng chung và checkout

| Schema | Field và ràng buộc |
|---|---|
| `MoneyDTO` | `{amount: integer >= 0, currency: "VND"}`; field giá/tiền cần thu > 0 theo 03, không float |
| `BaseReadDTO` | `{id: UUID, created_at: timestamp, updated_at: timestamp}`; chỉ dùng khi schema ghi kế thừa, không áp cho địa giới |
| `ConsentInput` | `{purpose: data_processing hoặc marketing, policy_version: string <= 32, granted: boolean}`; mỗi purpose tối đa một lần trong mảng |
| `ContactInput` | `{name: string 1..255, phone: string 1..20, email?: string <= 254 = ""}`; trim tên, phone là số di động Việt Nam hợp lệ theo US-301 rồi chuẩn E.164, email chữ thường |
| `ShippingInput` | `{ward_code: string 1..10, street: string 1..255}`; ward phải tồn tại, không nhận province do suy ra từ ward |
| `InvoiceInput` | `{company_name, company_address: string 1..255, tax_code: string 1..14, invoice_email: email <= 254}` |
| `QuoteInput` | `{contact: ContactInput, shipping: ShippingInput, payment_method: cod hoặc online, voucher_code?: string <= 32 = "", language?: vi hoặc en = vi, invoice_requested?: boolean = false, invoice_info?: InvoiceInput hoặc null = null}`; invoice_info phải có iff invoice_requested; giỏ lấy từ account hoặc X-Cart-Token, không nhận giá/dòng hàng do client tự cung cấp |
| `CheckoutInput` | Các field QuoteInput cộng `{quote_token: string, expected_total: MoneyDTO, consents: ConsentInput[]}`; bắt buộc data_processing granted=true với policy_version hiện hành đã hiển thị; marketing tuỳ chọn. Consent không tham gia hash giá. Chọn địa chỉ có sẵn bằng GET me/addresses rồi gửi bản chụp Contact/Shipping tương ứng (US-302). Tuỳ chọn lưu địa chỉ của Customer dùng POST me/addresses riêng, không sửa snapshot Đơn hàng nếu việc lưu địa chỉ thất bại; không cho client ghi Address của người khác |
| `QuoteLineDTO` | `{variant_id: UUID, quantity: integer > 0, product_name: string hoặc null, sku: string hoặc null, size: string hoặc null, color_name: string hoặc null, unit_price: MoneyDTO hoặc null, list_price: MoneyDTO hoặc null, voucher_discount: MoneyDTO hoặc null, available: boolean}`; dòng không bán được dùng null cho dữ liệu không còn cung cấp, không bịa giá |
| `QuoteDTO` | `{lines: QuoteLineDTO[], subtotal: MoneyDTO hoặc null, discount: MoneyDTO hoặc null, shipping_fee: MoneyDTO hoặc null, total: MoneyDTO hoặc null, shipping_source: ghn hoặc fallback hoặc free hoặc null, checkout_allowed: boolean, quote_token: string hoặc null, expires_at: timestamp hoặc null}`; quote hợp lệ có toàn bộ tiền, token/hạn và checkout_allowed=true. Quote lỗi do dòng không bán được có token/hạn null, checkout_allowed=false; các tổng phụ thuộc dòng lỗi là null |
| `CheckoutCreatedDTO` | `{order_code: string <= 16, lookup_token: string hoặc null}`; khách đã đăng nhập nhận null, Guest nhận JWT 30 phút |
| `PaymentStartInput` | `{gateway: vnpay hoặc momo}`; return_url bị từ chối với INVALID_RETURN_URL |
| `PaymentStartDTO` | `{payment_id: UUID, state: ready hoặc initializing hoặc terminal, payment_status: enum Payment.status, code: string hoặc null, redirect_url: URL hoặc null}`; ready có URL và code=null; initializing có code=PAYMENT_INITIALIZING, URL=null, HTTP202; terminal có URL=null, HTTP200. Kết quả từ chối tạo chắc chắn trả422 ErrorDTO code PAYMENT_CREATION_REJECTED và lưu kết quả idempotency, không giả terminal thành công |
| `IdempotencyPendingDTO` | `{code: "IDEMPOTENCY_IN_PROGRESS", retry_after: integer > 0}`; HTTP202, header Retry-After cùng số giây; không phải lỗi 500 hoặc lời hứa đã tạo tài nguyên |
| `OrderLookupInput` / `OrderLookupDTO` | Input `{code: string <= 16, phone: string <= 20}`; output `{order_code: string <= 16, lookup_token: string}`. Không khớp trả chung 404 ORDER_NOT_FOUND |

### 5.3. Vòng đời quote_token

1. `ordering` validate QuoteInput, đọc các dòng giỏ và catalog, đánh giá Voucher/ship ngoài transaction khóa dài, trả QuoteDTO. Quote không Giữ hàng hoặc bảo đảm giá tương lai. `QUOTE_TTL = 5 phút` **[Giả định · kiểm chứng: tỉ lệ `QUOTE_EXPIRED` trên staging]**, cấu hình được, ngắn hạn độc lập TTL Giữ hàng/Payment; chỉ cấp token cho quote có thể checkout và tổng > 0.
2. Token dùng Django signing HMAC-SHA256, salt `ordering.checkout-quote.v1`, keyring `QUOTE_SIGNING_KEYS` có `kid` và active key riêng, không dùng khoá JWT hoặc secret provider. Đây là token ký, không mã hoá, không phải JWT xác thực. Payload có `schema_version = 1`, `kid`, `issued_at`, `expires_at`, `subject_hash`, `input_hash`, `cart_hash`, `lines: [{variant_id, quantity, checkout_version, snapshot_hash}]`, các số tiền VND dạng integer và `shipping_fingerprint`. Không chứa contact/email/phone/street/invoice hoặc secret.
3. Binding hash là HMAC-SHA256 với key của token và domain riêng cho subject/input/cart/snapshot/shipping, không phải hash PII không có khoá. Subject = account_id của Customer, hoặc hash cart token ổn định của Guest; đổi từ Guest sang Customer phải lấy quote mới. Input canonical là QuoteInput đã validate, áp defaults, phone/email/voucher chuẩn hoá, JSON UTF-8 sort key và separator cố định, không whitespace tuỳ ý; invoice_info absent được chuẩn về null. Cart canonical là cặp variant_id/quantity sắp theo UUID. Snapshot hash gồm các field snapshot, giá/điều kiện bán/cân nặng dùng khi báo giá; shipping_fingerprint gồm phí, source/reason, dữ liệu request đã chuẩn hoá và revision config/mapping tác động phí. Không đưa consents, expected_total, Idempotency-Key hoặc quote_token vào input hash.
4. Checkout kiểm tra quyền và Idempotency-Key. Key completed cùng request trả nguyên kết quả đã lưu **trước khi kiểm hạn quote**; cùng key khác request trả409, in_progress trả202. Với thao tác mới, xác minh chữ ký/salt/kid/schema/hạn, binding danh tính/body và so expected_total với số đã ký. Sai chữ ký/binding/body trả400 INVALID_QUOTE; hết hạn trả409 QUOTE_EXPIRED; không lấy payload ký làm quyền truy cập tài nguyên hoặc giá được bảo đảm.
5. Trong transaction, khóa Cart trước StockItem; mọi mutation cart cũng khóa Cart (merge khóa hai Cart theo id tăng dần). Đọc lại cart_hash, sau đó khóa StockItem → Variant → Voucher theo 02. Tính lại giá tại một now chung, kiểm phiên bản/snapshot/điều kiện bán, Voucher, cấu hình và tổng. Cart thay đổi hoặc snapshot/tổng khác báo giá → rollback và PRICE_CHANGED; ngoài transaction dựng lại QuoteDTO. Không gọi GHN dưới khóa; nếu shipping config/mapping/request fingerprint đổi, rollback rồi báo giá mới, không dùng phí cũ như phí được bảo đảm.
6. Thành công tạo Order/OrderLine, side effect tồn kho/Voucher/Consent, kết quả idempotency và xóa các dòng đã mua khỏi Cart cùng transaction. Cùng token với key mới vẫn phải khớp giỏ hiện tại; token không phải khóa chống tạo đơn duy nhất và không được dùng để mua lại giỏ đã checkout. Thao tác giỏ chen sau khóa được tuần tự hoá, không xóa hàng mới của request khác ngoài snapshot đã kiểm tra. Rollback không làm mất giỏ hoặc tiêu hao lượt Voucher.
7. Keyring giữ key xác minh cũ ít nhất bằng QUOTE_TTL cộng clock skew cấu hình; token hợp lệ phải thoả `expires_at - issued_at <= QUOTE_TTL` và kiểm hạn bằng thời gian server. Không log token, input canonical có PII hoặc keyring. Scope/key idempotency lưu response theo quy tắc 24 giờ, không giữ riêng bảng Quote.

### 5.4. Schema tài nguyên đọc và ghi

Các DTO đọc chỉ có field trong bảng này. Ký hiệu `Base + ...` kế thừa BaseReadDTO; field có cùng tên với 03 giữ type/enum/NULL/max_length tại đó, nhưng tiền chuyển MoneyDTO và FK chỉ trả ID, không tự nhúng model. Mọi field thêm/đổi phải sửa hợp đồng và OpenAPI cùng PR.

| Schema | Field được phép |
|---|---|
| `AccountDTO` | Base + email, kind, full_name, phone, language, is_active, email_verified; không password/token_version/token/hash |
| `ProfileDTO` | AccountDTO + `marketing_opt_in: boolean` từ Consent marketing mới nhất, mặc định false |
| `AddressDTO` / `AddressInput` | Read Base + recipient_name, phone, ward_code, street, is_default; input chỉ các field này, is_default mặc định false; không nhận account_id |
| `CategoryDTO` / `CategoryInput` | Read Base + parent_id, name, slug, position; input name, slug, parent_id?=null, position?=0. `CategoryTreeDTO` thêm `children: CategoryTreeDTO[]` |
| `GeoDTO` | `{code: string <= 10, name: string <= 255}`; array province/ward, province đã có trên route |
| `SizeDTO` / `SizeInput` | Read Base + code, name, position, is_active; input code, name, position?=0, is_active?=true |
| `ColorDTO` / `ColorInput` | Read Base + code, name, hex, is_active; input code, name, hex, is_active?=true |
| `ImageDTO` / `ImageInput` | Read Base + product_color_id, `url: URL`, position; input multipart `{product_color_id: UUID, file: binary, position?: integer = 0}`; JPEG/PNG/WebP ≤5MB, giới hạn ảnh theo05. Không trả storage credential hoặc đường dẫn ổ đĩa |
| `VariantDTO` | Base + product_color_id, size_id, sku, price, status, checkout_version, is_available; thêm `effective_price: MoneyDTO`, `size: SizeDTO`, `color: ColorDTO` |
| `VariantCreateInput` | `{variants: [{size_id: UUID, color_id: UUID, sku: string <= 64, price: MoneyDTO}]}` mảng không rỗng, không trùng tổ hợp/SKU. Frontend dựng ma trận size×màu và Admin nhập SKU/giá từng dòng; backend validate toàn bộ rồi tạo atomically, tạo ProductColor còn thiếu |
| `VariantPatchInput` | sku?, price?, status?; không đổi SKU đã có đơn; không nhận product_id/size_id/color_id để đổi danh tính tổ hợp đã bán |
| `ProductInput` | category_id, name, slug, weight_grams, description?=""; không nhận status/sold_30d; tạo draft, đổi trạng thái qua action riêng |
| `ProductDTO` | Base + category_id, name, slug, description, status, weight_grams, sold_30d; `colors: [{id: UUID, color: ColorDTO, images: ImageDTO[]}]`, `variants: VariantDTO[]`, `min_effective_price: MoneyDTO hoặc null`, `is_available: boolean` |
| `ProductSummaryDTO` | `{id, name, slug, status, category_id, created_at, min_effective_price: MoneyDTO hoặc null, list_price: MoneyDTO hoặc null, image_url: URL hoặc null, is_available: boolean}`; giá/ảnh cho Biến thể đại diện rẻ nhất, tie-break variant_id |
| `CartDTO` | `{id: UUID hoặc null, cart_token: string hoặc null, items: CartLineDTO[], total: MoneyDTO, warnings: CartWarningDTO[]}`; cart_token chỉ trả khi cấp giỏ Guest mới, không trả token của người khác; giỏ chưa tồn tại trả id=null, items=[], total={amount:0,currency:VND}, warnings=[] |
| `CartLineDTO` | `{id: UUID, variant_id: UUID, quantity: integer > 0, product_name: string hoặc null, sku: string hoặc null, unit_price: MoneyDTO hoặc null, available: boolean, price_changed: boolean}`; dòng archived không bịa giá. Cart.total cộng các dòng còn giá, không phải quote checkout |
| `CartWarningDTO` | `{variant_id: UUID, requested: integer > 0, kept: integer >= 0, code: quantity_capped_stock hoặc quantity_capped_limit}`; mô tả số lượng đích yêu cầu và số thực giữ, không phải số tăng thêm |
| `CartAddInput` / `CartQuantityInput` | Add `{variant_id: UUID, quantity: integer > 0}` là cộng thêm; patch `{quantity: integer > 0}` là số lượng đích. Số giữ không vượt min(Số lượng bán được,10). Nếu còn mua được nhưng số đích vượt tồn/giới hạn, cập nhật tới mức tối đa và trả200 CartDTO kèm warning, không âm thầm cắt số lượng; ví dụ đang2, thêm2, tồn3 → giữ3, requested=4, kept=3 (US-201). Không còn mua được/archived thì trả409 OUT_OF_STOCK và không tạo dòng quantity=0 hoặc thay đổi giỏ; dòng hết hàng cũ vẫn được đánh dấu theo US-202 |
| `CartMergeDTO` | `{cart: CartDTO, warnings: CartWarningDTO[]}`; warnings ở cấp ngoài liệt kê việc cắt số lượng khi gộp theo BR-CRT-03; cart.warnings=[] để không lặp cảnh báo |
| `OrderLineDTO` | Base + variant_id, product_name, sku, size, color_name, unit_price, list_price, quantity, voucher_discount |
| `OrderSummaryDTO` | `{code: string, status: enum Order.status, payment_method: cod hoặc online, total: MoneyDTO, created_at: timestamp, placed_at: timestamp hoặc null}` |
| `OrderDTO` | OrderSummaryDTO + contact_name, contact_phone, contact_email, ship_ward_code, ship_street, subtotal, discount, shipping_fee, shipping_fee_fallback, voucher_code, language, invoice_requested, invoice_info, expires_at, cancelled_at, delivered_at, completed_at, `lines: OrderLineDTO[]`, `shipment: ShipmentSummaryDTO hoặc null` |
| `ShipmentSummaryDTO` | `{provider_order_code: string hoặc null, status: enum Shipment.status}`; không raw_payload, creation_input, lease hoặc secret |
| `BackofficeOrderDTO` | OrderDTO + id, customer_id, payment_id, warehouse_return_required, returned_to_warehouse_at, cancel_reason, updated_at, `flags: OrderFlagDTO[]`, `history: AuditEntryDTO[]`; chỉ response back-office được có thông tin audit |
| `OrderFlagDTO` | Base + kind, note, resolved_at, resolved_by |
| `AuditEntryDTO` | `{occurred_at: timestamp, actor_id: UUID hoặc null, fields: {field_name: {before: JSON scalar hoặc null, after: JSON scalar hoặc null}}}`; field_name chỉ allowlist audit03 mục10.1, không chứa PII hoặc raw payload |
| `ReturnDTO` / `ReturnLineDTO` | Return: Base + order_id, status, channel, reason, note, refund_id, recorded_by, `lines: ReturnLineDTO[]`; Line: Base + order_line_id, quantity, accepted_quantity, restock |
| `ReturnInput` | `{order_id: UUID, channel: hotline hoặc zalo, reason: string 1..500, lines: [{order_line_id: UUID, quantity: integer > 0}]}`; không trùng dòng, phải cùng Order |
| `ReturnAcceptInput` | `{lines: [{return_line_id: UUID, accepted_quantity: integer >= 0, restock: boolean}]}`; phải đủ đúng các dòng yêu cầu, không trùng/thiếu; không nhận refund amount do client tính |
| `RefundDTO` | Base + payment_id, amount, reason, channel, status, provider_refund_ref, recorded_by, completed_at; thêm `gateway: vnpay hoặc momo hoặc null`; không thông tin tài khoản ngân hàng |
| `RefundCompleteInput` | `{provider_refund_ref: string 1..64, completed_at: timestamp}`; recorded_by lấy từ phiên, không nhận của client |
| `StockDTO` | Base + warehouse_id, variant_id, on_hand, reserved, awaiting_dispatch; thêm sku, product_name và `available: integer >= 0` |
| `StockWriteInput` | `{variant_id: UUID, warehouse_id: UUID, quantity: integer > 0, reference: string 1..64}` cho inbound; adjust dùng `{variant_id, warehouse_id, delta: integer khác0, reason: string 1..500}`; count dùng `{variant_id, warehouse_id, counted_quantity: integer >= 0}`; mỗi request một Biến thể, không có amount do client tự tính |
| `ErasureDTO` | Base + account_id, status, received_at, started_at, completed_at, handled_by; không subject_phone/required_handlers/event payload ở response thường |
| `GuestErasureInput` | `{subject_phone: string <= 20, received_at: timestamp}`; Staff đã xác minh ngoài hệ thống trước khi ghi, không tự suy từ thông tin tra cứu |
| `SalePriceDTO` / `SalePriceInput` | Read Base + variant_id, price, starts_at, ends_at; input `{variant_id?: UUID, product_id?: UUID, price: MoneyDTO, starts_at, ends_at}` đúng một target; product target áp cùng giá cho mọi Variant và transaction toàn bộ, không tạo một phần |
| `VoucherDTO` / `VoucherInput` | Read Base + code, kind, value, max_discount, min_order_value, usage_limit, per_customer_limit, starts_at, ends_at, is_active; thêm `used_count: integer >= 0`. Input bỏ Base/used_count; cả input/read dùng value integer phần trăm khi percent, MoneyDTO khi fixed, trường tiền khác là MoneyDTO hoặc null; các giới hạn nullable, is_active mặc định true |
| `OrderingSettingsDTO` | `{free_shipping_threshold: MoneyDTO, cod_limit: MoneyDTO}` |
| `ShippingSettingsDTO` | `{fallback_fee: MoneyDTO}` |
| `GhnLocationDTO` / `GhnLocationInput` | Read `{ward_code, ghn_province_id: integer hoặc null, ghn_district_id: integer hoặc null, ghn_ward_code: string hoặc null}`; chưa map dùng null. Input bắt buộc đủ ba ID/mã phù hợp mode đã nghiệm thu, không ID giả |
| `RevenueDTO` | `{from: timestamp, to: timestamp, granularity: day hoặc month, rows: [{period: string, completed_orders: integer >= 0, gross_total: MoneyDTO, return_refunds: MoneyDTO, revenue: MoneyDTO}]}`; công thức BR-REV-01/02 |

### 5.5. Auth, action và query

| Schema | Field và ràng buộc |
|---|---|
| `LoginInput` / `GoogleInput` | Login `{email: email <=254, password: string}`; Google `{id_token: string, consents?: ConsentInput[]}`. Audience lấy từ nhánh route, không nhận kind/aud do client tự đặt. Tạo Account Google mới phải có data_processing granted=true/phiên bản hiện hành theo CMP-01; thiếu trả422 DATA_PROCESSING_CONSENT_REQUIRED, chưa tạo Account/token. Account đã tồn tại không cần consent đăng ký lại và không ghi thêm Consent chỉ từ việc đăng nhập |
| `RegisterInput` | `{email, password, full_name: string 1..255, phone?: string <=20 = "", language?: vi hoặc en = vi, consents: ConsentInput[]}`; cần data_processing granted=true; không nhận kind/is_active/email_verified |
| `TokenPairDTO` | `{access_token: string, refresh_token: string, token_type: "Bearer", expires_in: integer > 0}`; chỉ BFF nhận, không đưa ra browser/session JSON |
| `RefreshInput` / `LogoutInput` | `{refresh_token: string}`; refresh endpoint tự xác minh refresh JWT, không yêu cầu access token còn hạn. Logout xác minh family đúng phiên/audience và thu hồi idempotent, BFF xoá cookie; không nhận family_id tuỳ ý |
| `EmailInput` / `EmailTokenInput` / `PasswordResetInput` | Email `{email}`; verify `{token: string}`; reset `{token: string, password: string}`. Không nhận account_id để đổi mật khẩu người khác |
| `AcceptedDTO` | `{status: "accepted"}` cho gửi email, không tiết lộ account tồn tại |
| `ProfilePatchInput` | full_name?: string <=255, phone?: string <=20, language?: vi/en, marketing_opt_in?: boolean, marketing_policy_version?: string <=32; khi đổi marketing phải có marketing_policy_version hiện hành đã hiển thị; field email/kind/read-only bị từ chối |
| `StaffCreateInput` / `StaffPatchInput` | Create `{email, full_name, password, phone?: string = ""}`; kind luôn staff. Patch chỉ full_name?, phone?, is_active?; không đổi kind/email hay tạo Admin qua API |
| `OrderCancelInput` | Store body rỗng; Staff `{reason: string 1..500, warehouse_return_required?: boolean}`; T14 bắt buộc boolean, các nhánh khác chỉ cho false/absent |
| `NoteInput` | `{note: string <=500}`; không chứa PII; return reject dùng field này, flag resolve body rỗng |
| `BulkInput` / `BulkResultDTO` | Input `{ids: UUID[]}` 1..100, không trùng; response `{results: [{id: UUID, http_status: integer, order: OrderSummaryDTO hoặc null, error: ErrorDTO.error hoặc null}]}` giữ thứ tự input. Confirm hợp lệ status200, hand-over đã nhận status202; từng đơn một transaction, lỗi đơn này không rollback đơn khác. Envelope HTTP200, không dùng 207; toàn request sai shape trả400 trước khi xử lý |
| `ShipmentAcceptedDTO` | `{order_id: UUID, shipment_id: UUID, status: enum Shipment.status}`; HTTP202, poll GET orders/{id}; nhận lệnh chưa có nghĩa tạo GHN thành công |
| `ErasureAcceptedDTO` | `{request_id: UUID, status: received hoặc processing hoặc completed hoặc rejected, completed_at: timestamp hoặc null}`; request_id là ID ErasureRequest, khác error.request_id truy vết HTTP |
| `PageQuery` / `ProductQuery` | Page `{page?: integer>=1 = 1, page_size?: integer>=1 = 24, lớn hơn 100 thì giới hạn ở 100}`; Product thêm category?: UUID, size?: code, color?: code, price_min?/price_max?: integer>=0, in_stock?: boolean, q?: string<=255, ordering?: newest/price/-price/best_selling = newest. Back-office thêm status?: enum Product.status; storefront không cho lọc draft/archived |
| `OrderQuery` / `StatusQuery` | Order = Page + status?, payment_method?, from?, to?, flag?: enum OrderFlag.kind, customer_id?: UUID, code?: string, phone?: string; storefront chỉ Page + status? theo US-402, không chấp nhận customer_id/phone để xem người khác. Status = Page + status?: enum của tài nguyên tương ứng; Stock = Page + variant_id?, warehouse_id?, available_lt?: integer>=0 = 5; Customer = Page + q?: string<=255 |
| `ReportQuery` | `{from: timestamp, to: timestamp, granularity?: day hoặc month = day}`; from < to, query CSV bỏ granularity |

### 5.6. Registry request/response của endpoint

Các route trong bảng ở mục 4 có schema tại đây; path params giữ UUID/code/slug như mục 1. `Patch<X>` chỉ cho field ghi của X theo PATCH semantics; `None` không body. `ErrorDTO` áp cho lỗi mọi operation trừ webhook/HTML/CSV. Khi bootstrap, mỗi operation phải khai báo request/response/status/permission/error schemas trong OpenAPI và có ví dụ trước khi frontend dùng; CI kiểm schema sinh lại theo12. Không tự sinh OpenAPI từ field model để lấp chỗ còn chưa triển khai.

Response lỗi mặc định do `shared.api.schema.AutoSchema` (`DEFAULT_SCHEMA_CLASS`) thêm vào mọi operation, theo thứ tự mã tăng dần, đều là `ErrorDTO`: 400 và 500 luôn có; 429 khi view có throttle; 404 khi path có tham số hoặc operation có query `page` (trang vượt quá cuối). View tự khai mã đặc thù (409, 422…) bằng `extend_schema(responses=…)`; mã view đã khai không bị ghi đè. 401/403 và 503 `AUTH_STATE_UNAVAILABLE` chưa khai mặc định, thêm cùng JWT ở M1.

| Nhánh / operation | Request hoặc query | Success response |
|---|---|---|
| store GET categories | None | 200 CategoryTreeDTO[] |
| store GET products / products/{slug} | ProductQuery / None | 200 Page<ProductSummaryDTO> / ProductDTO |
| store GET geo/provinces / geo/provinces/{code}/wards | None | 200 GeoDTO[] |
| store GET cart | None | 200 CartDTO |
| store POST cart/items; PATCH cart/items/{id} | CartAddInput; CartQuantityInput | 200 CartDTO, kể cả khi tạo giỏ mới |
| store DELETE cart/items/{id} | None | 204 |
| store POST cart/merge | None, X-Cart-Token bắt buộc | 200 CartMergeDTO; giỏ Guest đã gộp không còn quyền dùng token cũ |
| store POST checkout/quote; checkout | QuoteInput; CheckoutInput | 200 QuoteDTO; 201 CheckoutCreatedDTO hoặc 202 IdempotencyPendingDTO |
| store POST orders/{code}/payments | PaymentStartInput | 200/202 PaymentStartDTO |
| store POST orders/lookup | OrderLookupInput | 200 OrderLookupDTO |
| store GET orders; orders/{code} | PageQuery + status?; None | 200 Page<OrderSummaryDTO>; OrderDTO |
| store POST orders/{code}/cancel | None | 200 OrderDTO |
| store POST auth/register | RegisterInput | 202 AcceptedDTO cho mọi email hợp lệ về định dạng; không cấp token, không trả AccountDTO. Lỗi validate (mật khẩu yếu, thiếu consent) vẫn trả 400/422 vì không phụ thuộc email đã tồn tại |
| store POST auth/google | GoogleInput | 200 TokenPairDTO |
| store/backoffice POST auth/login; auth/refresh | LoginInput; RefreshInput | 200 TokenPairDTO |
| store/backoffice POST auth/logout | LogoutInput | 204; dùng refresh token để logout kể cả access token hết hạn |
| store POST auth/verify-email | EmailTokenInput | 204 |
| store POST auth/verify-email/resend; store/backoffice POST auth/password/forgot | EmailInput | 202 AcceptedDTO |
| store/backoffice POST auth/password/reset | PasswordResetInput | 204 |
| store GET me; PATCH me | None; ProfilePatchInput | 200 ProfileDTO |
| store GET/POST me/addresses | None / AddressInput | 200 AddressDTO[] / 201 AddressDTO |
| store PATCH/DELETE me/addresses/{id} | Patch<AddressInput> / None | 200 AddressDTO / 204 |
| store POST me/erasure-request | None | 201 ErasureDTO |
| backoffice GET orders; orders/{id} | OrderQuery; None | 200 Page<BackofficeOrderDTO>; BackofficeOrderDTO |
| backoffice POST orders/{id}/confirm; start-packing; flags/{flag_id}/resolve | None | 200 BackofficeOrderDTO |
| backoffice POST orders/{id}/cancel | OrderCancelInput | 200 BackofficeOrderDTO |
| backoffice POST orders/{id}/hand-over | None | 202 ShipmentAcceptedDTO |
| backoffice POST orders/bulk/confirm; orders/bulk/hand-over | BulkInput | 200 BulkResultDTO |
| backoffice POST orders/{id}/returned-to-warehouse | None | 200 BackofficeOrderDTO, replay không nhập kho thêm |
| backoffice GET/POST returns | StatusQuery / ReturnInput | 200 Page<ReturnDTO> / 201 ReturnDTO |
| backoffice POST returns/{id}/receive | None | 200 ReturnDTO |
| backoffice POST returns/{id}/accept; reject | ReturnAcceptInput; NoteInput | 200 ReturnDTO |
| backoffice GET refunds; POST refunds/{id}/complete | StatusQuery; RefundCompleteInput | 200 Page<RefundDTO>; RefundDTO |
| backoffice GET stock | Stock query tại5.5 | 200 Page<StockDTO> |
| backoffice POST stock/inbound; adjust; count | StockWriteInput theo từng lệnh | 200 StockDTO hoặc 202 IdempotencyPendingDTO |
| backoffice GET customers; customers/{id} | Customer query tại5.5; None | 200 Page<AccountDTO>; AccountDTO |
| backoffice GET/POST erasure-requests | StatusQuery / GuestErasureInput | 200 Page<ErasureDTO> / 201 ErasureDTO |
| backoffice POST erasure-requests/{id}/complete | None | 202 ErasureAcceptedDTO khi processing; 200 khi completed/rejected đã kết thúc |
| backoffice GET/POST categories | None / CategoryInput | 200 CategoryTreeDTO[] / 201 CategoryDTO |
| backoffice PATCH/DELETE categories/{id} | Patch<CategoryInput> / None | 200 CategoryDTO / 204 |
| backoffice GET products; products/{id} | ProductQuery; None | 200 Page<ProductSummaryDTO>; ProductDTO |
| backoffice POST/PATCH products; products/{id} | ProductInput / Patch<ProductInput> | 201 / 200 ProductDTO |
| backoffice DELETE products/{id} | None | 204 |
| backoffice POST products/{id}/publish; archive | None | 200 ProductDTO |
| backoffice POST products/{id}/variants | VariantCreateInput | 201 VariantDTO[] |
| backoffice PATCH products/{id}/variants/{variant_id} | VariantPatchInput | 200 VariantDTO |
| backoffice POST products/{id}/images | ImageInput multipart | 201 ImageDTO |
| backoffice PATCH/DELETE products/{id}/images/{image_id} | `{position: integer}` / None | 200 ImageDTO / 204 |
| backoffice GET/POST sizes; colors | PageQuery / SizeInput hoặc ColorInput | 200 Page<SizeDTO> hoặc Page<ColorDTO> / 201 SizeDTO hoặc ColorDTO |
| backoffice PATCH sizes/{id}; colors/{id} | Patch<SizeInput>; Patch<ColorInput> | 200 SizeDTO; ColorDTO |
| backoffice GET/POST sale-prices | PageQuery / SalePriceInput | 200 Page<SalePriceDTO> / 201 SalePriceDTO[] (một hoặc nhiều Variant) |
| backoffice PATCH/DELETE sale-prices/{id} | Patch<SalePriceInput> chỉ price/starts_at/ends_at / None | 200 SalePriceDTO / 204 |
| backoffice GET/POST vouchers; PATCH vouchers/{id} | PageQuery / VoucherInput; Patch<VoucherInput> | 200 Page<VoucherDTO> / 201 VoucherDTO; 200 VoucherDTO |
| backoffice GET/POST staff; PATCH staff/{id} | PageQuery / StaffCreateInput; StaffPatchInput | 200 Page<AccountDTO> / 201 AccountDTO; 200 AccountDTO |
| backoffice GET/PATCH settings/ordering; settings/shipping | None / Patch<OrderingSettingsDTO> hoặc Patch<ShippingSettingsDTO> | 200 DTO tương ứng |
| backoffice GET settings/ghn-locations; PATCH settings/ghn-locations/{ward_code} | PageQuery; GhnLocationInput | 200 Page<GhnLocationDTO>; GhnLocationDTO |
| backoffice GET reports/revenue; reports/paid-orders.csv | ReportQuery | 200 RevenueDTO; 200 text/csv UTF-8, Content-Disposition attachment |
| GET /healthz; /readyz | None | 200 `{status:"ok"}`; ready DB lỗi trả503 `{status:"unavailable"}` không lộ lỗi kết nối |
| GET /api/schema/; /api/docs/ | None | 200 OpenAPI document; HTML Swagger UI, chỉ môi trường được phép |
| webhooks vnpay/ipn; momo/ipn; ghn | Payload provider đã validate tại06 | ACK/status riêng tại06, không ErrorDTO |
| /dev/fake-gateway/… | Chỉ local/test được bật | HTML và thao tác giả lập theo06, không nằm trong client production |

CSV có các cột cố định `order_code`, `payment_method`, `paid_at`, `amount_received_vnd`, `order_status`, không email/phone/địa chỉ; chỉ đơn có khoản thanh toán gắn bằng Order.payment_id đã thu được xác minh, từ ngày thu tiền theo query; không cộng lần trả thừa vào cùng dòng đơn. Những trường hợp tiền thực nhận chưa xác định không tự coi là đã thu. CSV là báo cáo kế toán, không thay sổ đối chiếu tiền GHN chuyển khoản.
