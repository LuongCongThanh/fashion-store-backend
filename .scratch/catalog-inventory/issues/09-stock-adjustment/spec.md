# 09 – Điều chỉnh Tồn kho có lý do

Status: ready-for-agent · Ưu tiên: 12 · Blocked by: [08](../08-stock-inbound-visibility/spec.md) · **PR:** —

## Mục tiêu
Staff tăng/giảm Tồn kho bằng một lệnh có lý do. Không giảm vượt Số lượng bán được; lịch sử và idempotency đầy đủ.

## Việc cần làm
- [ ] `inventory/services/stock.py`: `adjust_stock`, tái dùng seam lock StockItem của ticket 08 (không copy ORM). Xử lý delta dương/âm; delta 0 bị từ chối.
- [ ] `inventory/exceptions.py`: lỗi domain `INSUFFICIENT_AVAILABLE` (409) kèm số tối đa giảm được trong `details`.
- [ ] Serializer/view `POST stock/adjust` + `Idempotency-Key` + OpenAPI.
- [ ] Test: reason bắt buộc, delta, insufficient, race, idempotency replay.

## Quyết định
- Lý do bắt buộc, mọi thay đổi ghi lịch sử (US-701 AC2, BR-INV-09).
- Giảm vượt Số lượng bán được → `409 INSUFFICIENT_AVAILABLE` kèm giới hạn (US-701 AC3, BR-INV-11, [04 §4.2](../../../../docs/architecture/04-api-contract.md), [modules/inventory §4.2](../../../../docs/architecture/modules/inventory.md)).
- Movement ghi actor/reason/reference theo [03 §4.5](../../../../docs/architecture/03-data-model.md#45-inventory_stock_movement-lịch-sử-thay-đổi-tồn-kho-br-inv-09).
- View chỉ map domain exception ra HTTP.

## Acceptance criteria
- [ ] Delta khác 0, lý do bắt buộc; movement ghi actor/reason/reference đúng.
- [ ] Giảm vượt available trả conflict kèm giới hạn, không đổi dữ liệu.
- [ ] Hai điều chỉnh cạnh tranh serialize đúng; không ra số âm.
- [ ] Idempotency replay/conflict và availability projection đúng.
- [ ] API/OpenAPI/concurrency tests xanh.

## Ghi chú
- Lỗi phải rollback toàn bộ (movement, projection, idempotency claim).
