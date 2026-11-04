# Kế hoạch triển khai theo module cho MVP

Status: draft

## 1. Mục tiêu và cách dùng

Tài liệu này chuyển phạm vi business đã chốt thành kế hoạch triển khai cho 8 module nghiệp vụ của Backend. Đây là tài liệu review trước khi tách thành spec và ticket; không thay thế tài liệu business, kiến trúc hoặc roadmap hiện có.

Nguyên tắc:

- Ranh giới module theo `docs/architecture/02-backend-structure.md`: `identity`, `catalog`, `inventory`, `promotions`, `payments`, `shipping`, `ordering`, `notifications`.
- Bao gồm story P1 và P2. Slice P2 được đánh dấu **Có thể hoãn** và không chặn luồng MVP cốt lõi.
- Mỗi slice dự kiến tương ứng một ticket/PR có thể review độc lập. Một transaction cần bảo toàn tính nhất quán không bị chia thành trạng thái trung gian không an toàn.
- Thứ tự triển khai bám M1–M6 trong `.scratch/mvp-roadmap/map.md`; M0 và M7 được thể hiện dưới dạng cross-cutting gate.
- Mọi tên domain dùng theo `GLOSSARY.md`. Khi chi tiết trong plan khác tài liệu nguồn, tài liệu nguồn sở hữu quyết định.

## 2. Bản đồ module và mốc

| Module | Sở hữu chính | Mốc triển khai | User story chính |
|---|---|---|---|
| `identity` | Tài khoản, xác thực, sổ địa chỉ, đồng ý xử lý dữ liệu, Yêu cầu xoá dữ liệu | M1, M6 | US-302, US-501–506, US-1001, US-1101–1102 |
| `catalog` | Danh mục, Sản phẩm, Biến thể, size, màu, ảnh, giá, Giá khuyến mãi | M1 | US-101–104, US-801–805 |
| `inventory` | Kho, Tồn kho, Giữ hàng, Hàng chờ xuất, Kiểm kê | M1–M5 | US-201, US-305–307, US-603–604, US-607, US-701–703 |
| `promotions` | Voucher và lượt dùng Voucher | M2–M4 | US-304, US-901 |
| `payments` | Thanh toán, Cổng thanh toán, COD, Hoàn tiền, Đối soát | M2, M3, M5 | US-305–306, US-403, US-605, US-608 |
| `shipping` | Báo giá phí ship, GHN, Vận đơn, webhook, Đối soát | M2, M4 | US-303, US-603, US-609, US-1004 |
| `ordering` | Giỏ hàng, Tính thử, checkout, Đơn hàng, vòng đời, Đổi trả, báo cáo | M2–M6 | US-201–403, US-601–609, US-1002–1003, US-1101–1102 |
| `notifications` | Email phát sinh từ sự kiện nội bộ | M2–M6 | BR-NTF-01–03 và các story phát sự kiện nguồn |

### 2.1. Thứ tự phụ thuộc tổng quát

1. M1 dựng `identity` lõi, `catalog` và `inventory` để Admin tạo Sản phẩm, Staff nhập kho và Người mua duyệt hàng.
2. M2 thêm `promotions`, phần báo giá của `shipping`, COD của `payments`, rồi ghép tại `ordering` thành Giỏ hàng → Tính thử → checkout COD.
3. M3 hoàn thiện Thanh toán online và các transition T3–T5 tại `ordering`.
4. M4 hoàn thiện fulfillment: T6–T14, Vận đơn, webhook, tra cứu và xử lý ngoại lệ.
5. M5 thêm Đổi trả, Hoàn tiền thủ công và Doanh thu.
6. M6 hoàn thiện Tài khoản Khách hàng, gắn đơn vãng lai và quyền riêng tư.

### 2.2. Thứ tự khởi tạo module

Thứ tự dưới đây là thứ tự module được đưa vào sử dụng lần đầu, không có nghĩa phải hoàn tất toàn bộ một module rồi mới bắt đầu module kế tiếp. Các module như `inventory`, `payments`, `shipping`, `ordering` và `notifications` tiếp tục được mở rộng ở nhiều mốc.

| Thứ tự | Module | Bắt đầu | Lý do đứng trước module kế tiếp |
|---:|---|---|---|
| 1 | `identity` | M1 | JWT và permission thật phải có trước mọi endpoint back-office của `catalog` và `inventory` |
| 2 | `catalog` | M1 | `Product`/`Variant` và giá là dữ liệu gốc để tạo `StockItem` và storefront |
| 3 | `inventory` | M1 | Cần `Variant`; cung cấp availability trước khi mở storefront và checkout |
| 4 | `promotions` | M2 | Cung cấp Voucher quote/redemption cho Tính thử và checkout COD |
| 5 | `shipping` | M2 | Cung cấp báo giá GHN/Fake và Phí ship dự phòng cho Tính thử |
| 6 | `payments` | M2 | Cung cấp Payment COD trước checkout COD, rồi mở rộng online ở M3 |
| 7 | `ordering` | M2 | Orchestrate contract của `catalog`, `inventory`, `promotions`, `shipping` và `payments` |
| 8 | `notifications` | M2 | Chỉ bắt đầu khi `ordering` phát sự kiện nghiệp vụ đầu tiên; sau đó mở rộng theo từng mốc |

