# Guide ticket 06 — Ảnh theo màu

## Mục đích

Upload và quản lý ảnh an toàn theo ProductColor; không expose storage internals.

## Bản đồ file

| Vị trí | Dùng làm gì | Mục đích |
|---|---|---|
| `modules/catalog/models/product_image.py` | Metadata file/position | Liên kết ảnh với màu |
| `services/images.py` | validate/process/store/delete | Một seam side effect |
| `api/backoffice/` serializer/view | multipart HTTP | Admin capability |
| storage settings | local/S3 backend | Không hard-code filesystem |
| tests mentor tạo + fixtures ảnh | security/storage/API | Chặn file độc hại |

## Cách viết code và thứ tự thực hiện

Ở mỗi Step, tách metadata trong DB khỏi thao tác storage. Viết interface/function signature trước, kiểm input trước side effect và xác định cleanup khi lỗi. API view chỉ nhận multipart rồi gọi service; không nhét xử lý Pillow vào serializer.

1. **Step 1:** Nhận test đỏ upload ảnh nhỏ hợp lệ.
2. **Step 2:** Tạo model/migration và storage service.
3. **Step 3:** Viết multipart serializer/view/URL.
4. **Step 4:** Thêm reorder/delete.
5. **Step 5:** Làm xanh MIME/EXIF/pixel/ownership/error cleanup tests.
6. **Step 6:** Chạy gates/review.

## Kiến thức

Django storage, Pillow, multipart parser, file lifecycle, transaction vs external side effect.
