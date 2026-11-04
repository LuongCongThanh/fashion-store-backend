# 04. Quy tắc nghiệp vụ

> Trạng thái: **Đã chốt cho MVP** ([quy ước](../../README.md#trạng-thái-tài-liệu)). Mỗi quy tắc có mã `BR-xxx` để user story và test tham chiếu tới.
> Thuật ngữ dùng theo [GLOSSARY.md](../../GLOSSARY.md).

## 1. Sản phẩm và Danh mục

| Mã | Quy tắc |
|---|---|
| BR-CAT-01 | Mỗi Sản phẩm có ít nhất một Biến thể. Người mua luôn mua Biến thể, không mua Sản phẩm. |
| BR-CAT-02 | Biến thể là tổ hợp duy nhất của **size × màu** trong một Sản phẩm. Không có hai Biến thể trùng size và màu. Mọi Biến thể có đủ size và màu; Sản phẩm không có size dùng size `FREESIZE`. |
| BR-CAT-03 | Mỗi Biến thể có **mã SKU duy nhất toàn hệ thống**, viết bằng chữ in hoa tiếng Anh, số và dấu gạch ngang, ví dụ `TSHIRT-BASIC-WHT-M`. SKU không thay đổi sau khi đã có đơn. |
| BR-CAT-04 | Giá bán đặt ở cấp **Biến thể**. Giá là số nguyên VND, lớn hơn 0. |
| BR-CAT-05 | Ảnh gắn theo **màu** của Sản phẩm: mọi size cùng màu dùng chung bộ ảnh. |
| BR-CAT-06 | Cân nặng (gram) nhập ở cấp **Sản phẩm** và bắt buộc phải có để tính phí ship. |
| BR-CAT-07 | Sản phẩm có trạng thái `draft` (nháp), `active` (đang bán), `archived` (ngừng bán). Chỉ Sản phẩm `active` hiển thị trên storefront. |
| BR-CAT-08 | Sản phẩm `active` mà mọi Biến thể đều hết hàng vẫn hiển thị, kèm nhãn "Hết hàng", và không thêm vào Giỏ hàng được. |
| BR-CAT-09 | Không xoá cứng Sản phẩm hoặc Biến thể đã có trong đơn; chỉ chuyển sang `archived`. |
| BR-CAT-10 | Tên, mô tả Sản phẩm và tên Danh mục chỉ có **tiếng Việt**. |
| BR-CAT-11 | Size và màu của Biến thể được chọn từ **danh sách size** và **bảng màu** dùng chung do Admin quản lý. Size có thứ tự hiển thị; màu có mã, tên và mã hex. Size hoặc màu đã có Biến thể dùng chỉ được ẩn, không được xoá. Bộ lọc trên storefront lọc theo mã size và mã màu. |
| BR-CAT-12 | Sắp xếp **bán chạy** theo tổng số lượng trong Dòng đơn hàng của các đơn đã vào Chờ xác nhận, chưa bị huỷ và không Hoàn hàng, trong 30 ngày gần nhất, tính theo Sản phẩm. Số liệu cập nhật mỗi đêm, không cần thời gian thực. |
| BR-CAT-13 | MVP tìm kiếm theo **chuỗi con liên tiếp trong tên Sản phẩm**, không phân biệt hoa thường và dấu tiếng Việt. Bỏ khoảng trắng đầu/cuối từ khoá; từ khoá rỗng được coi là không lọc tìm kiếm. Không sửa lỗi gõ, đảo thứ tự từ hoặc tìm gần đúng. Tìm kiếm chỉ lọc kết quả, vẫn kết hợp với các bộ lọc và cách sắp xếp của US-102. |

## 2. Giá và khuyến mãi

### 2.1. Giá khuyến mãi (Sale Price)

| Mã | Quy tắc |
|---|---|
| BR-PRC-01 | Giá khuyến mãi gắn với một Biến thể, có thời gian bắt đầu và kết thúc. Giá khuyến mãi phải **nhỏ hơn** Giá bán. |
| BR-PRC-02 | Tại một thời điểm, mỗi Biến thể có tối đa **một** Giá khuyến mãi hiệu lực. |
| BR-PRC-03 | Giá áp dụng = Giá khuyến mãi nếu đang hiệu lực, ngược lại = Giá bán. |
| BR-PRC-04 | Mức giảm của Giá khuyến mãi = `(Giá bán − Giá khuyến mãi) / Giá bán`, tính chính xác (không làm tròn) từ Giá bán và đơn giá đã chụp trên Dòng đơn hàng. Mức này quyết định quyền Đổi trả (BR-RET-03). |
| BR-PRC-05 | Không đổi được Giá bán của Biến thể xuống bằng hoặc thấp hơn một Giá khuyến mãi đang hoặc sắp hiệu lực của Biến thể đó. Admin phải sửa Giá khuyến mãi trước. |

### 2.2. Mã giảm giá (Voucher)

| Mã | Quy tắc |
|---|---|
| BR-VCH-01 | Mỗi Đơn hàng dùng **tối đa một** Voucher. |
| BR-VCH-02 | Voucher **cộng dồn** với Giá khuyến mãi: Voucher tính trên Tạm tính, vốn đã dùng Giá áp dụng. |
| BR-VCH-03 | Voucher có một trong hai kiểu: giảm **theo %** (có thể kèm mức giảm tối đa) hoặc giảm **số tiền cố định**. |
| BR-VCH-04 | Điều kiện của Voucher gồm: thời gian hiệu lực, giá trị đơn tối thiểu, tổng số lượt dùng, số lượt dùng tối đa cho mỗi Người mua (BR-VCH-07). |
| BR-VCH-05 | Voucher chỉ giảm trên **Tạm tính**, không giảm phí ship. |
| BR-VCH-06 | Số tiền giảm không vượt quá Tạm tính; Tạm tính sau giảm không âm. |
| BR-VCH-07 | Số lượt dùng của một Người mua được đếm theo **Tài khoản hoặc số điện thoại**: mọi lượt dùng trùng Tài khoản, hoặc trùng số điện thoại liên hệ của đơn đang đặt, đều được tính. Ví dụ: Khách hàng đã dùng hết lượt thì không dùng tiếp được khi đặt như Khách vãng lai bằng cùng số điện thoại. |
| BR-VCH-08 | Lượt dùng Voucher được tính khi đơn được tạo. Nếu đơn bị huỷ trước khi Đang giao, lượt dùng được **trả lại**. |
| BR-VCH-09 | Mã Voucher không phân biệt hoa thường, lưu dạng chữ in hoa, ví dụ `SALE10`. |
| BR-VCH-10 | Tiền giảm theo % được **làm tròn xuống đến đồng** trước khi áp mức giảm tối đa và giới hạn bằng Tạm tính: `discount = min((subtotal * percent) // 100, max_discount nếu có, subtotal)`. Voucher số tiền cố định dùng `min(value, subtotal)`. Tính bằng số nguyên, không dùng số thực dấu phẩy động. |

## 3. Tồn kho

| Mã | Quy tắc |
|---|---|
| BR-INV-01 | Tồn kho được quản lý theo **Biến thể × Kho**. MVP có một Kho. |
| BR-INV-02 | Số lượng bán được = Tồn kho − tổng Giữ hàng còn hiệu lực. Không bao giờ âm. |
| BR-INV-03 | Giỏ hàng **không** Giữ hàng. Thêm vào Giỏ hàng không làm giảm Số lượng bán được. |
| BR-INV-04 | Đơn **COD**: trừ Tồn kho ngay khi đặt đơn thành công; số đã trừ thành Hàng chờ xuất của đơn (BR-INV-10). |
| BR-INV-05 | Đơn **thanh toán online**: tạo Giữ hàng có thời hạn **15 phút**. Mọi link thanh toán của đơn (kể cả khi thử lại) hết hạn ở **phút thứ 10** kể từ khi đặt đơn, sớm hơn Giữ hàng 5 phút để kịp nhận thông báo thanh toán đến muộn. Từ phút thứ 7 không tạo link thanh toán mới, để mỗi lần thử còn ít nhất 3 phút cho Người mua trả tiền (chuyển sang app ngân hàng hoặc ví, nhập OTP). Thanh toán thành công thì chuyển Giữ hàng thành trừ Tồn kho và Hàng chờ xuất. Hết hạn Giữ hàng mà chưa thanh toán thì huỷ đơn và giải phóng Giữ hàng. Hai thời hạn này cố định, không cấu hình. |
| BR-INV-06 | Khi đặt đơn, nếu bất kỳ Dòng đơn hàng nào không đủ Số lượng bán được thì **không tạo đơn** và báo cho Người mua Biến thể nào thiếu, còn bao nhiêu. |
| BR-INV-07 | Huỷ đơn trước khi Đang giao thì Hàng chờ xuất của đơn được trả lại Tồn kho ngay; đơn online chưa thanh toán thì giải phóng Giữ hàng. |
| BR-INV-08 | Đơn Hoàn hàng: hàng được cộng lại Tồn kho khi Staff **xác nhận đã nhận hàng về Kho**. Hàng Đổi trả: chỉ phần được **Chấp nhận** và được Staff chọn nhập lại mới cộng lại Tồn kho; hàng lỗi không nhập lại (BR-RET-08). |
| BR-INV-09 | Mọi thay đổi Tồn kho đều được ghi lịch sử (loại thay đổi, số lượng, đơn liên quan, người thực hiện). |
| BR-INV-10 | Hàng đã bán nhưng chưa Bàn giao là **Hàng chờ xuất**, theo dõi theo Mã đơn. Hàng chờ xuất của đơn được xoá khi Vận đơn tạo xong (đơn sang Đang giao). Hàng trên kệ = Tồn kho + Hàng chờ xuất ([ADR 0010](../adr/0010-stock-decremented-at-order-awaiting-dispatch.md)). |
| BR-INV-11 | Điều chỉnh giảm Tồn kho, kể cả qua Kiểm kê, không được vượt quá Số lượng bán được; vượt thì báo lỗi kèm số tối đa giảm được. Nếu thiếu hàng cho đơn đã đặt, Staff huỷ đơn theo BR-ORD-05. |
| BR-INV-12 | **Kiểm kê**: Staff nhập số đếm thực tế của một Biến thể; hệ thống điều chỉnh Tồn kho theo chênh lệch = số đếm − (Tồn kho + Hàng chờ xuất), tính tại lúc Staff xác nhận, với lý do "kiểm kê". |

## 4. Giỏ hàng

| Mã | Quy tắc |
|---|---|
| BR-CRT-01 | Giỏ hàng lưu ở server, cho cả Khách vãng lai và Khách hàng. |
| BR-CRT-02 | Giỏ của Khách vãng lai hết hạn sau **30 ngày** không hoạt động. |
| BR-CRT-03 | Khi Khách vãng lai đăng nhập, Giỏ hàng vãng lai được **gộp** vào Giỏ hàng của Tài khoản: Biến thể trùng thì cộng dồn số lượng, nhưng không vượt quá Số lượng bán được. |
| BR-CRT-04 | Giá trong Giỏ hàng luôn là Giá áp dụng **hiện tại**. Nếu giá thay đổi so với lúc thêm vào Giỏ hàng, hệ thống thông báo cho Người mua. |
| BR-CRT-05 | Số lượng tối đa của một Biến thể trong một giỏ là **10**. |

## 5. Đặt hàng và tính tiền

| Mã | Quy tắc |
|---|---|
| BR-ORD-01 | Tổng tiền đơn = Tạm tính − giảm giá Voucher + phí ship. |
| BR-ORD-02 | Dòng đơn hàng lưu **bản chụp** tên Sản phẩm, SKU, size, màu, đơn giá, mức giảm và phần Voucher phân bổ cho dòng tại thời điểm đặt. Voucher được phân bổ về từng dòng theo tỷ lệ giá trị dòng, phần lẻ dồn vào dòng cuối. Sửa Sản phẩm sau đó không làm đổi đơn cũ. |
| BR-ORD-03 | Mã đơn có dạng `FS<YYMM>-` cộng 6 ký tự chữ và số **ngẫu nhiên**, ví dụ `FS2610-7K3QZD`. Mã không đoán được và không cho biết thứ tự hay số lượng đơn. |
| BR-ORD-04 | Địa chỉ giao hàng theo cấu trúc **2 cấp**: tỉnh/thành phố và phường/xã (theo sắp xếp đơn vị hành chính từ 07/2025), kèm địa chỉ chi tiết. |
| BR-ORD-05 | Chỉ huỷ **cả đơn**, không huỷ từng Dòng đơn hàng. Nếu một phần hàng không giao được, Staff liên hệ Người mua, huỷ đơn và tạo đơn mới. |
| BR-ORD-06 | Quy tắc huỷ và chuyển trạng thái xem [05-order-lifecycle.md](./05-order-lifecycle.md). |
| BR-ORD-07 | Backend tính lại tổng khi đặt đơn, không tin giá Frontend. Đơn chỉ được tạo khi các dòng, giá và điều kiện bán lúc đặt khớp với Tính thử mà Người mua đã xác nhận. Khác ở bất kỳ điểm nào thì không tạo đơn và Người mua phải xác nhận Tính thử mới, kể cả khi tổng tiền tình cờ không đổi. Tính thử có hạn, không Giữ hàng và không cam kết giá; hết hạn phải Tính thử lại. Cách kiểm tra kỹ thuật: [`ordering` mục 5.1](../architecture/modules/ordering.md#51-luồng-checkout). |
| BR-ORD-08 | Đơn của Khách vãng lai được gắn vào Tài khoản Khách hàng có email trùng (không phân biệt hoa thường): ngay khi email đó được xác thực, kể cả qua đăng nhập Google, với các đơn đã đặt trước đó; hoặc ngay lúc đặt đơn nếu email đó đã thuộc một Tài khoản đã xác thực. Không gắn theo số điện thoại. |
| BR-ORD-09 | MVP chỉ nhận Đơn hàng có **Tổng tiền đơn > 0**, với cả COD và online. Tính thử và checkout đều từ chối nếu tổng tính được bằng 0 hoặc âm; không tự giảm giá trị Voucher, tăng Phí ship hoặc đổi Phương thức thanh toán để tạo đơn. Checkout kiểm tra lại trong transaction trước khi commit; bị từ chối thì không tạo Order, Payment, Giữ hàng, Hàng chờ xuất hay lượt dùng Voucher. |

### Phân bổ Voucher về Dòng đơn hàng (BR-ORD-02)

- Sắp các dòng theo `variant_id` tăng dần để có thứ tự ổn định, không phụ thuộc thứ tự request hay thứ tự truy vấn DB. Giá trị dòng `L_i = unit_price_i * quantity_i`, tổng `S = SUM(L_i)`, số giảm của đơn `D` tính theo BR-VCH-10.
- Phân bổ ban đầu `d_i = (D * L_i) // S`. Phần dư `R = D - SUM(d_i)` được cộng vào dòng cuối. Nếu vượt giá trị dòng đó, chỉ cộng tới `L_i`, rồi chuyển phần còn lại lần lượt về các dòng trước theo thứ tự ngược. Nhờ vậy luôn có `0 <= d_i <= L_i` và `SUM(d_i) = D`, kể cả khi các dòng có giá trị rất nhỏ.
- Lưu `d_i` thành `voucher_discount` lúc tạo đơn; không phân bổ lại theo giá hoặc Voucher hiện tại khi Đổi trả.
- Ví dụ: Tạm tính 1.001đ, Voucher 10% → giảm 100đ. Hai dòng lần lượt 500đ và 501đ → phân bổ 49đ và 51đ. Trường hợp ba dòng mỗi dòng 1đ, giảm 2đ → phân bổ 0đ, 1đ, 1đ; không dồn 2đ vào một dòng chỉ có giá trị 1đ.

## 6. Vận chuyển

| Mã | Quy tắc |
|---|---|
| BR-SHP-01 | Phí ship được lấy **theo thời gian thực** từ GHN, dựa trên địa chỉ giao và tổng cân nặng (cân nặng Sản phẩm × số lượng). Kích thước gói dùng giá trị mặc định cấu hình được. |
| BR-SHP-02 | Nếu API GHN lỗi hoặc quá thời gian chờ, dùng **Phí ship dự phòng** (mặc định 35.000đ) để Người mua vẫn checkout được. Đơn được gắn Cờ cần xử lý "phí ship dự phòng" để Staff theo dõi. |
| BR-SHP-03 | Đơn có Tạm tính **sau khi trừ Voucher** đạt Ngưỡng miễn phí ship (mặc định 500.000đ) được **miễn phí ship**; cửa hàng vẫn trả Cước vận chuyển cho GHN. |
| BR-SHP-04 | Phí ship dự phòng và ngưỡng miễn phí ship do Admin cấu hình. |
| BR-SHP-05 | Khi Staff bàn giao đơn cho GHN, hệ thống tự tạo Vận đơn ở GHN. Đơn chỉ chuyển sang Đang giao khi GHN tạo Vận đơn thành công; tạo thất bại thì đơn vẫn Đang đóng gói và được gắn Cờ cần xử lý. Staff bàn giao lại thì hệ thống dùng lại Vận đơn đó. |
| BR-SHP-06 | Trạng thái giao hàng được cập nhật từ GHN qua webhook và job Đối soát định kỳ. |
| BR-SHP-07 | Với đơn COD, số tiền thu hộ = tổng tiền đơn. |
| BR-SHP-08 | Khi Vận đơn gặp sự cố (GHN báo mất hàng, hư hàng, sự cố, hoặc tự huỷ Vận đơn mà hệ thống không yêu cầu), đơn được gắn Cờ cần xử lý. Staff được huỷ đơn đang giao chỉ trong trường hợp này, bắt buộc nhập lý do ([05-order-lifecycle.md](./05-order-lifecycle.md) mục 4.7). |

## 7. Thanh toán

| Mã | Quy tắc |
|---|---|
| BR-PAY-01 | Phương thức thanh toán: **COD** hoặc **online**, chốt khi đặt đơn. Thanh toán online đi qua Cổng thanh toán **VNPay** hoặc **MoMo**; Người mua chọn Cổng ở mỗi lần trả tiền, và khi đơn còn chờ thanh toán thì được thử lại bằng Cổng khác. |
| BR-PAY-02 | Trạng thái Thanh toán chỉ được xác nhận qua **thông báo server-to-server (IPN)** hoặc **job Đối soát**, không bao giờ dựa vào trang Người mua được chuyển về (Return URL). |
| BR-PAY-03 | Một thông báo thanh toán nhận lặp lại nhiều lần chỉ được xử lý **một lần**. |
| BR-PAY-04 | Số tiền **đã được provider xác nhận thu thành công (captured)** phải khớp đúng Tổng tiền đơn. Không khớp thì không xác nhận đơn, gắn Cờ cần xử lý cho Staff và **tự tạo yêu cầu Hoàn tiền** đúng số tiền đã nhận. Đơn vẫn chờ thanh toán; Người mua trả lại đúng số tiền được nếu link còn hạn. Số tiền yêu cầu trong thông báo failed/pending/authorized không phải bằng chứng đã thu tiền và không tự tạo nghĩa vụ Hoàn tiền. |
| BR-PAY-05 | Nếu nhận được tiền cho một Đơn hàng **không còn chờ thanh toán**, hệ thống **tự tạo yêu cầu Hoàn tiền** cho khoản tiền đó và gắn Cờ cần xử lý cho Staff; Đơn hàng giữ nguyên trạng thái. Hai trường hợp thường gặp: đơn đã bị huỷ (Người mua trả sát lúc hết hạn), hoặc đơn đã được thanh toán bởi một lần trả tiền khác (Người mua trả ở hai tab). |
| BR-PAY-06 | Giá trị đơn COD tối đa (hạn mức COD) mặc định **5.000.000đ**, do Admin cấu hình; vượt mức thì Người mua phải thanh toán online. |

## 8. Hoàn tiền

| Mã | Quy tắc |
|---|---|
| BR-REF-01 | Mỗi Hoàn tiền gắn với đúng Thanh toán đã nhận tiền. Hoàn tiền của đơn online luôn trả về **đúng Cổng thanh toán** đã nhận khoản tiền đó. |
| BR-REF-02 | Phát sinh khi: huỷ đơn đã thanh toán online, Hoàn hàng đơn đã thanh toán online, Đổi trả được chấp nhận, hoặc trường hợp BR-PAY-04, BR-PAY-05. |
| BR-REF-03 | MVP: Staff thực hiện hoàn tiền **thủ công** trên trang quản trị của VNPay hoặc MoMo, rồi ghi nhận "Đã hoàn tiền" trong back-office kèm mã giao dịch hoàn. |
| BR-REF-04 | Đơn COD bị huỷ trước khi giao: không phát sinh Hoàn tiền. Đơn COD Đổi trả: hoàn bằng chuyển khoản ngân hàng, Staff ghi nhận thủ công và gắn với khoản thu COD của đơn. Việc đối chiếu tiền COD mà GHN chuyển về cho cửa hàng nằm ngoài phạm vi MVP; kế toán làm tay theo bảng kê của GHN. |
| BR-REF-05 | Số tiền Hoàn tiền: huỷ hoặc Hoàn hàng đơn đã thanh toán online thì hoàn **toàn bộ** Tổng tiền đơn, kể cả Phí ship; trường hợp BR-PAY-04, BR-PAY-05 thì hoàn đúng số tiền đã nhận; Đổi trả thì theo BR-RET-07. |
| BR-REF-06 | Một thao tác nghiệp vụ chỉ tạo một yêu cầu Hoàn tiền cho mỗi Thanh toán, kể cả khi xử lý lại. Tổng các khoản Hoàn tiền đang yêu cầu và đã hoàn không vượt số tiền thực nhận của Thanh toán đó. |

## 9. Đổi trả

| Mã | Quy tắc |
|---|---|
| BR-RET-01 | Người mua được yêu cầu Đổi trả trong **7 ngày** (đủ 7 × 24 giờ) kể từ lúc đơn **Đã giao**. Hết hạn này thì hết quyền Đổi trả; đơn chuyển sang **Hoàn tất** khi không còn Đổi trả nào đang mở. |
| BR-RET-02 | Điều kiện: hàng **còn tag, chưa qua sử dụng**. |
| BR-RET-03 | Hàng có Giá khuyến mãi giảm **trên 50%** (BR-PRC-04) **không** được Đổi trả. |
| BR-RET-04 | MVP: Người mua gửi yêu cầu qua hotline hoặc Zalo; Staff ghi nhận yêu cầu trong back-office. |
| BR-RET-05 | "Đổi" hàng (đổi size, đổi màu) được xử lý như **trả hàng + tạo đơn mới**. |
| BR-RET-06 | Phí ship gửi trả: cửa hàng chịu nếu hàng lỗi hoặc giao sai, Người mua chịu trong các trường hợp còn lại. |
| BR-RET-07 | Số tiền Hoàn tiền khi Đổi trả = phần Người mua **đã thực trả** cho số lượng **được chấp nhận** (BR-RET-08), tức đơn giá trừ phần Voucher đã phân bổ cho dòng (BR-ORD-02). Không truy thu phí ship khi phần hàng còn giữ lại tụt dưới ngưỡng miễn phí ship. Ví dụ: 3 áo × 200.000đ, Voucher giảm 60.000đ, trả 1 áo thì hoàn 180.000đ. |
| BR-RET-08 | Staff Chấp nhận Đổi trả **theo từng dòng**: nhập số lượng được chấp nhận (từ 0 tới số lượng gửi trả) và chọn nhập lại Tồn kho hay không (hàng lỗi thì không nhập lại). Yêu cầu được Chấp nhận nếu có ít nhất một sản phẩm được chấp nhận, ngược lại bị Từ chối. |
| BR-RET-09 | Hàng không được chấp nhận được gửi lại cho Người mua, Người mua chịu phí ship. MVP: Staff xử lý việc gửi lại ngoài hệ thống và ghi chú vào yêu cầu Đổi trả. |

### Làm tròn Hoàn tiền khi Đổi trả nhiều lần (BR-RET-07)

- Với mỗi Dòng đơn hàng, gọi `N = unit_price * quantity - voucher_discount` là số tiền hàng thực trả, `q = quantity`. Số tiền hoàn lũy kế cho `k` sản phẩm được chấp nhận là `F(k) = (N * k) // q`, với `F(0) = 0`.
- Nếu đã chấp nhận `k` sản phẩm ở các yêu cầu trước, lần này chấp nhận thêm `n` thì số hoàn của dòng là `F(k + n) - F(k)`. Tính `k` từ các yêu cầu `accepted` hoặc `refunded`, kể cả khoản hoàn còn chờ Staff xử lý; không tính yêu cầu bị từ chối hoặc số lượng không được chấp nhận. Khoá Order khi tính và chấp nhận để hai yêu cầu không dùng cùng một mốc `k`.
- Tiền hoàn của yêu cầu là tổng số hoàn các dòng. Phần lẻ được bù theo số lượng lũy kế; khi trả hết dòng, `F(q) = N`, nên tổng các lần hoàn bằng đúng số tiền hàng thực trả. Không tính lại Voucher và không hoàn Phí ship trong Đổi trả.
- Ví dụ: dòng 3 sản phẩm × 100đ, được phân bổ Voucher 1đ → `N = 299đ`. Trả lần lượt từng sản phẩm thì hoàn 99đ, 100đ, 100đ; tổng 299đ. Một lần trả cả 3 cũng hoàn 299đ.
- Nếu có sản phẩm được chấp nhận nhưng tổng tiền hoàn của yêu cầu bằng 0 (do Voucher hoặc làm tròn), vẫn xử lý nhập lại Tồn kho theo lựa chọn của Staff và khép lại yêu cầu ở `refunded`, không tạo Hoàn tiền 0đ hay gọi Cổng thanh toán. `refunded` trong trường hợp này nghĩa là đã xử lý xong và không còn tiền phải hoàn. Không có sản phẩm nào được chấp nhận thì vẫn là `rejected` theo BR-RET-08.

## 10. Thông báo

| Mã | Quy tắc |
|---|---|
| BR-NTF-01 | Email được gửi khi: đặt đơn COD thành công ("Đặt đơn thành công"), thanh toán online thành công ("Thanh toán thành công"), đơn bị huỷ, đơn Đang giao, đơn Đã giao, Hoàn tiền được ghi nhận. Đơn online chưa thanh toán không nhận email nào, kể cả khi bị huỷ vì hết hạn hoặc do Người mua tự huỷ. Ngoại lệ: tiền về cho đơn không còn chờ thanh toán (BR-PAY-05) thì gửi email báo tiền sẽ được hoàn. |
| BR-NTF-02 | Email gửi theo **ngôn ngữ Khách hàng đã chọn** (vi/en). Khách vãng lai: theo ngôn ngữ giao diện lúc đặt đơn. Tên Sản phẩm trong email luôn là tiếng Việt. |
| BR-NTF-03 | Khách vãng lai không nhập email thì không nhận email; vẫn tra cứu đơn được. |

## 11. Doanh thu

| Mã | Quy tắc |
|---|---|
| BR-REV-01 | Doanh thu chỉ tính đơn **Hoàn tất** và ghi vào ngày Hoàn tất (giờ Việt Nam). Doanh thu của đơn = Tổng tiền đơn − các Hoàn tiền của Đổi trả. Hoàn tiền theo BR-PAY-04, BR-PAY-05 là trả lại tiền thừa nên không làm giảm Doanh thu. |
| BR-REV-02 | Báo cáo Doanh thu tách hai phần: tiền hàng (Tạm tính − giảm giá Voucher − Hoàn tiền của Đổi trả) và Phí ship đã thu. |