Ba module `promotions`, `shipping` và `payments` thuộc cùng **execution wave**: có thể triển khai song song sau nền M1. Số 4–6 chỉ là tie-break để đọc và tạo ticket, không biểu thị phụ thuộc trực tiếp giữa ba module. `notifications` đứng sau `ordering` khi khởi tạo, nhưng mỗi email mới phải được làm cùng mốc với sự kiện nguồn, không dồn đến cuối dự án.

### 2.3. Execution waves

| Wave | Module / phần module | Kết quả mở khoá |
|---|---|---|
| W1 | `identity` lõi | Xác thực Staff/Admin và hai audience JWT |
| W2 | `catalog` nền | Danh mục, Sản phẩm, Biến thể, giá và contract cho module khác |
| W3 | `inventory` nền | Tồn kho, availability, Nhập kho/điều chỉnh/Kiểm kê |
| W4 | `promotions` + `shipping` + `payments` nền | Đủ contract để dựng Tính thử và checkout COD |
| W5 | `ordering` | Giỏ hàng, Tính thử, checkout và vòng đời Đơn hàng |
| W6 | `notifications` | Email theo sự kiện đã tồn tại |
| W7 | Mở rộng các module theo M3–M6 | Thanh toán online, fulfillment, Đổi trả, quyền riêng tư |

## 3. Plan module `identity`

### Phạm vi và public contract

- Sở hữu `Account`, vai trò Customer/Staff/Admin, JWT, phiên đăng nhập, xác thực email, Google, quên mật khẩu, hồ sơ, sổ địa chỉ, bằng chứng đồng ý, Yêu cầu xoá dữ liệu và lịch sử Staff truy cập dữ liệu.
- Cung cấp contract để module khác kiểm tra/đọc danh tính, ghi đồng ý, ghi lịch sử truy cập, bắt đầu ẩn danh và phản ứng khi email được xác thực.
- Không sở hữu Đơn hàng hay điều kiện hoàn tất Yêu cầu xoá dữ liệu; `ordering` kiểm tra các điều kiện đó rồi yêu cầu `identity` thực hiện.

### Slices

| ID | Mốc | Slice / kết quả | Dependency | Truy vết |
|---|---|---|---|---|
| ID-01 | M1 | Hoàn thiện JWT login/refresh/logout cho storefront và back-office; audience tách biệt, vô hiệu phiên Staff ngay khi tài khoản bị vô hiệu | M0 `Account`, JWT keyring, Redis fail-open/fail-closed theo kiến trúc | US-502, US-1001; quy tắc phân quyền |
| ID-02 | M1 | Permission và API tối thiểu cho Staff/Admin để mở endpoint quản trị M1; audit thao tác ghi back-office | ID-01, shared API/audit | US-701–703, US-801–805 |
| ID-03 | M2 | Contract nhận diện Khách vãng lai/Khách hàng khi checkout và lưu bằng chứng đồng ý theo phiên bản chính sách | ID-01 | US-301–302; CMP-01–03 |
| ID-04 | M6 | Đăng ký email với response `202` không lộ email tồn tại; xác thực email và phát sự kiện `EmailVerifiedV1` | `notifications` gửi link | US-501; BR-ORD-08 |
| ID-05 | M6 | Google login và chặn email thuộc Tài khoản nội bộ dùng storefront | ID-01, adapter Google | US-502 |
| ID-06 | M6 | Quên/đặt lại mật khẩu, token một lần và vô hiệu theo chính sách bảo mật | `notifications` | US-503 |
| ID-07 | M6 | Hồ sơ, ngôn ngữ và sổ địa chỉ; không cho Khách hàng tự đổi email | ID-01, shared geo | US-302, US-504–506 **Có thể hoãn** |
| ID-08 | M6 | Admin tạo/sửa/vô hiệu Staff bằng service hiện có; không tạo Admin qua API | ID-01/02 | US-1001 |
| ID-09 | M6 | Ghi lịch sử Staff xem dữ liệu Người mua với đúng phạm vi action; API tra cứu lịch sử | shared audit | US-1102 **Có thể hoãn**; CMP-07 |
| ID-10 | M6 | Vòng đời Yêu cầu xoá dữ liệu, HMAC số điện thoại làm bằng chứng, phát sự kiện ẩn danh và chỉ completed khi mọi Event delivery bắt buộc hoàn tất | outbox operations; contract từ `ordering` | US-1101; CMP-05–06; ADR 0016 |

### Kiểm thử bắt buộc

