# Guide ticket 09 — Điều chỉnh Tồn kho

## Mục đích

Staff sửa chênh lệch có lý do mà không giảm vượt Số lượng bán được.

## Bản đồ file

| Vị trí | Dùng làm gì | Mục đích |
|---|---|---|
| `inventory/services/stock.py` | `adjust_stock` | Reuse lock/movement seam |
| inventory exceptions | `INSUFFICIENT_AVAILABLE` | Lỗi domain ổn định |
| inventory API serializer/view | adjust command | HTTP adapter |
| tests mentor tạo | boundary/concurrency/idempotency | Hành vi |

## Cách viết code và thứ tự thực hiện

Ở mỗi Step, tái dùng seam lock của Tồn kho thay vì copy ORM. Viết type hints và pseudo-code cho delta dương/âm/zero, rồi triển khai từng trường hợp dưới transaction. Domain exception phải mô tả tình huống; view chỉ map contract ra HTTP.

1. **Step 1:** Nhận test đỏ adjustment thành công.
2. **Step 2:** Viết service trên seam StockItem lock hiện có.
3. **Step 3:** Nối serializer/view/idempotency/OpenAPI.
4. **Step 4:** Làm xanh reason/delta/insufficient/race tests.
5. **Step 5:** Chạy gates và review.

## Kiến thức

DomainError details, signed delta, row locking, rollback, idempotent response replay.
