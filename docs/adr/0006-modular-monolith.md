# Modular monolith: một Django app `modules`, bên trong chia module nghiệp vụ

> **Đã được thay thế** ở phần tổ chức Django app bởi [ADR 0018](./0018-one-django-app-per-module.md): mỗi module là một Django app trong `apps/`, `shared` đổi thành `common`. Các quy tắc ranh giới giữa module dưới đây vẫn áp dụng.

Backend là một Django project duy nhất, deploy một lần. Toàn bộ nghiệp vụ nằm trong **một** Django app tên `modules`. Bên trong app này, mỗi module nghiệp vụ là một package con (`modules/catalog/`, `modules/ordering/`…) có models, services, selectors và API riêng. Hạ tầng dùng chung (outbox sự kiện, dữ liệu địa giới hành chính) nằm trong một app thứ hai là `shared`; app này không chứa nghiệp vụ và không import `modules`.

Ranh giới giữa các module được giữ bằng ba quy tắc:

1. Module chỉ gọi nhau qua `contracts.py` của module kia; được import thêm `events.py` và `exceptions.py` của module lớp dưới. Ngoại lệ import model để khai báo FK được mô tả bên dưới. `import-linter` kiểm tra quy tắc này trong CI.
2. Việc phụ, và mọi thông báo từ lớp dưới lên lớp trên, đi qua sự kiện phát sau khi transaction commit.
3. Phụ thuộc chỉ đi một chiều, từ trên xuống:
   `notifications` → `ordering` → `inventory`, `promotions` → `identity`, `catalog`, `payments`, `shipping` → `shared`.
   Các module cùng lớp không import lẫn nhau.

Khoá ngoại (FK) giữa các module được phép, nhưng chỉ theo chiều phụ thuộc ở quy tắc 3.

`payments` và `shipping` được đặt ở lớp dưới `ordering` và không biết gì về Đơn hàng. Chúng chỉ làm việc với một mã tham chiếu (`reference`) và báo kết quả lên bằng sự kiện. Nhờ vậy `ordering` gọi được chúng khi checkout mà không tạo vòng phụ thuộc. Giá khuyến mãi nằm trong `catalog` cùng với giá bán, vì danh sách Sản phẩm cần lọc và sắp xếp theo giá áp dụng.

Lý do chọn một app thay vì mỗi module một app: team muốn chỉ có một Django app nghiệp vụ cần đăng ký và cấu hình, và chấp nhận đánh đổi là dùng chung một chuỗi migrations.

## Các phương án đã cân nhắc

- **Mỗi module là một Django app**: có migrations riêng và ranh giới ở cả mức database, nhưng không chọn vì muốn giữ cấu hình chỉ có một app nghiệp vụ.
- **Cấm FK giữa các module, chỉ lưu ID**: không chọn, vì mất ràng buộc toàn vẹn ở database đối với dữ liệu tiền và hàng.

## Hệ quả

- Toàn bộ model dùng chung một thư mục `modules/migrations/`. Khi hai nhánh code cùng tạo migration sẽ phải merge (`makemigrations --merge`). CI cần chặn trường hợp migration bị trùng số.
- `modules/models.py` phải import model của mọi module con thì Django mới nhận ra. Tương tự, `management/commands/`, `templates/` và `admin.py` phải nằm ở gốc `modules/`.
- Mỗi model phải khai báo `Meta.db_table` có tiền tố theo module con (ví dụ `catalog_product`), để nhìn tên bảng là biết thuộc module nào.
- Django đăng ký model theo `app_label.ModelName`, mà mọi module con dùng chung `app_label = "modules"`. Vì vậy tên class model phải duy nhất trong toàn app `modules`, kể cả khi nằm ở hai module con khác nhau.
- Ranh giới giữa các module chỉ được kiểm tra ở mức import trong code, nên `import-linter` là bắt buộc trong CI, không phải tuỳ chọn.
- FK sang module khác khai báo bằng class được import, kể cả FK tới `Account`, không khai báo bằng chuỗi (`settings.AUTH_USER_MODEL`, `"modules.Variant"`). FK khai báo bằng chuỗi không tạo import nên `import-linter` không kiểm tra được chiều của nó.
- FK chỉ để database giữ toàn vẹn dữ liệu, không để truy vấn xuyên module: không dùng lookup `__`, `select_related`, `prefetch_related` đi vào model của module khác, mà lấy dữ liệu qua `contracts.py`. Nếu không, schema của module kia sẽ ngầm thành một phần interface của nó. ORM đi qua FK mà không cần import, nên quy tắc này chỉ kiểm tra được khi review.
- Dòng đơn hàng lưu bản chụp (snapshot) tên, SKU và đơn giá tại thời điểm đặt, nên vẫn đúng dù Sản phẩm thay đổi sau này.