- Token storefront không gọi được back-office và ngược lại; refresh rotation/replay và vô hiệu Staff có test.
- Đăng ký email mới và email đã tồn tại trả response không phân biệt; không gửi email sai đối tượng.
- Email nội bộ bị từ chối ở storefront với thông báo chung.
- Yêu cầu xoá dữ liệu giữ `processing` khi một handler lỗi, retry không tạo thêm tác vụ ẩn danh, và chỉ hoàn tất khi mọi handler bắt buộc `completed`.
- Audit chỉ ghi khi mở chi tiết Khách hàng, chi tiết Đơn hàng hoặc tìm theo số điện thoại; không ghi khi mở danh sách.

### Definition of Done

- Permission matrix trong `02-actors-permissions.md` có test API đại diện cho từng audience/role.
- Không còn email/số điện thoại thô trong bằng chứng sau ẩn danh; dữ liệu kế toán/thuế được giữ đúng CMP-05.
- Event schema và contract được kiểm tra; OpenAPI phản ánh đầy đủ lỗi 401/403/409/422/503 liên quan.

## 4. Plan module `catalog`

### Phạm vi và public contract

- Sở hữu Danh mục, Sản phẩm, Biến thể, danh sách size, bảng màu, ảnh theo màu, Giá bán, Giá khuyến mãi, bản sao trạng thái còn hàng và số liệu bán chạy.
- Cung cấp snapshot Biến thể/giá cho `ordering`, dữ liệu Biến thể cho `inventory`, và contract cập nhật trạng thái còn hàng/số liệu bán chạy.

### Slices

| ID | Mốc | Slice / kết quả | Dependency | Truy vết |
|---|---|---|---|---|
| CAT-01 | M1 | Model và constraint cho Danh mục dạng cây, size, màu; quy tắc chỉ ẩn khi đã được dùng | shared base model | BR-CAT-10–11; US-801, US-805 |
| CAT-02 | M1 | Model Sản phẩm, Biến thể và ảnh theo màu; unique size×màu, SKU toàn hệ thống, cân nặng bắt buộc | CAT-01 | BR-CAT-01–06, BR-CAT-09; US-802 |
| CAT-03 | M1 | Giá bán và Giá khuyến mãi với exclusion/validation thời gian, Giá áp dụng và chặn Giá bán xung đột | CAT-02, PostgreSQL constraint | BR-PRC-01–05; US-804 |
| CAT-04 | M1 | Back-office CRUD và transition `draft`/`active`/`archived`; quyền Admin và audit | ID-02, CAT-01–03 | BR-CAT-07–09; US-801–805 |
| CAT-05 | M1 | Storefront danh sách/chi tiết, phân trang, filter size/màu/giá, sắp xếp; sản phẩm hết hàng vẫn hiển thị | CAT-02/03, inventory projection | US-101–102, US-104; BR-CAT-08 |
| CAT-06 | M1 | Tìm tên không phân biệt hoa thường/dấu bằng PostgreSQL; từ khoá rỗng và chuỗi con liên tiếp | CAT-05, `unaccent` | US-103; BR-CAT-13 |
| CAT-07 | M4 | Projection bán chạy 30 ngày và contract cập nhật từ job của `ordering` | Đơn hàng đã có vòng đời đủ | US-102; BR-CAT-12 |

### Kiểm thử bắt buộc

- Constraint DB cho SKU, size×màu, giá nguyên dương và khoảng Giá khuyến mãi chồng nhau.
- Thay đổi Giá bán đồng thời với tạo Giá khuyến mãi không tạo trạng thái vi phạm.
- Filter size + màu chỉ khớp cùng một Biến thể còn hàng; filter giá dùng Giá áp dụng.
- Tìm `ao thun`, `áo thun`, chữ hoa/thường cho cùng kết quả; không sửa lỗi gõ hay đảo từ.
- Archived/hết hàng và dữ liệu snapshot của Dòng đơn hàng không bị lẫn trách nhiệm.

### Definition of Done

- Admin tạo được Sản phẩm đầy đủ và Người mua duyệt/tìm/filter đúng US-101–104.
- Public contract không để module khác import model/service nội bộ.
- Query danh sách có kiểm tra số query và index phù hợp với NFR.

## 5. Plan module `inventory`

### Phạm vi và public contract

- Sở hữu Kho, Tồn kho, Giữ hàng, Hàng chờ xuất, Nhập kho, điều chỉnh, Kiểm kê và lịch sử mọi thay đổi.
- Mọi thay đổi số lượng đi qua service có khoá dòng; `ordering` chỉ gọi public contract.

### Slices

