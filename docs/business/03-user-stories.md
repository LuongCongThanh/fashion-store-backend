# 03. User stories

> Trạng thái: **Đã chốt cho MVP** ([quy ước](../../README.md#trạng-thái-tài-liệu)). Chỉ gồm phạm vi **MVP**.
> Mỗi story có tiêu chí nghiệm thu (AC) viết theo dạng *Cho trước / Khi / Thì*, và tham chiếu tới quy tắc `BR-xxx` trong [04-business-rules.md](./04-business-rules.md).
> Độ ưu tiên: **P1** bắt buộc cho MVP, **P2** nên có trong MVP.

## Danh sách epic

| Epic | Tên | Vai trò chính |
|---|---|---|
| E1 | Duyệt và tìm kiếm Sản phẩm | Guest, Customer |
| E2 | Giỏ hàng | Guest, Customer |
| E3 | Checkout và thanh toán | Guest, Customer |
| E4 | Theo dõi và huỷ đơn | Guest, Customer |
| E5 | Tài khoản Khách hàng | Customer |
| E6 | Xử lý Đơn hàng | Staff |
| E7 | Tồn kho | Staff |
| E8 | Quản lý Sản phẩm và Danh mục | Admin |
| E9 | Khuyến mãi | Admin |
| E10 | Quản trị hệ thống | Admin |
| E11 | Dữ liệu cá nhân | Guest, Customer, Staff |

---

## E1. Duyệt và tìm kiếm Sản phẩm

### US-101 · Xem danh sách Sản phẩm theo danh mục · P1
**Là** Người mua, **tôi muốn** xem Sản phẩm theo danh mục **để** tìm món mình cần.

- AC1: Cho trước danh mục "Áo thun" có 30 Sản phẩm `active`, khi Người mua mở danh mục, thì thấy danh sách có phân trang, mỗi Sản phẩm hiện ảnh, tên, Giá áp dụng thấp nhất trong các Biến thể (BR-PRC-03) và Giá bán nếu đang có Giá khuyến mãi.
- AC2: Sản phẩm `draft` hoặc `archived` không xuất hiện (BR-CAT-07).
- AC3: Sản phẩm hết hàng mọi Biến thể vẫn hiện, kèm nhãn "Hết hàng" (BR-CAT-08).

### US-102 · Lọc và sắp xếp · P1
**Là** Người mua, **tôi muốn** lọc theo size, màu, khoảng giá và sắp xếp **để** thu hẹp kết quả.

- AC1: Khi chọn size M và màu Trắng, thì chỉ hiện Sản phẩm có **ít nhất một Biến thể** size M màu Trắng còn hàng. Size và màu lọc theo mã trong danh sách size và bảng màu dùng chung (BR-CAT-11).
- AC2: Sắp xếp được theo: mới nhất, giá tăng dần, giá giảm dần, bán chạy (BR-CAT-12).
- AC3: Lọc theo giá dùng Giá áp dụng (đã tính Giá khuyến mãi).
- AC4: Bộ lọc size chỉ hiện các size có trong kết quả hiện tại, theo thứ tự hiển thị của danh sách size.

### US-103 · Tìm kiếm theo tên · P1
**Là** Người mua, **tôi muốn** gõ tên Sản phẩm **để** tìm nhanh.

- AC1: Gõ "ao thun", "áo thun" hoặc "ÁO THUN" cho cùng kết quả; bỏ khoảng trắng đầu/cuối từ khoá (BR-CAT-13).
- AC2: Gõ một phần tên, ví dụ "basic", vẫn ra Sản phẩm "Áo thun Basic cổ tròn".
- AC3: Không có kết quả thì hiển thị thông báo và gợi ý danh mục.
- AC4: Khớp chuỗi con liên tiếp: "ao thun" khớp "Áo thun Basic cổ tròn"; "ao thnu" hoặc "thun ao" không khớp tên này. MVP không tự sửa lỗi gõ hoặc tìm gần đúng (BR-CAT-13).
- AC5: Từ khoá rỗng hoặc chỉ có khoảng trắng cho kết quả như không tìm kiếm. Kết quả vẫn áp dụng trạng thái hiển thị, các bộ lọc và cách sắp xếp của US-101, US-102.

### US-104 · Xem chi tiết Sản phẩm · P1
**Là** Người mua, **tôi muốn** xem chi tiết và chọn size, màu **để** quyết định mua.

- AC1: Chọn màu thì đổi bộ ảnh theo màu (BR-CAT-05).
- AC2: Chọn size × màu thì hiện đúng giá, SKU và trạng thái còn hàng của Biến thể đó.
- AC3: Tổ hợp size × màu không tồn tại hoặc hết hàng thì không chọn được để thêm vào giỏ.

---

## E2. Giỏ hàng

### US-201 · Thêm vào giỏ · P1
- AC1: Cho trước Biến thể còn 3, khi Người mua thêm 2, thì giỏ có 2. Thêm tiếp 2 thì báo chỉ còn 3 và giỏ giữ ở mức 3.
- AC2: Không vượt quá 10 cho mỗi Biến thể (BR-CRT-05).
- AC3: Thêm vào giỏ không làm giảm Số lượng bán được (BR-INV-03).

### US-202 · Xem và sửa giỏ · P1
- AC1: Giỏ hiện giá **hiện tại** của từng Biến thể. Nếu giá đã đổi so với lúc thêm, hiện thông báo (BR-CRT-04).
- AC2: Biến thể đã hết hàng hoặc bị `archived` được đánh dấu và không cho checkout cho tới khi Người mua xoá khỏi giỏ.

### US-203 · Giữ giỏ cho Khách vãng lai · P1
- AC1: Khách vãng lai thêm hàng, đóng trình duyệt, quay lại sau 3 ngày vẫn thấy giỏ.
- AC2: Sau 30 ngày không hoạt động thì giỏ bị xoá (BR-CRT-02).

### US-204 · Gộp giỏ khi đăng nhập · P1
- AC1: Cho trước giỏ vãng lai có Biến thể A × 2, giỏ tài khoản có A × 1 và B × 1, khi đăng nhập, thì giỏ tài khoản có A × 3 và B × 1 (BR-CRT-03).
- AC2: Nếu A chỉ còn 2 thì A được giữ ở mức 2 và Người mua được thông báo.

---

## E3. Checkout và thanh toán

### US-301 · Checkout không cần tài khoản · P1
**Là** Khách vãng lai, **tôi muốn** đặt hàng mà không phải đăng ký **để** mua nhanh.

- AC1: Bắt buộc nhập họ tên, số điện thoại, tỉnh/thành, phường/xã, địa chỉ chi tiết; email tuỳ chọn.
- AC2: Số điện thoại phải là số di động Việt Nam hợp lệ.
- AC3: Bắt buộc tick đồng ý xử lý dữ liệu cá nhân, checkbox không tick sẵn (CMP-01).
- AC4: Ngay sau khi đặt đơn, Khách vãng lai xem, thanh toán và huỷ được đơn vừa đặt trong 30 phút mà không phải tra cứu lại (xem [02-actors-permissions.md](./02-actors-permissions.md) mục 2).

### US-302 · Checkout với tài khoản · P1
- AC1: Khách hàng chọn được địa chỉ từ sổ địa chỉ hoặc nhập địa chỉ mới (có tuỳ chọn lưu vào sổ).
- AC2: Thông tin liên hệ được điền sẵn từ hồ sơ.

### US-303 · Xem phí ship · P1
- AC1: Khi Người mua chọn xong phường/xã, hệ thống hiện Phí ship lấy từ GHN (BR-SHP-01).
- AC2: Cho trước API GHN lỗi, thì hiện Phí ship dự phòng (mặc định 35.000đ) và Người mua vẫn đặt hàng được (BR-SHP-02).
- AC3: Tạm tính sau khi trừ Voucher đạt Ngưỡng miễn phí ship (mặc định 500.000đ) thì Phí ship = 0đ (BR-SHP-03).

### US-304 · Áp Voucher · P1
- AC1: Nhập `sale10` hay `SALE10` đều nhận (BR-VCH-09).
- AC2: Voucher hết hạn, hết lượt, chưa đủ giá trị đơn tối thiểu, hoặc Người mua đã dùng hết lượt của mình (đếm theo Tài khoản hoặc số điện thoại, BR-VCH-07) thì báo lý do cụ thể.
- AC3: Đã có một Voucher, nhập Voucher thứ hai thì Voucher mới **thay thế** Voucher cũ (BR-VCH-01).
- AC4: Voucher không giảm phí ship (BR-VCH-05).

### US-305 · Đặt đơn COD · P1
- AC1: Cho trước giỏ hợp lệ và tổng tiền ≤ hạn mức COD (mặc định 5.000.000đ), khi chọn COD và đặt hàng, thì đơn ở trạng thái Chờ xác nhận, Tồn kho bị trừ ngay (BR-INV-04), Người mua thấy Mã đơn.
- AC2: Tổng tiền vượt hạn mức COD thì không cho chọn COD (BR-PAY-06).
- AC3: Có email thì nhận email "Đặt đơn thành công".

### US-306 · Thanh toán VNPay / MoMo · P1
- AC1: Khi chọn thanh toán online và đặt hàng, đơn ở Chờ thanh toán, hàng được Giữ 15 phút (BR-INV-05). Người mua chọn Cổng thanh toán VNPay hoặc MoMo rồi được chuyển sang trang của Cổng đó.
- AC2: Thanh toán thành công thì đơn chuyển sang Chờ xác nhận **chỉ khi** hệ thống nhận IPN hoặc Đối soát thành công, không dựa vào việc Người mua quay lại trang (BR-PAY-02).
- AC3: Người mua quay lại trang trước khi IPN tới thì thấy trạng thái "Đang xác nhận thanh toán" và trang tự cập nhật.
- AC4: Quá 15 phút chưa thanh toán thì đơn bị huỷ và hàng được giải phóng (T4).
- AC5: Thanh toán thất bại thì Người mua được thử lại, bằng cùng Cổng hoặc Cổng khác, nếu chưa tới phút thứ 7 kể từ khi đặt đơn (BR-PAY-01, BR-INV-05).
- AC6: Đơn online chưa thanh toán không nhận email "Đặt đơn thành công"; thanh toán thành công thì nhận email "Thanh toán thành công" (BR-NTF-01).

### US-307 · Hết hàng khi đặt đơn · P1
- AC1: Cho trước hai Người mua cùng đặt Biến thể cuối cùng, thì chỉ một đơn thành công; người còn lại được báo hết hàng và không có đơn nào được tạo cho người đó (BR-INV-06).

### US-308 · Giá thay đổi khi đặt đơn · P1
- AC1: Cho trước Người mua đã xem tổng 450.000đ ở bước tính thử, khi Giá khuyến mãi vừa hết hạn và tổng tính lại là 520.000đ, thì đơn **không** được tạo và Người mua thấy bảng tính mới để xác nhận lại (BR-ORD-07).
- AC2: Tương tự khi Voucher vừa hết lượt hoặc phí ship thay đổi.

---

## E4. Theo dõi và huỷ đơn

### US-401 · Khách vãng lai tra cứu đơn · P1
- AC1: Nhập đúng mã đơn và số điện thoại thì xem được chi tiết đơn và trạng thái.
- AC2: Sai một trong hai thì báo "Không tìm thấy đơn", không tiết lộ thông tin nào khác.
- AC3: Giới hạn số lần tra cứu sai theo IP để chống dò mã đơn.

### US-402 · Khách hàng xem lịch sử đơn · P1
- AC1: Danh sách đơn sắp xếp mới nhất trước, có lọc theo trạng thái.
- AC2: Chi tiết đơn hiện Dòng đơn hàng theo **bản chụp** lúc đặt (BR-ORD-02), mã vận đơn GHN khi có.

### US-403 · Khách tự huỷ đơn · P1
- AC1: Đơn ở Chờ thanh toán, Chờ xác nhận hoặc Đã xác nhận thì có nút huỷ.
- AC2: Đơn từ Đang đóng gói trở đi thì không có nút huỷ, hiển thị hướng dẫn liên hệ hotline.
- AC3: Huỷ đơn đã thanh toán online thì Người mua được báo tiền sẽ được hoàn về đúng Cổng thanh toán đã nhận tiền (BR-REF-01).

---

## E5. Tài khoản Khách hàng

### US-501 · Đăng ký bằng email · P1
- AC1: Email chưa tồn tại, mật khẩu đạt yêu cầu tối thiểu, tick đồng ý dữ liệu cá nhân thì tạo tài khoản và gửi email xác thực.
- AC2: Mọi lần đăng ký hợp lệ về định dạng đều nhận cùng một phản hồi "Kiểm tra email để xác thực tài khoản", dù email đã tồn tại hay chưa, để không lộ email nào đã có Tài khoản. Email đã thuộc một Tài khoản Khách hàng chưa xác thực thì gửi lại email xác thực; đã thuộc Tài khoản đã xác thực, hoặc Tài khoản Staff/Admin, thì gửi cho chủ email thư báo "có người vừa thử đăng ký bằng email của bạn". Không tạo Tài khoản mới và không đổi mật khẩu của Tài khoản đã có.
- AC3: Sau khi email được xác thực (kể cả qua đăng nhập Google), các đơn đặt như Khách vãng lai bằng cùng email được gắn vào Tài khoản (BR-ORD-08).
- AC4: Khách hàng đã xác thực email mà đặt đơn như Khách vãng lai bằng cùng email thì đơn được gắn vào Tài khoản ngay lúc đặt (BR-ORD-08).

### US-502 · Đăng nhập bằng email hoặc Google · P1
- AC1: Đăng nhập Google lần đầu bằng email chưa có Tài khoản thì tạo Tài khoản mới.
- AC2: Đăng nhập Google bằng email đã có Tài khoản email + mật khẩu thì liên kết vào Tài khoản đó. Nếu Tài khoản đó chưa xác thực email, mật khẩu cũ bị xoá và mọi phiên đăng nhập cũ mất hiệu lực, để người đã đăng ký trước bằng email của người khác không giữ được quyền truy cập.
- AC3: Đăng nhập sai nhiều lần liên tiếp thì tạm khoá đăng nhập trong một khoảng thời gian.
- AC4: Email thuộc Tài khoản Staff hoặc Admin thì không đăng nhập storefront được, kể cả bằng Google; báo lỗi chung.

### US-503 · Quên mật khẩu · P1
- AC1: Nhập email thì luôn hiện "Nếu email tồn tại, chúng tôi đã gửi hướng dẫn".
- AC2: Link đặt lại mật khẩu dùng một lần và hết hạn sau 1 giờ.
- AC3: Đặt lại mật khẩu thành công thì mọi phiên đăng nhập cũ mất hiệu lực.

### US-504 · Sổ địa chỉ · P2
- AC1: Thêm, sửa, xoá địa chỉ; chọn một địa chỉ mặc định.

### US-505 · Chọn ngôn ngữ · P2
- AC1: Chọn vi hoặc en; email sau đó gửi theo ngôn ngữ đã chọn (BR-NTF-02).

### US-506 · Cập nhật hồ sơ · P2
- AC1: Khách hàng sửa được họ tên và số điện thoại (CMP-04).
- AC2: MVP không cho tự đổi email; muốn dùng email khác thì đăng ký Tài khoản mới.

---

## E6. Xử lý Đơn hàng (Staff)

### US-601 · Danh sách đơn cần xử lý · P1
- AC1: Lọc theo trạng thái, phương thức thanh toán, khoảng ngày; tìm theo mã đơn hoặc số điện thoại.
- AC2: Lọc được các đơn có Cờ cần xử lý, theo từng loại: phí ship dự phòng (BR-SHP-02), sai số tiền (BR-PAY-04), tiền về cho đơn không còn chờ thanh toán (BR-PAY-05), tạo Vận đơn thất bại (BR-SHP-05). Staff gỡ cờ khi xử lý xong.

### US-602 · Xác nhận và đóng gói · P1
- AC1: Staff chuyển Chờ xác nhận → Đã xác nhận → Đang đóng gói (T6, T8).
- AC2: Chọn nhiều đơn và xác nhận hàng loạt.

### US-603 · Bàn giao vận chuyển · P1
- AC1: Staff bấm bàn giao cho một hoặc nhiều đơn Đang đóng gói; hệ thống tạo Vận đơn ở GHN ở chế độ chạy nền. Khi GHN tạo xong, đơn chuyển sang Đang giao và lưu mã Vận đơn (T10).
- AC2: Tạo Vận đơn thất bại thì đơn giữ nguyên Đang đóng gói, được gắn Cờ cần xử lý và Staff thấy lý do lỗi.
- AC3: Trong lúc Vận đơn đang được tạo, Staff không huỷ được đơn (xem [05-order-lifecycle.md](./05-order-lifecycle.md) mục 4.5).
- AC4: Sau khi tạo Vận đơn thất bại, Staff xử lý nguyên nhân rồi bàn giao lại thì hệ thống dùng lại Vận đơn đó và gửi lại yêu cầu tạo sang GHN (BR-SHP-05).

### US-604 · Staff huỷ đơn · P1
- AC1: Huỷ được ở Chờ xác nhận, Đã xác nhận, Đang đóng gói (T7, T9); bắt buộc nhập lý do.
- AC2: Đơn đã thanh toán online thì tạo yêu cầu Hoàn tiền ở trạng thái chờ xử lý.

### US-605 · Ghi nhận Hoàn tiền thủ công · P1
- AC1: Staff nhập mã giao dịch hoàn và ngày hoàn, yêu cầu chuyển sang Đã hoàn tiền (BR-REF-03); Người mua nhận email.

### US-606 · Ghi nhận Đổi trả · P1
- AC1: Chỉ tạo được cho đơn Đã giao trong vòng 7 ngày (BR-RET-01).
- AC2: Dòng có Giá khuyến mãi giảm trên 50% không được chọn (BR-RET-03).
- AC3: Staff xác nhận đã nhận hàng thì yêu cầu chuyển sang Đã nhận hàng; Tồn kho **chưa** được cộng lại.
- AC4: Staff Chấp nhận theo từng dòng: nhập số lượng được chấp nhận (từ 0 tới số lượng gửi trả) và chọn nhập lại Tồn kho hay không (hàng lỗi). Chỉ phần được chấp nhận và chọn nhập lại mới cộng lại Tồn kho (BR-INV-08, BR-RET-08).
- AC5: Số tiền Hoàn tiền đề xuất = phần Người mua đã thực trả cho số lượng được chấp nhận (BR-RET-07). Không dòng nào được chấp nhận thì yêu cầu bị Từ chối; hàng được gửi lại Người mua (BR-RET-09).

### US-607 · Xử lý đơn Hoàn hàng · P1
- AC1: Đơn Hoàn hàng hiện trong danh sách chờ Staff xác nhận nhận hàng về Kho; xác nhận xong thì cộng lại Tồn kho.
- AC2: Danh sách cũng gồm đơn huỷ T14 đã xác nhận hàng chưa rời Kho và còn cần nhập lại; không gồm hàng mất/hư hoặc đơn đã trả Hàng chờ xuất khi huỷ trước khi Vận đơn tạo xong. Hai thao tác xác nhận đồng thời hoặc gọi lại chỉ cộng tồn một lần.

### US-608 · Xử lý tiền về cho đơn không còn chờ thanh toán · P1
- AC1: Có danh sách các yêu cầu Hoàn tiền do hệ thống tự tạo (BR-PAY-05) để Staff xử lý, gồm cả đơn đã huỷ và đơn được trả tiền hai lần.

### US-609 · Xử lý Vận đơn gặp sự cố · P1
- AC1: Đơn Đang giao mà GHN báo mất hàng, hư hàng, sự cố, hoặc tự huỷ Vận đơn thì được gắn Cờ cần xử lý và hiện trong bộ lọc cờ (BR-SHP-08).
- AC2: Staff huỷ được đơn đó (T14), bắt buộc nhập lý do; đơn đã thanh toán online được tạo Hoàn tiền toàn bộ (BR-REF-05).
- AC3: Khi huỷ T14, Staff phải xác nhận hàng chưa rời Kho hay mất/hư. Chỉ hàng chưa rời Kho được đánh dấu chờ nhập lại; huỷ chưa tự tăng tồn. Staff xác nhận nhập lại theo US-607; hàng mất/hư không được nhập lại.
- AC4: Đơn Đang giao không có cờ này thì Staff không huỷ được.

---

## E7. Tồn kho (Staff)

### US-701 · Nhập kho và điều chỉnh · P1
- AC1: Nhập số lượng nhập kho cho từng Biến thể.
- AC2: Điều chỉnh tăng/giảm bắt buộc chọn lý do; mọi thay đổi được ghi lịch sử (BR-INV-09).
- AC3: Điều chỉnh giảm vượt quá Số lượng bán được thì báo lỗi kèm số tối đa giảm được (BR-INV-11).

### US-702 · Xem tồn kho · P1
- AC1: Xem theo Biến thể: Tồn kho, số đang Giữ hàng, Hàng chờ xuất, Số lượng bán được.
- AC2: Lọc các Biến thể có Số lượng bán được dưới một ngưỡng do Staff tự nhập khi lọc (mặc định 5). Ngưỡng này không phải cấu hình hệ thống.

### US-703 · Kiểm kê · P1
**Là** Staff, **tôi muốn** nhập số hàng đếm được trên kệ **để** Tồn kho khớp với thực tế mà không phải tự trừ hàng của các đơn chưa Bàn giao.

- AC1: Staff nhập số đếm thực tế của từng Biến thể; hệ thống hiện Tồn kho, Hàng chờ xuất và chênh lệch = số đếm − (Tồn kho + Hàng chờ xuất) (BR-INV-12).
- AC2: Cho trước Tồn kho 7 và 3 áo thuộc đơn COD chưa Bàn giao, khi Staff đếm được 10, thì chênh lệch bằng 0 và không có điều chỉnh nào.
- AC3: Xác nhận thì Tồn kho được điều chỉnh theo chênh lệch, tính tại lúc xác nhận, với lý do "kiểm kê" và được ghi lịch sử (BR-INV-09). Chênh lệch giảm vượt quá Số lượng bán được thì báo lỗi như US-701 AC3.

---

## E8. Quản lý Sản phẩm và Danh mục (Admin)

### US-801 · Quản lý Danh mục · P1
- AC1: Tạo Danh mục nhiều cấp, sắp xếp thứ tự hiển thị.

### US-802 · Tạo Sản phẩm và Biến thể · P1
- AC1: Nhập tên, mô tả (tiếng Việt), danh mục, cân nặng (bắt buộc, BR-CAT-06).
- AC2: Chọn size và màu từ danh sách size và bảng màu dùng chung (BR-CAT-11) thì hệ thống sinh ma trận Biến thể; Admin nhập SKU và giá cho từng Biến thể. Sản phẩm không có size dùng size `FREESIZE` (BR-CAT-02).
- AC3: SKU trùng thì báo lỗi (BR-CAT-03).
- AC4: Upload ảnh theo màu (BR-CAT-05).

### US-803 · Đăng bán và ngừng bán · P1
- AC1: Chuyển Sản phẩm `draft` → `active` → `archived`. Sản phẩm đã có đơn không xoá được (BR-CAT-09).

### US-804 · Đặt Giá khuyến mãi · P1
- AC1: Chọn Biến thể (hoặc toàn bộ Biến thể của một Sản phẩm), nhập giá khuyến mãi và thời gian.
- AC2: Giá khuyến mãi ≥ giá bán thì báo lỗi; trùng thời gian với Giá khuyến mãi khác thì báo lỗi (BR-PRC-01, BR-PRC-02).
- AC3: Hạ Giá bán của Biến thể xuống bằng hoặc thấp hơn một Giá khuyến mãi đang hoặc sắp hiệu lực thì báo lỗi (BR-PRC-05).

### US-805 · Quản lý danh sách size và bảng màu · P1
- AC1: Thêm size (tên, thứ tự hiển thị) và màu (mã, tên tiếng Việt, mã hex) (BR-CAT-11).
- AC2: Size hoặc màu đã có Biến thể dùng thì chỉ ẩn được, không xoá được; size hoặc màu đã ẩn không chọn được cho Biến thể mới.

---

## E9. Khuyến mãi (Admin)

### US-901 · Tạo Voucher · P1
- AC1: Nhập mã, kiểu giảm (% kèm mức tối đa, hoặc số tiền cố định), giá trị đơn tối thiểu, tổng lượt, lượt mỗi Người mua, thời gian hiệu lực (BR-VCH-03, BR-VCH-04).
- AC2: Xem được số lượt đã dùng; vô hiệu hoá Voucher bất kỳ lúc nào.

---

## E10. Quản trị hệ thống (Admin)

### US-1001 · Quản lý Tài khoản Staff · P1
- AC1: Tạo, vô hiệu hoá Tài khoản Staff; vô hiệu hoá thì mọi phiên của Tài khoản đó mất hiệu lực ngay.
- AC2: Email đã thuộc một Tài khoản khác (kể cả Tài khoản Khách hàng) thì không tạo được.
- AC3: Tài khoản Admin không tạo được trên back-office, chỉ tạo bằng lệnh `manage.py create_staff --admin`.

### US-1002 · Cấu hình vận hành · P1
- AC1: Sửa được Phí ship dự phòng, ngưỡng miễn phí ship, hạn mức COD; mọi lần sửa được ghi lịch sử.
- AC2: Thời gian Giữ hàng và hạn link thanh toán là cố định, không sửa được (BR-INV-05). Thông tin doanh nghiệp và các chính sách là nội dung tĩnh của Frontend ở MVP (xem [06-compliance.md](./06-compliance.md) mục 4).

### US-1003 · Báo cáo doanh thu cơ bản · P2
- AC1: Doanh thu theo ngày/tháng chỉ tính đơn **Hoàn tất**, ghi vào ngày Hoàn tất; Doanh thu của đơn = Tổng tiền đơn − Hoàn tiền của Đổi trả (BR-REV-01). Báo cáo tách tiền hàng và Phí ship (BR-REV-02).
- AC2: Cho trước Người mua trả tiền hai lần cho một đơn và lần thứ hai được hoàn (BR-PAY-05), khi đơn Hoàn tất, thì Doanh thu của đơn vẫn bằng Tổng tiền đơn.
- AC3: Có thêm số liệu tạm cho đơn Đã giao chưa Hoàn tất, hiển thị tách khỏi Doanh thu.
- AC4: Admin xuất danh sách đơn đã thu tiền theo ngày ra file rồi gửi cho kế toán xuất hoá đơn (xem [06-compliance.md](./06-compliance.md)).

### US-1004 · Ánh xạ phường/xã sang GHN · P1
- AC1: Admin xem danh sách phường/xã chưa có ánh xạ sang GHN, kèm số đơn đang có Cờ cần xử lý `ghn_ward_unmapped`.
- AC2: Admin chọn ID tỉnh, quận, phường của GHN cho một phường/xã; lưu xong thì Staff bàn giao các đơn đó như bình thường rồi gỡ cờ.
- AC3: Story này có thể bỏ nếu kiểm tra cho thấy API GHN đã dùng địa chỉ 2 cấp (xem [06-integrations.md](../architecture/06-integrations.md) mục 4.2).

---

## E11. Dữ liệu cá nhân

### US-1101 · Yêu cầu xoá dữ liệu · P1
- AC1: Khách hàng gửi yêu cầu xoá trong tài khoản; Khách vãng lai gửi qua kênh hỗ trợ.
- AC2: Staff xử lý yêu cầu thì thông tin cá nhân được ẩn danh, dữ liệu đơn vẫn giữ cho kế toán (CMP-05).
- AC3: Tài khoản đã ẩn danh không đăng nhập được nữa.
- AC4: Yêu cầu chỉ được hoàn thành khi mọi Đơn hàng của người đó đã ở trạng thái cuối (Hoàn tất, Đã huỷ, Hoàn hàng) và không còn Hoàn tiền nào chờ xử lý; trước đó yêu cầu ở trạng thái chờ.
- AC5: Yêu cầu của Khách hàng chỉ ẩn danh các đơn đã gắn vào Tài khoản. Đơn vãng lai chưa gắn cần một Yêu cầu xoá dữ liệu riêng, Staff xác minh người yêu cầu (CMP-05).

### US-1102 · Lịch sử truy cập dữ liệu Người mua · P2
- AC1: Mỗi lần Staff mở chi tiết Khách hàng, mở chi tiết Đơn hàng, hoặc tìm đơn theo số điện thoại đều được ghi lại: ai, lúc nào, xem dữ liệu của ai (CMP-07).
- AC2: Mở danh sách đơn không được ghi.
