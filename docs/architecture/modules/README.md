# Các module nghiệp vụ

Mỗi **module** là một vùng nghiệp vụ có ranh giới và là đúng một Django app trong `apps/` ([ADR 0018](../../adr/0018-one-django-app-per-module.md)). Khuôn chung, quy tắc import và lớp phụ thuộc ở [02](../02-backend-structure.md); file ở đây chỉ ghi phần riêng của từng module.

| Lớp | Module | Sở hữu | Code |
|---|---|---|---|
| 6 | [`notifications`](./notifications.md) | Email theo sự kiện | _(kế hoạch)_ |
| 5 | [`ordering`](./ordering.md) | Giỏ hàng, checkout, Đơn hàng, Đổi trả, Cờ cần xử lý | _(kế hoạch)_ |
| 4 | [`inventory`](./inventory.md) | Kho, Tồn kho, Giữ hàng, Hàng chờ xuất, Kiểm kê | _(kế hoạch)_ |
| 4 | [`promotions`](./promotions.md) | Voucher, Lượt dùng Voucher | _(kế hoạch)_ |
| 3 | [`identity`](./identity.md) | Tài khoản, xác thực, sổ địa chỉ, dữ liệu cá nhân | Một phần |
| 3 | [`catalog`](./catalog.md) | Danh mục, Sản phẩm, Biến thể, Giá bán, Giá khuyến mãi | _(kế hoạch)_ |
| 3 | [`payments`](./payments.md) | Thanh toán, Hoàn tiền, Đối soát | _(kế hoạch)_ |
| 3 | [`shipping`](./shipping.md) | Phí ship, Vận đơn, Đối soát | _(kế hoạch)_ |
| 2 | [`geo`](./geo.md) | Tỉnh/thành, phường/xã | Có |

Dàn ý chung: 1. **Sở hữu** · 2. **Cây thư mục** · 3. **Quan hệ với module khác** (gọi `contracts` nét liền; sự kiện nét đứt, chiều phát → nghe) · 4. **Public API** (`contracts.py`, `events.py`, `exceptions.py`) · 5. **Quy tắc riêng** (chỉ phần đặc thù) · 6. **Tài liệu liên quan**.

Field của model không chép ở đây; schema nằm ở [03](../03-data-model.md). Danh mục sự kiện đầy đủ và lịch job ở [07](../07-async-events-jobs.md).
