# Guide ticket 10 — Kiểm kê

## Mục đích

Staff nhập số đếm; server tính delta trên trạng thái đã khóa và ghi movement khi có chênh lệch.

## Bản đồ file

| Vị trí | Dùng làm gì | Mục đích |
|---|---|---|
| `inventory/services/stock.py` | `count_stock` | Tính delta server-side |
| inventory API serializer/view | counted_quantity command | Không nhận delta client |
| tests mentor tạo | zero/race/idempotency | Bảo vệ công thức |

## Cách viết code và thứ tự thực hiện

Ở mỗi Step, đặt tên rõ `counted_quantity`, `shelf_quantity` và `delta`; không dùng `data`/`value`. Viết công thức và case table trước, sau đó service lock dữ liệu, tính chênh lệch và ghi movement khi cần. Chạy test sau từng case.

1. **Step 1:** Nhận test đỏ count tăng/giảm.
2. **Step 2:** Viết service lock rồi tính counted − hàng trên kệ.
3. **Step 3:** Không tạo movement khi delta 0.
4. **Step 4:** Nối API/idempotency/OpenAPI.
5. **Step 5:** Làm xanh concurrency/boundary tests, gates/review.

## Kiến thức

Derived value under lock, zero-delta no-op, transaction history, concurrent update.
