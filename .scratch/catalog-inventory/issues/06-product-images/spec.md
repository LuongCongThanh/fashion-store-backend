# 06 – Quản lý ảnh Sản phẩm theo màu

Status: ready-for-agent · Ưu tiên: 10 · Blocked by: [05](../05-product-variant-management/spec.md) · **PR:**

## Mục tiêu
Admin upload, sắp xếp, xoá bộ ảnh gắn với màu của Sản phẩm; mọi size cùng màu dùng chung ảnh (BR-CAT-05); client chỉ nhận URL an toàn.

## Việc cần làm
- [ ] `modules/catalog/models/product_image.py` + migration: metadata file, `position`, FK `ProductColor`.
- [ ] `services/images.py`: validate → xử lý (Pillow) → lưu storage → ghi DB; reorder; delete; cleanup khi lỗi.
- [ ] `api/backoffice/`: `POST products/{id}/images` (multipart), `PATCH/DELETE products/{id}/images/{image_id}`.
- [ ] Storage qua Django storage settings (local/S3), không hard-code filesystem.

## Quyết định
- Schema: [03 §3.6](../../../../docs/architecture/03-data-model.md); endpoint/DTO: [04-api-contract](../../../../docs/architecture/04-api-contract.md).
- Chỉ JPEG/PNG/WebP, ≤5 MB, strip EXIF, giới hạn pixel, tên file UUID.
- Tách metadata DB khỏi thao tác storage; kiểm input trước side effect; định nghĩa cleanup khi lỗi.
- View chỉ nhận multipart rồi gọi service; không xử lý Pillow trong serializer.

## Acceptance criteria
- [ ] Upload JPEG/PNG/WebP hợp lệ ≤5 MB: strip EXIF, giới hạn pixel, tên file UUID.
- [ ] MIME giả, file quá lớn, decompression bomb, nested ownership sai bị từ chối.
- [ ] Reorder/delete đúng ProductColor; lỗi storage/DB không để trạng thái mồ côi không kiểm soát.
- [ ] Response chỉ có URL, không credential hay path local.
- [ ] Multipart OpenAPI và API/storage test xanh; `make fmt`, `make lint` sạch.

## Ghi chú
- Mentor viết test đỏ + fixture ảnh (upload nhỏ hợp lệ trước); người làm viết production code.
- Bẫy: transaction DB không rollback được file đã ghi lên storage — xử lý side effect ngoài transaction rõ ràng.