| ID | Mốc | Slice / kết quả | Dependency | Truy vết |
|---|---|---|---|---|
| INV-01 | M1 | Kho MVP và `StockItem` theo Biến thể×Kho; selector Số lượng bán được không âm | CAT-02 | BR-INV-01–02 |
| INV-02 | M1 | Nhập kho/điều chỉnh với lý do, actor và lịch sử bất biến; giảm không vượt Số lượng bán được | INV-01, ID-02 | US-701–702; BR-INV-09, BR-INV-11 |
| INV-03 | M1 | Kiểm kê tính chênh lệch từ hàng trên kệ tại thời điểm xác nhận | INV-01/02 | US-703; BR-INV-10–12 |
| INV-04 | M2 | Contract đọc availability và commit COD nguyên tử: khoá theo thứ tự ổn định, trừ Tồn kho, tạo Hàng chờ xuất | INV-01, M0 idempotency | US-305, US-307; BR-INV-04, BR-INV-06 |
| INV-05 | M3 | Giữ hàng online 15 phút, commit/release/expired; retry và tiền về sát hạn không bán vượt tồn | INV-04 | US-306; BR-INV-05–07 |
| INV-06 | M4 | Xoá Hàng chờ xuất khi Vận đơn tạo xong; trả lại khi huỷ trước Đang giao | INV-04, ordering transition | US-603–604; BR-INV-07, BR-INV-10 |
| INV-07 | M4/M5 | Nhập lại hàng Hoàn hàng hoặc phần Đổi trả được chấp nhận; idempotent theo thao tác nguồn | INV-02, ordering return flow | US-607, US-606; BR-INV-08 |

### Kiểm thử bắt buộc

- Hai transaction cùng mua Biến thể cuối cùng: đúng một đơn thành công, Số lượng bán được không âm.
- Deadlock/race test dùng thứ tự khoá Biến thể ổn định cho giỏ nhiều dòng.
- Retry cùng idempotency key không trừ Tồn kho, tạo Giữ hàng, Hàng chờ xuất hoặc nhập lại lần hai.
- Giữ hàng quá hạn không còn làm giảm Số lượng bán được dù job chưa giải phóng.
- Kiểm kê đang cạnh tranh với checkout tính lại dưới khoá và không giảm phần đã giữ/bán.

### Definition of Done

- Mọi delta có lịch sử loại, số lượng, đơn liên quan và actor; không có đường ghi số lượng trực tiếp từ API.
- Contract trả lỗi domain đủ dữ liệu để `ordering` báo Biến thể thiếu và số còn lại.
- Test concurrency chạy trên PostgreSQL, không thay bằng SQLite/mock lock.

## 6. Plan module `promotions`

### Phạm vi và public contract

- Sở hữu Voucher, điều kiện sử dụng và Lượt dùng Voucher.
- Giá khuyến mãi không thuộc module này mà thuộc `catalog`.

### Slices

| ID | Mốc | Slice / kết quả | Dependency | Truy vết |
|---|---|---|---|---|
| PRO-01 | M2 | Model Voucher, mã uppercase, loại phần trăm/số tiền, thời gian, minimum, tổng/per-Shopper limit | ID-03 | US-901; BR-VCH-01–07, BR-VCH-09–10 |
| PRO-02 | M2 | Contract validate/quote Voucher cho Tính thử, trả lý do cụ thể và phép tính số nguyên | PRO-01 | US-304; BR-VCH-02–06, BR-VCH-10 |
| PRO-03 | M2 | Reserve Lượt dùng trong transaction checkout theo Tài khoản hoặc HMAC số điện thoại; chống vượt hạn mức khi cạnh tranh | PRO-01/02, ordering checkout | BR-VCH-04, BR-VCH-07–08 |
| PRO-04 | M3/M4 | Trả lượt khi huỷ trước Đang giao; không trả ở T14; thao tác lặp không thay đổi bộ đếm lần hai | ordering transitions | BR-VCH-08; T4/T5/T7/T9/T14 |
| PRO-05 | M2 | Back-office tạo/sửa/vô hiệu Voucher với quyền Admin và audit | ID-02 | US-901 |

### Kiểm thử bắt buộc

- Tính phần trăm làm tròn xuống, cap tối đa và không vượt Tạm tính; không dùng float.
- Hai checkout cạnh tranh ở lượt cuối chỉ một checkout dùng được Voucher.
- Một Customer đổi sang checkout như Guest bằng cùng số điện thoại không vượt per-Shopper limit.
- Huỷ/retry/event lặp không trả lượt hai lần; T14 giữ lượt.

### Definition of Done

- Public contract tách validate khỏi reserve nhưng checkout luôn kiểm tra lại và reserve trong transaction.
- Lý do Voucher không hợp lệ ổn định cho API; không rò rỉ dữ liệu Người mua khác.

## 7. Plan module `payments`

### Phạm vi và public contract

- Sở hữu Payment online/COD, từng lần thử Cổng thanh toán, IPN, adapter VNPay/MoMo/Fake, Hoàn tiền và Đối soát.
- Không tự chuyển trạng thái Đơn hàng; phát sự kiện để `ordering` quyết định theo trạng thái hiện tại.

### Slices

