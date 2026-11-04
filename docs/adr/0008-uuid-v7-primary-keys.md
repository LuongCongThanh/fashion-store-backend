# Khoá chính UUID v7, sinh qua hàm bọc `common.models.uuid7`

Các bảng do dự án định nghĩa dùng khoá chính UUID v7, trừ hai bảng địa giới được nêu bên dưới. Quy tắc không áp lên bảng framework hoặc event model do pghistory sinh (03 mục 0.9). `default` của `id` trong `common.models.BaseModel` là hàm của chính repo, `common.models.uuid7()`; hàm này gọi `uuid.uuid7()` có sẵn từ Python 3.14, nên không cần package ngoài. UUID không lộ số lượng đơn hay khách qua ID tăng dần; v7 có tiền tố thời gian nên sắp xếp được theo thời gian tạo và không làm index B-tree phân mảnh như v4.

Django ghi đường dẫn của `default` vào mọi file migration. Hàm bọc giữ đường dẫn trong migration cố định là `common.models.uuid7`, nên muốn đổi cách sinh UUID chỉ cần sửa thân hàm. Hàm bọc phải có trước migration đầu tiên; sau đó muốn đổi đường dẫn thì phải sửa hoặc squash các migration đã có.

## Các phương án đã cân nhắc

- **Số tự tăng (`BigAutoField`)**: loại, vì lộ quy mô kinh doanh qua ID trong URL và API.
- **UUID v4 (`uuid.uuid4`, có sẵn)**: loại, vì ngẫu nhiên hoàn toàn nên chèn rải rác khắp index và không sắp xếp được theo thời gian.
- **Python 3.13 kèm `uuid-utils`**: không chọn. Django 5.2 LTS đã hỗ trợ Python 3.14, và khi chưa có code thì lên 3.14 ngay rẻ hơn mang thêm một dependency rồi gỡ sau.

## Hệ quả

- Đổi kiểu cột (ví dụ sang số tự tăng) mới là việc tốn kém, vì phải migrate mọi bảng và mọi FK. Đổi cách sinh UUID (v7 sang v4) thì chỉ cần sửa hàm bọc.
- 48 bit đầu của UUID v7 là thời điểm tạo, tính bằng mili giây. Ai có `id` của Khách hàng, Địa chỉ hay Sản phẩm qua API đều biết bản ghi đó được tạo lúc nào. Rủi ro này được chấp nhận. Đơn hàng dùng `code` trên URL storefront nên không bị ảnh hưởng.
- Mã đơn (`ordering_order.code`) theo cùng lý do: không đánh số tuần tự mà là `FS<YYMM>-` cộng 6 ký tự Crockford Base32 ngẫu nhiên (ví dụ `FS2610-7K3QZD`), có ràng buộc `UNIQUE` và sinh lại khi trùng. Mã tuần tự theo tháng sẽ lộ số Đơn hàng mỗi tháng và dễ đoán, khiến việc tra cứu đơn của Khách vãng lai (Mã đơn + số điện thoại) chỉ còn dựa vào việc đoán số điện thoại.
- Ngoại lệ duy nhất là `geo_province` và `geo_ward`: hai bảng dùng mã chính thức của Cục Thống kê làm khoá chính, vì đây là dữ liệu nạp từ nguồn ngoài, mã ổn định, và được dùng làm FK ở nhiều bảng (`ship_ward_code`, `ward_code`). Các bảng có khoá tự nhiên khác (`common_event_delivery` theo cặp sự kiện–handler, `common_idempotency_key`, `identity_refresh_token.jti`, `shipping_ghn_location_mapping.ward_code`) vẫn có `id` UUID v7 và giữ khoá tự nhiên bằng ràng buộc `UNIQUE`, không dùng khoá chính ghép.
