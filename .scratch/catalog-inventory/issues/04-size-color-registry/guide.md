# Guide ticket 04 — Size và màu

## Mục đích

Tạo registry chuẩn để Biến thể và filter không dùng chuỗi tùy ý.

## Bản đồ file

| Vị trí | Dùng làm gì | Mục đích |
|---|---|---|
| `modules/catalog/models/size.py`, `color.py` | Schema/constraint | Mã chuẩn, active flag |
| `modules/migrations/` | Bảng + seed FREESIZE | DB repeatable |
| `modules/catalog/services/` | create/update/hide | Chặn delete khi đã dùng |
| `modules/catalog/api/backoffice/` | GET/POST/PATCH | Admin quản lý |
| catalog tests (mentor tạo) | constraint/API/permission | Kiểm hành vi |

## Cách viết code và thứ tự thực hiện

Ở mỗi Step, viết enum/model/constraint trước, sau đó service ghi và API mỏng. Dùng type hints, tên biến nghiệp vụ và chia validation thành field-level với invariant cần DB. Viết từng capability nhỏ rồi chạy test mentor cung cấp.

1. **Step 1:** Nhận test đỏ create/list size và color.
2. **Step 2:** Tạo model/constraint/migration + seed FREESIZE.
3. **Step 3:** Viết service và serializers/views/URLs.
4. **Step 4:** Mentor thêm duplicate/hex/hide-used tests; bạn làm xanh.
5. **Step 5:** Chạy OpenAPI/gates và gửi review.

## Kiến thức

TextChoices/constraints, data migration, pagination, partial update, audit.