| ID | Mốc | Slice / kết quả | Dependency | Truy vết |
|---|---|---|---|---|
| PAY-01 | M2 | Payment COD và contract start/collect/cancel idempotent | ordering reference | US-305; BR-PAY-01, BR-SHP-07 |
| PAY-02 | M3 | Model Payment/attempt và Fake Gateway; chuẩn bị trong transaction, gọi provider ngoài transaction, operation ID ổn định | M0 idempotency/outbox | US-306; ADR 0013 |
| PAY-03 | M3 | Adapter VNPay/MoMo theo interface chung và link hết hạn từ `ordering`; local/test dùng Fake | PAY-02 | BR-PAY-01 |
| PAY-04 | M3 | IPN xác minh chữ ký, chống trùng và chỉ xác nhận server-to-server; phát `PaymentSucceededV1`/`PaymentFailedV1` | PAY-02/03 | BR-PAY-02–04 |
| PAY-05 | M3 | Recovery payment initialization và Đối soát Payment treo; lease chống hai worker cùng xử lý | PAY-02/03 | US-306; BR-PAY-02 |
| PAY-06 | M3 | Model/contract yêu cầu Hoàn tiền gắn đúng Payment, request key ổn định, tổng không vượt tiền nhận | PAY-04 | US-608; BR-REF-01–02, BR-REF-05–06 |
| PAY-07 | M5 | Staff ghi nhận Hoàn tiền thủ công cho online/COD, phát `RefundRecordedV1`, audit mã tham chiếu | PAY-06, ID-02 | US-605; BR-REF-03–04 |
| PAY-08 | M6 | Redact raw provider payload theo Yêu cầu xoá dữ liệu nhưng giữ dữ liệu cần cho đối soát/kế toán | ID-10 | CMP-05 và retention gate |

### Kiểm thử bắt buộc

- IPN chữ ký sai, số tiền sai, trùng và tới không theo thứ tự; Return URL không xác nhận Thanh toán.
- Hai tab thanh toán tạo hai Payment; khoản thứ hai được phát hiện để hoàn mà không làm sống lại/chuyển lại đơn.
- Timeout khi khởi tạo provider đi qua `unknown`/recovery, không tạo Payment/provider operation mới.
- Hoàn tiền retry cùng key trả cùng bản ghi; khác tham số conflict; tổng requested+completed không vượt tiền nhận.
- Job Đối soát và IPN chạy đồng thời chỉ phát một sự kiện thành công có hiệu lực.

### Definition of Done

- Fake Gateway chạy hết flow M3; adapter thật chỉ được coi là nghiệm thu ở M7 sandbox.
- Raw payload không xuất hiện trong log/audit; secret và chữ ký dùng helper tập trung.
- Các handler downstream có thể xử lý event lặp và event đến muộn.

## 8. Plan module `shipping`

### Phạm vi và public contract

- Sở hữu báo giá phí ship, cấu hình Phí ship dự phòng, ánh xạ địa chỉ GHN, Vận đơn, adapter Fake/GHN, webhook và Đối soát.
- Ngưỡng miễn phí ship thuộc `ordering`; `shipping` trả báo giá và nguồn báo giá.

### Slices

| ID | Mốc | Slice / kết quả | Dependency | Truy vết |
|---|---|---|---|---|
| SHP-01 | M2 | Interface báo giá và Fake GHN; tính tổng cân nặng, cache theo request chuẩn hoá, timeout dùng Phí ship dự phòng | CAT-02, shared geo | US-303; BR-SHP-01–02 |
| SHP-02 | M2 | Back-office cấu hình Phí ship dự phòng và kích thước gói, có audit | ID-02 | US-1002; BR-SHP-04 |
| SHP-03 | M4 | Model Vận đơn và request tạo Vận đơn với mã thao tác ổn định; provider call ngoài transaction | ordering hand-over | US-603; BR-SHP-05 |
| SHP-04 | M4 | Fake GHN và adapter GHN cho create/cancel/query; lease và recovery `creation_unknown` | SHP-03 | BR-SHP-05–06 |
| SHP-05 | M4 | Webhook xác thực/chống trùng, chuyển provider status thành event domain; giữ sự kiện tới sớm để retry downstream | SHP-04, outbox | US-603, US-609; BR-SHP-06–08 |
| SHP-06 | M4 | Job Đối soát Vận đơn và retry cancellation; Cờ cần xử lý do `ordering` sở hữu | SHP-04/05 | BR-SHP-06, BR-SHP-08 |
| SHP-07 | M4 | Quản lý ánh xạ phường/xã sang GHN, chỉ giữ nếu sandbox xác nhận GHN chưa hỗ trợ mã 2 cấp trực tiếp | shared geo, M7 fact check | US-1004 |
| SHP-08 | M6 | Redact `creation_input`/payload theo Yêu cầu xoá dữ liệu trong giới hạn retention đã chốt | ID-10 | CMP-05 và retention gate |

### Kiểm thử bắt buộc

- GHN timeout ở quote trả Phí ship dự phòng và nguồn fallback; cache fallback không lẫn cache quote thật.
- Timeout create không tạo Vận đơn lần hai; retry query theo mã shop ổn định.
- Webhook trùng, sớm, muộn và mâu thuẫn; status provider lạ không chuyển trạng thái đơn.
- Staff huỷ khi Vận đơn `requested/creation_unknown` bị chặn ở `ordering`; Vận đơn tạo sau khi đơn huỷ kích hoạt yêu cầu huỷ và cờ.

### Definition of Done

