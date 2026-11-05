# Trừ Tồn kho khi bán, theo dõi Hàng chờ xuất tới lúc Bàn giao

Tồn kho bị trừ ngay khi hàng được bán: lúc đặt đơn COD, hoặc lúc Thanh toán online thành công (Giữ hàng chuyển thành trừ Tồn kho). Hàng đã bán nhưng chưa rời Kho (hàng rời Kho khi Vận đơn GHN tạo xong, sau Bàn giao) được `inventory` theo dõi riêng thành Hàng chờ xuất theo Mã đơn, mỗi dòng là một `DispatchLine`, nên hàng trên kệ = Tồn kho + Hàng chờ xuất. Lý do: Số lượng bán được chỉ cần trừ Giữ hàng khỏi Tồn kho, không phải trừ thêm các đơn chưa giao; mọi con số về hàng trong Kho nằm ở `inventory` và được cập nhật cùng transaction với Đơn hàng.

## Các phương án đã cân nhắc

- **Chỉ trừ Tồn kho lúc Bàn giao**: Tồn kho khớp số hàng trên kệ, nhưng mọi đơn đã đặt mà chưa giao phải thành một kiểu Giữ hàng không hết hạn, và Số lượng bán được phải trừ thêm phần đó. Phải sửa BR-INV-04, BR-INV-05, T2, T3, T7, T9 và data model; không chọn.
- **Không lưu Hàng chờ xuất, `ordering` tự đếm Dòng đơn hàng của các đơn chưa Bàn giao khi Kiểm kê**: ít code hơn, nhưng số liệu về hàng trong Kho bị chia ra hai module và màn Kiểm kê phải đặt ở `ordering`; không chọn.

## Hệ quả

- Tồn kho **không** bằng số hàng trên kệ. Kiểm kê so số Staff đếm được với Tồn kho + Hàng chờ xuất, rồi điều chỉnh Tồn kho theo phần chênh lệch.
- Khi Vận đơn tạo xong (T10), `ordering` gọi `inventory.contracts.dispatch_stock(reference)` để xoá Hàng chờ xuất của đơn. Huỷ đơn trước khi hàng rời Kho (T7, T9) gọi `release_dispatch_line(reference)`: giảm Hàng chờ xuất và trả lại Tồn kho trong cùng transaction.
- Hàng Hoàn hàng và hàng Đổi trả được cộng lại Tồn kho khi về Kho; lúc này hàng đã rời Hàng chờ xuất từ T10.
