# 06 — Quản lý ảnh Sản phẩm theo màu

**What to build:** Admin upload, sắp xếp và xóa bộ ảnh gắn với màu của Sản phẩm; storefront sau này chỉ nhận URL an toàn và mọi size cùng màu dùng chung ảnh.

Blocked by: 05 — Sản phẩm và ProductColor tồn tại.

Status: ready-for-agent

**PR:** —

- [ ] Upload JPEG/PNG/WebP hợp lệ ≤5 MB, strip EXIF, giới hạn pixel và tên file UUID.
- [ ] MIME giả, file quá lớn/decompression bomb và nested ownership sai bị từ chối.
- [ ] Reorder/delete đúng ProductColor; lỗi storage/DB không để trạng thái mồ côi không kiểm soát.
- [ ] Response chỉ có URL, không credential/path local.
- [ ] Multipart OpenAPI và API/storage tests xanh.