- Flow Fake GHN từ bàn giao đến Đã giao/Hoàn hàng/sự cố chạy hết ở M4.
- Không tuyên bố adapter thật hoàn tất trước M7 sandbox; các giả định xác thực webhook và địa chỉ được ghi trong Fog.

## 9. Plan module `ordering`

### Phạm vi và public contract

- Sở hữu Giỏ hàng, Tính thử, checkout, Đơn hàng/Dòng đơn hàng, Mã đơn, vòng đời T1–T14, Cờ cần xử lý, Đổi trả, cấu hình Ngưỡng miễn phí ship/Hạn mức COD và báo cáo Doanh thu.
- Là orchestration layer; gọi contract của module khác nhưng không import nội bộ. Mọi transition khoá Đơn hàng và nằm trong `services/transitions.py`.

### Slices

| ID | Mốc | Slice / kết quả | Dependency | Truy vết |
|---|---|---|---|---|
| ORD-01 | M2 | Giỏ hàng server cho Guest/Customer, TTL 30 ngày, giới hạn 10/Biến thể, giá hiện tại và merge khi đăng nhập | CAT-05, INV-01, ID-03 | US-201–204; BR-CRT-01–05 |
| ORD-02 | M2 | Tính thử chứa dòng, giá, Voucher, Phí ship, tổng, expiry và `quote_token`; dữ liệu canonical để checkout so lại | catalog/promotions/shipping contracts | US-303–304, US-308; BR-ORD-01, BR-ORD-07, BR-ORD-09 |
| ORD-03 | M2 | Model Order/OrderLine/address/invoice snapshot, Mã đơn ngẫu nhiên, phân bổ Voucher ổn định theo dòng | ORD-02 | US-301–302; BR-ORD-02–05 |
| ORD-04 | M2 | Checkout COD nguyên tử: khoá/kiểm lại quote, commit Tồn kho, Lượt dùng Voucher, COD Payment, xóa dòng giỏ đã mua, phát `OrderPlacedV1` | INV-04, PRO-03, PAY-01 | US-305, US-307–308; T2 |
| ORD-05 | M2 | Cấu hình Ngưỡng miễn phí ship/Hạn mức COD và cờ phí ship dự phòng | ID-02, SHP-01/02 | US-303, US-1002; BR-SHP-02–04, BR-PAY-06 |
| ORD-06 | M3 | Checkout online T1, tạo Giữ hàng/Payment attempt, API thử lại Cổng thanh toán trong cửa sổ cho phép | INV-05, PAY-02–05 | US-306; BR-INV-05, BR-PAY-01 |
| ORD-07 | M3 | Handler thanh toán và T3/T4/T5: thành công, hết hạn, tự huỷ; tiền sai/đến muộn/đến lần hai tạo Hoàn tiền + Cờ cần xử lý | ORD-06, PAY-04/06 | US-403, US-608; BR-PAY-04–05; lifecycle 4.1/4.6 |
| ORD-08 | M4 | Back-office queue, T6 xác nhận, T8 đóng gói, bàn giao bất đồng bộ T10 | SHP-03–06, INV-06 | US-601–603 |
| ORD-09 | M4 | Huỷ T7/T9/T14, bắt lý do, hoàn kho/Hoàn tiền/Voucher đúng trạng thái và chặn khi Vận đơn chưa rõ | ORD-07/08 | US-604, US-609; lifecycle 4.3/4.5/4.7 |
| ORD-10 | M4 | Handler Vận đơn cho T11/T12, nhận hàng Hoàn hàng, COD collected và job T13 | ORD-08/09, PAY-01, INV-07 | US-607, US-609; lifecycle T11–T13 |
| ORD-11 | M4 | Guest lookup token 30 phút, tra Mã đơn+số điện thoại và lịch sử Customer; permission đúng quyền sở hữu | ID-01/03 | US-401–402 |
| ORD-12 | M4 | Cờ cần xử lý: tạo idempotent, danh sách, chi tiết và gỡ có audit | ID-02 | US-601, US-608–609 |
| ORD-13 | M5 | Vòng đời Đổi trả riêng; validate 7 ngày, mức Giá khuyến mãi, nhận hàng, chấp nhận theo dòng/restock và từ chối | ORD-10, INV-07 | US-606; BR-RET-01–09 |
| ORD-14 | M5 | Tính Hoàn tiền Đổi trả lũy kế, liên kết Refund và chuyển `refunded` khi ghi nhận hoặc khi tổng bằng 0 | ORD-13, PAY-06/07 | US-605–606; BR-RET-07 |
| ORD-15 | M5 | Báo cáo Doanh thu và xuất đơn đã thu tiền theo ngày, gồm invoice info | ORD-10/14 | US-1003 **Có thể hoãn**; BR-REV-01–02 |
| ORD-16 | M4 | Job bán chạy 30 ngày gọi contract `catalog` | ORD-10, CAT-07 | BR-CAT-12 |
| ORD-17 | M6 | Gắn đơn Guest theo email đã xác thực; không gắn theo số điện thoại | ID-04 | BR-ORD-08 |
| ORD-18 | M6 | Điều phối Yêu cầu xoá dữ liệu: kiểm đơn cuối/không Hoàn tiền chờ, ẩn danh order PII và gọi `identity` | ID-10, PAY-08, SHP-08 | US-1101; CMP-05 |
| ORD-19 | M6 | Gọi contract audit khi Staff xem chi tiết/tìm theo số điện thoại | ID-09 | US-1102 **Có thể hoãn**; CMP-07 |

