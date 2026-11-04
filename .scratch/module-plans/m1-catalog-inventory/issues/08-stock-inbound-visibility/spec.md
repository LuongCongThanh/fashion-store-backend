# 08 — Xem Tồn kho và Nhập kho

**What to build:** Staff xem Tồn kho/Số lượng bán được và ghi nhận hàng mới bằng số phiếu. Nhập kho cập nhật lịch sử và trạng thái còn hàng mà retry không cộng hai lần.

Blocked by: 05 — Biến thể; 07 — catalog contracts và giá/snapshot.

Status: ready-for-agent

**PR:** —

- [ ] Kho MAIN/StockItem/StockMovement và constraint/index được migrate đúng.
- [ ] Staff/Admin đọc danh sách Tồn kho, lọc tồn thấp và nhận SKU/tên qua public contract.
- [ ] Nhập kho khóa dòng, tăng on_hand, ghi movement actor/reference và cập nhật availability cùng transaction.
- [ ] Idempotency replay/conflict/pending đúng; concurrency không làm quantity sai.
- [ ] Permission, migration, API/OpenAPI, contract và flow tests xanh.
