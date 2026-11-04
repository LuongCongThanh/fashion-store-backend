# 10 – Kiểm kê theo số đếm trên kệ

Status: ready-for-agent · Ưu tiên: 13 · Blocked by: [09](../09-stock-adjustment/spec.md) · **PR:** —

## Mục tiêu
Staff nhập số đếm trên kệ; server tính chênh lệch lúc xác nhận, điều chỉnh Tồn kho và ghi lịch sử. Client không gửi delta.

## Việc cần làm
- [ ] `inventory/services/stock.py`: `count_stock` — khoá StockItem, tính `delta = counted_quantity − shelf_quantity` với `shelf_quantity = on_hand + awaiting_dispatch`, ghi movement lý do "kiểm kê" khi `delta != 0`.
- [ ] Serializer/view `POST stock/count` nhận `counted_quantity` theo Biến thể, `Idempotency-Key`, OpenAPI.
- [ ] Case table trước khi code: tăng, giảm, 0, giảm vượt available. Test thêm race và idempotency.

## Quyết định
- Công thức và thời điểm tính theo BR-INV-12, US-703 AC1, AC3; ví dụ chuẩn US-703 AC2 (Tồn kho 7 + 3 Hàng chờ xuất, đếm 10 → delta 0).
- Giảm vượt Số lượng bán được → `409 INSUFFICIENT_AVAILABLE` như ticket 09 (BR-INV-11).
- Endpoint theo [04 §4.2](../../../../docs/architecture/04-api-contract.md).

## Acceptance criteria
- [ ] Delta tính server-side từ `counted_quantity` và hàng trên kệ dưới khoá.
- [ ] Delta 0 không tạo movement nhưng trả kết quả/idempotency ổn định.
- [ ] Không vi phạm invariant available/reserved; race với thao tác kho khác serialize đúng.
- [ ] Availability projection, permission, idempotency đúng.
- [ ] API/OpenAPI/concurrency tests xanh.

## Ghi chú
- Đặt tên rõ `counted_quantity`, `shelf_quantity`, `delta`; không dùng `data`/`value`.
