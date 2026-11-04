# M1 — Catalog và Tồn kho

Status: ready-for-agent

## Problem Statement

Fashion Store chưa có luồng Backend hoàn chỉnh để Admin đăng nhập và quản lý Sản phẩm, Staff quản lý Tồn kho, còn Người mua duyệt/tìm/lọc Sản phẩm với đúng Giá áp dụng và trạng thái còn hàng. Code hiện tại mới có nền Django/shared và model Tài khoản; các module Catalog và Inventory chưa có hành vi nghiệp vụ hoặc HTTP API.

Người phát triển cần một phạm vi M1 có thể triển khai theo các lát cắt end-to-end, mỗi lát cắt tạo ra hành vi quan sát được, thay vì xây model/service/API rời rạc rồi chờ tới cuối mới tích hợp.

## Solution

Xây M1 theo chuỗi tracer bullet:

1. Staff/Admin đăng nhập back-office bằng JWT, sau đó xoay và thu hồi phiên.
2. Admin quản lý Danh mục, danh sách size, bảng màu, Sản phẩm, Biến thể, ảnh, Giá bán và Giá khuyến mãi.
3. Staff xem Tồn kho, Nhập kho, điều chỉnh và Kiểm kê; trạng thái còn hàng được phản chiếu sang Catalog.
4. Người mua truy cập API công khai để duyệt cây Danh mục, tìm/lọc/sắp xếp và xem chi tiết Sản phẩm.
5. Flow acceptance chứng minh toàn chuỗi qua HTTP API, PostgreSQL thật và OpenAPI.

## User Stories

1. Là Admin, tôi muốn đăng nhập back-office để quản lý Catalog an toàn.
2. Là Staff, tôi muốn đăng nhập back-office để thực hiện nghiệp vụ Tồn kho.
3. Là người dùng đã đăng nhập, tôi muốn xoay refresh token để phiên tiếp tục mà không nhập lại mật khẩu.
4. Là người dùng đã đăng nhập, tôi muốn đăng xuất để refresh family hiện tại không cấp thêm access token.
5. Là Admin, tôi muốn tạo và sắp xếp cây Danh mục để Người mua điều hướng theo nhóm Sản phẩm.
6. Là Người mua, tôi muốn xem cây Danh mục công khai để chọn nhóm Sản phẩm.
7. Là Admin, tôi muốn quản lý danh sách size và bảng màu chuẩn để mọi Biến thể dùng cùng mã.
8. Là Admin, tôi muốn tạo Sản phẩm draft và các Biến thể size×màu để chuẩn bị dữ liệu bán.
9. Là Admin, tôi muốn publish hoặc archive Sản phẩm để kiểm soát nội dung storefront.
10. Là Admin, tôi muốn quản lý ảnh theo màu để mọi size cùng màu dùng chung bộ ảnh.
11. Là Admin, tôi muốn đặt Giá bán và lịch Giá khuyến mãi để Giá áp dụng đúng thời điểm.
12. Là Staff, tôi muốn xem Tồn kho và Số lượng bán được theo Biến thể để biết tình trạng hàng.
13. Là Staff, tôi muốn Nhập kho với số phiếu để ghi nhận hàng mới và có lịch sử.
14. Là Staff, tôi muốn điều chỉnh Tồn kho có lý do để sửa sai lệch mà vẫn truy vết được.
15. Là Staff, tôi muốn Kiểm kê theo số đếm trên kệ để hệ thống tự tính chênh lệch.
16. Là Người mua, tôi muốn xem danh sách Sản phẩm active với ảnh, giá và trạng thái còn hàng.
17. Là Người mua, tôi muốn tìm tên không phân biệt dấu/hoa thường để tìm Sản phẩm nhanh.
18. Là Người mua, tôi muốn lọc theo Danh mục, size, màu, Giá áp dụng và còn hàng để thu hẹp kết quả.
19. Là Người mua, tôi muốn xem chi tiết theo màu/size để chọn đúng Biến thể, SKU, giá và ảnh.
20. Là đội phát triển, tôi muốn OpenAPI, migration, import boundaries và test gate bảo vệ contract M1.

## Implementation Decisions