### Kiểm thử bắt buộc

- Checkout COD/online retry cùng Idempotency-Key trả cùng kết quả; khác payload conflict; rollback không để lại tài nguyên một phần.
- Quote khác ở bất kỳ dòng/giá/điều kiện nào đều bị từ chối dù tổng tình cờ bằng nhau.
- Mọi T1–T14 có test transition hợp lệ, transition cấm, event trùng/sớm/muộn và hai transition cạnh tranh.
- Job huỷ đơn hết hạn dừng khi event delivery lag vượt 60 giây; tiền về sát phút 15 theo đúng lifecycle.
- Voucher allocation và Đổi trả nhiều lần khớp ví dụ BR-ORD-02/BR-RET-07, kể cả tổng hoàn bằng 0.
- Nhận Hoàn hàng/Đổi trả retry không nhập kho hoặc yêu cầu Hoàn tiền hai lần.
- Permission Guest lookup token, Mã đơn+số điện thoại, Customer ownership và Staff/Admin được test độc lập.

### Definition of Done

- State machine là nguồn cưỡng chế duy nhất; view/handler không sửa `Order.status` trực tiếp.
- Flow end-to-end Fake provider chạy được: COD và online → đóng gói → Vận đơn → Đã giao/Hoàn hàng → Đổi trả → Hoàn tất.
- Mọi side effect liên module nằm cùng transaction khi contract chỉ ghi DB; HTTP provider luôn ngoài transaction.

## 10. Plan module `notifications`

### Phạm vi và public contract

- Sở hữu `EmailLog`, template vi/en, scheduling/retry/lease và adapter email.
- Chỉ phản ứng với sự kiện; không sở hữu trạng thái nghiệp vụ nguồn. Payload sự kiện không chứa PII, handler đọc dữ liệu qua contract.

### Slices

| ID | Mốc | Slice / kết quả | Dependency | Truy vết |
|---|---|---|---|---|
| NTF-01 | M2 | `EmailLog`, adapter Mailpit/SES, render template, lease/retry/recovery và unique event+template | M0 outbox/tasks | BR-NTF-01–03 |
| NTF-02 | M2 | Email đặt COD thành công; bỏ qua Guest không có email; lưu ngôn ngữ snapshot | ORD-04 | US-305; BR-NTF-01–03 |
| NTF-03 | M3 | Email thanh toán online thành công, huỷ có điều kiện và unexpected payment | ORD-07, PAY events | US-306, US-403, US-608 |
| NTF-04 | M4 | Email Đang giao và Đã giao; đơn bị huỷ theo các transition đủ điều kiện | ORD-08–10 | US-603–604 |
| NTF-05 | M5 | Email Hoàn tiền được ghi nhận | PAY-07 | US-605; BR-NTF-01 |
| NTF-06 | M6 | Email xác thực và đặt lại mật khẩu; link chỉ được cấp lúc task thực sự gửi | ID-04/06 | US-501, US-503 |
| NTF-07 | M6 | Khi Customer erased: ẩn danh địa chỉ nhận, huỷ email chưa gửi và vô hiệu lease đang chạy | ID-10 | CMP-05 |

### Kiểm thử bắt buộc

- Event lặp chỉ tạo một EmailLog/template; worker retry không gửi hai lần sau khi ghi `sent`.
- Worker chết giữa claim/send/finalize được recovery theo lease; stale worker không ghi đè kết quả mới.
- Đơn online chưa thanh toán không nhận email huỷ; unexpected payment vẫn nhận email nếu có địa chỉ.
- Template chọn theo ngôn ngữ, nhưng tên Sản phẩm giữ tiếng Việt.
- Erasure cạnh tranh với worker gửi: email chưa gửi bị huỷ và không lộ địa chỉ sau đó.

### Definition of Done

- Mỗi trường hợp BR-NTF-01 có handler và contract test event tương ứng.
- EmailLog retention 90 ngày có job che địa chỉ/số tiền theo `06-compliance.md`.
- Lỗi provider không rollback nghiệp vụ nguồn và quan sát được qua log/Sentry.

## 11. Cross-cutting gates

### Gate trước khi mở module mới

- M0 core liên quan phải xanh: event/outbox, idempotency, API base, geo, audit context, import boundaries và coverage gate.
- Hoàn tất hoặc chấp nhận rõ backlog M0 chặn an toàn cho slice đang làm; không kéo toàn bộ backlog không liên quan vào mốc.
- Đọc ADR liên quan và `docs/architecture/13-python-django-coding-style.md` trước khi sửa Python/Django.

### Gate cho từng ticket/PR

