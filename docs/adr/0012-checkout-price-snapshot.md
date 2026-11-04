# Chốt giá dưới khoá Biến thể trong transaction checkout

Checkout báo giá và gọi GHN ngoài transaction, để không giữ khoá trong lúc chờ mạng. Vì vậy phải có cách chứng minh rằng đơn được tạo đúng với báo giá Người mua đã xem. Chọn hai việc đi cùng nhau:

1. **Tính thử trả `quote_token` có chữ ký, không lưu bảng Quote.** Token gắn với Người mua, nội dung checkout, giỏ hàng và phiên bản/snapshot của từng Biến thể. Không cần lưu và purge báo giá; đổi lại, không thu hồi riêng được từng token, và checkout luôn phải kiểm tra lại dữ liệu hiện hành.
2. **Kiểm tra lại dưới khoá Biến thể và bắt mọi writer của catalog cùng khoá.** Trong transaction tạo đơn, checkout khoá Cart, StockItem rồi Variant, so với token; khác ở bất kỳ điểm nào thì trả `PRICE_CHANGED`, kể cả khi tổng tiền tình cờ không đổi. Mọi service sửa dữ liệu ảnh hưởng checkout, kể cả thêm SalePrice mới, phải khoá các Variant bị ảnh hưởng trước khi ghi. Chỉ khoá ở checkout mà không ràng buộc writer thì không chặn được Giá khuyến mãi được thêm đồng thời.

Chi tiết: luồng ở [`ordering` mục 5.1](../architecture/modules/ordering.md#51-luồng-checkout), thứ tự khoá và quy tắc writer ở [13 mục 4](../architecture/13-python-django-coding-style.md#4-service-transaction-và-tác-vụ-bên-ngoài), payload và vòng đời token ở [04 mục 5.3](../architecture/04-api-contract.md#53-vòng-đời-quote_token).

## Các phương án đã cân nhắc

- **Bảng Quote trong DB**: thu hồi được từng báo giá, nhưng thêm bảng, job purge và một lần ghi cho mỗi lần Tính thử; không chọn.
- **Cho phép dùng báo giá cũ nếu tổng tiền không đổi**: ít lần phải xác nhận lại hơn, nhưng đơn có thể mang snapshot (tên, SKU, mức giảm quyết định quyền Đổi trả) khác cái Người mua đã thấy; không chọn.

## Hệ quả

- Checkout phải khoá Variant ngay cả khi tồn kho không đổi, và có thể bắt Người mua xác nhận lại dù tổng tiền không đổi.
- Cần quote mới thì rollback trước rồi mới gọi tích hợp bên ngoài; không gọi GHN khi đang giữ khoá.
- Token dùng keyring và salt riêng, không dùng khoá JWT ([05 mục 2](../architecture/05-auth-security.md#2-thiết-kế-jwt)).