- Backend giữ kiến trúc modular monolith. `identity`, `catalog`, `inventory` chỉ giao tiếp qua public contracts và event đã chốt; không import service/model nội bộ ngược layer.
- JWT dùng Ed25519 và keyring có `kid`. Access/refresh token có loại và audience riêng; back-office kiểm trạng thái Tài khoản từ PostgreSQL và fail-closed khi DB không xác minh được.
- Refresh rotation tạo đúng một successor, hỗ trợ replay response mã hóa trong 10 giây và thu hồi family khi phát hiện dùng lại ngoài cửa sổ.
- Catalog sở hữu Danh mục, size, màu, Sản phẩm, Biến thể, ảnh, Giá bán, Giá khuyến mãi và projection còn hàng.
- Inventory sở hữu Kho, StockItem và StockMovement. Mọi thay đổi `on_hand` đi qua service có transaction, actor và lịch sử.
- Số lượng bán được trong M1 bằng `on_hand`; schema vẫn tương thích Giữ hàng/Hàng chờ xuất ở các mốc sau.
- Khi availability đổi giữa 0 và dương, Inventory cập nhật projection Catalog trong cùng transaction qua public contract.
- API back-office dùng JWT `aud=backoffice`; chỉ Admin ghi Catalog, Staff/Admin thao tác Inventory. Storefront Catalog là public.
- Request/response/status/error tuân hợp đồng API hiện hành; OpenAPI đã sinh là contract frontend có CI drift check.
- Các ticket là vertical slice: mỗi ticket hoàn tất schema/service/API/OpenAPI/test cần thiết để demo hành vi của ticket.

## Testing Decisions

- Seam chính là HTTP API flow chạy với PostgreSQL thật. Test kiểm hành vi quan sát được, permission, response và side effect database.
- Assistant chuẩn bị test đỏ và giải thích hành vi; người học viết production code để làm test xanh.
- Service/concurrency/crypto test bổ sung khi invariant không thể chứng minh đủ qua API, đặc biệt refresh rotation, constraint giá và thao tác Tồn kho cạnh tranh.
- Flow acceptance dùng JWT thật, không dùng `force_authenticate` để khẳng định authentication hoạt động.
- Migration được kiểm từ DB rỗng và upgrade từ M0. Query list/detail có query-count/index baseline để ngăn N+1.
- Mỗi ticket chạy format, lint và targeted tests; ticket acceptance cuối chạy full suite và OpenAPI drift check.

## Out of Scope

- Đăng ký Customer, Google login, quên mật khẩu, sổ địa chỉ và Yêu cầu xoá dữ liệu.
- Giỏ hàng, Tính thử, checkout, Voucher, Giữ hàng, Hàng chờ xuất, Payment, Vận đơn và email nghiệp vụ.
- Frontend Next.js, AWS deployment, provider sandbox và k6 full load test.
- Số liệu bán chạy thật; M1 chỉ giữ hành vi sort ổn định khi số liệu chưa được job M4 cập nhật.

## Further Notes

- Thuật ngữ domain theo `GLOSSARY.md`; Sản phẩm và Biến thể không được dùng thay thế nhau.
- Hợp đồng API, data model và security docs vẫn sở hữu chi tiết schema/invariant. Spec này sở hữu phạm vi và hành vi M1.
- Mỗi ticket chỉ có `spec.md` lúc mở; `plan.md` tạo khi bắt đầu làm, `report.md` tạo sau khi có kết quả thực tế.

## Ticket Index

| # | Ticket | Blocked by |
|---:|---|---|
| 01 | [Back-office login](./issues/01-backoffice-login/spec.md) | None |
| 02 | [Refresh và logout](./issues/02-refresh-logout/spec.md) | 01 |
| 03 | [Quản lý Danh mục và storefront navigation](./issues/03-category-navigation/spec.md) | 01 |
| 04 | [Danh sách size và bảng màu](./issues/04-size-color-registry/spec.md) | 01 |
| 05 | [Quản lý Sản phẩm và Biến thể](./issues/05-product-variant-management/spec.md) | 03, 04 |
| 06 | [Ảnh Sản phẩm theo màu](./issues/06-product-images/spec.md) | 05 |
| 07 | [Giá bán và Giá khuyến mãi](./issues/07-pricing/spec.md) | 05 |
| 08 | [Xem Tồn kho và Nhập kho](./issues/08-stock-inbound-visibility/spec.md) | 05, 07 |
| 09 | [Điều chỉnh Tồn kho](./issues/09-stock-adjustment/spec.md) | 08 |
| 10 | [Kiểm kê](./issues/10-stock-count/spec.md) | 09 |
| 11 | [Storefront khám phá Sản phẩm](./issues/11-storefront-product-discovery/spec.md) | 06, 07, 10 |
| 12 | [Acceptance và hardening M1](./issues/12-m1-acceptance/spec.md) | 01–11 |