- Có traceability tới US/BR/CMP và chỉ rõ tài liệu sở hữu quyết định.
- Migration có constraint/index và test migration khi thay đổi dữ liệu hiện hữu.
- Service ghi, selector đọc, view mỏng; chuyển trạng thái model dùng method nhận `now` theo convention hiện tại.
- Chỉ dùng `contracts.py`/event để đi qua module; chạy generator import-linter khi thêm module path/FK ngoại lệ.
- Endpoint ghi có chiến lược idempotency; worker/provider call có operation ID, lease và recovery phù hợp.
- Event có schema/version/name cố định, payload không chứa PII; handler retry/idempotent.
- OpenAPI được sinh và commit cùng thay đổi endpoint.
- Chạy `make fmt`, `make lint`, test tương xứng và coverage branch ≥ 80% cho service/handler chịu gate.

### Gate tích hợp theo mốc

| Mốc | Gate chấp nhận |
|---|---|
| M1 | Admin tạo Sản phẩm → Staff nhập kho → Người mua tìm/filter đúng; JWT hai audience hoạt động |
| M2 | Flow COD hoàn chỉnh với Fake GHN quote, Voucher, concurrency Biến thể cuối và EmailLog |
| M3 | Flow online thành công/hết hạn/trả hai lần/sai số tiền với Fake Gateway |
| M4 | Checkout → đóng gói → Vận đơn → Đã giao/Hoàn hàng/huỷ sự cố chạy hết với Fake GHN |
| M5 | Đổi trả nhiều lần, làm tròn Hoàn tiền và Doanh thu có test ví dụ chuẩn |
| M6 | Đăng ký/login/profile và Yêu cầu xoá dữ liệu end-to-end; handler lỗi không báo hoàn tất sớm |
| M7 | Sandbox VNPay/MoMo/GHN, k6 staging và checklist pháp lý/go-live được xác minh |

### Gate trước go-live

- Pháp chế/kế toán chốt CMP-06, CMP-08, CMP-09, hoá đơn điện tử và thời hạn lưu raw payload/`creation_input`/địa chỉ Đơn hàng.
- Thông báo website với Bộ Công Thương hoàn tất.
- Adapter thật được kiểm tra chữ ký, mã kết quả, timeout, retry và webhook qua sandbox/tunnel; giả định US-1004 được giữ hoặc loại bằng bằng chứng GHN.
- Test tải xác minh giả định 500–5.000 đơn/ngày; theo dõi event delivery lag, queue, Payment/Vận đơn treo và Cờ cần xử lý.

## 12. Thứ tự tách spec/ticket đề xuất

Không tạo toàn bộ ticket M1–M6 cùng lúc. Khi mốc trước gần xong, tách mốc kế tiếp theo dependency dưới đây:

1. M1: ID-01/02 → CAT-01/02 + INV-01 → CAT-03/04 + INV-02/03 → CAT-05/06.
2. M2: PRO-01/02 + SHP-01/02 + PAY-01 → ORD-01/02/03/05 → PRO-03 + INV-04 → ORD-04 → NTF-01/02.
3. M3: PAY-02–05 + INV-05 → ORD-06/07 + PAY-06 → PRO-04 → NTF-03.
4. M4: SHP-03–06 → ORD-08/12 → INV-06 + ORD-09/10 → ORD-11/16 + CAT-07 → NTF-04; SHP-07 sau khi có kết quả sandbox liên quan.
5. M5: PAY-07 + ORD-13 → INV-07 + ORD-14 → NTF-05 → ORD-15 (**Có thể hoãn**).
6. M6: ID-04–08 → ORD-17 → ID-09 + ORD-19 (**Có thể hoãn**) → ID-10 + PAY-08 + SHP-08 + ORD-18 + NTF-07.

Feature spec chi tiết của M1 nằm tại [`m1-catalog-inventory/spec.md`](./m1-catalog-inventory/spec.md). Tài liệu đó sở hữu phạm vi, vertical tickets và gate hoàn tất M1; file này tiếp tục sở hữu thứ tự tổng thể giữa 8 module.

## 13. Điểm cần theo dõi, chưa đổi roadmap

- `ordering` là module duy nhất trải qua M2–M6; spec từng mốc phải giữ chung state machine và không tạo service chuyển trạng thái song song.
- `notifications` phải triển khai tăng dần theo sự kiện nguồn, không để toàn bộ tới M6.
- `inventory` có model ở M1 nhưng contract commit/reservation/restock xuất hiện theo M2–M5; ticket sau phải mở rộng contract thay vì import nội bộ.
- US-1004 có thể bị loại nếu GHN sandbox xác nhận hỗ trợ trực tiếp địa chỉ 2 cấp; chưa tự quyết trước M7.
- Các slice P2 ID-07, ID-09, ORD-15 và ORD-19 có thể hoãn, nhưng phần dữ liệu nền bắt buộc cho P1/CMP vẫn phải được thiết kế không chặn nâng cấp.
- Tài liệu này chưa sửa `.scratch/mvp-roadmap/map.md`. Chỉ cập nhật roadmap sau khi plan được review và chấp thuận.
