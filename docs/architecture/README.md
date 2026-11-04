# Tài liệu kiến trúc Backend

Kiến trúc kỹ thuật của backend Django cho Fashion Store. README chỉ là bản đồ: mỗi file trả lời câu hỏi gì; chi tiết nằm trong từng file.

## Vị trí trong bộ tài liệu

| Thư mục | Trả lời câu hỏi |
|---|---|
| [`GLOSSARY.md`](../../GLOSSARY.md) | Thuật ngữ nghiệp vụ nghĩa là gì, gọi tên thế nào cho đúng |
| [`docs/business/`](../business/) | Hệ thống phải làm gì |
| [`docs/adr/`](../adr/) | Vì sao chọn cách làm này |
| `docs/architecture/` (thư mục này) | Hệ thống được xây dựng như thế nào |

## Trạng thái

Mọi file **Đã chốt cho MVP**, riêng [09](./09-deployment-aws-target.md) là kiến trúc đích **chưa triển khai** (hạ tầng AWS chưa tồn tại, chỉ để định hướng). Quy ước nhãn: [README gốc](../../README.md#trạng-thái-tài-liệu).

## Đọc gì trước

Dev mới đọc theo thứ tự **01 → 02 → 13 → 08 → 11**; các file còn lại đọc khi làm tới phần liên quan.

## Tổng quan

| File | Trả lời câu hỏi | Liên quan |
|---|---|---|
| [01. Bối cảnh hệ thống](./01-system-context.md) | Hệ thống gồm những bên, container và module nào (C4 mức 1–3)? | [ADR 0001](../adr/0001-nextjs-frontend-django-api.md), [ADR 0009](../adr/0009-nextjs-bff-django-private.md) |
| [02. Cấu trúc Backend](./02-backend-structure.md) | Code đặt ở đâu, module phụ thuộc nhau thế nào? Hay tra cứu nhất khi viết code. | [ADR 0018](../adr/0018-one-django-app-per-module.md), [ADR 0007](../adr/0007-events-outbox-celery-no-kafka.md) |
| [Các module](./modules/README.md) | Mỗi module sở hữu gì, public API và quy tắc riêng? Luồng checkout: [`ordering`](./modules/ordering.md#51-luồng-checkout). | |

## Thiết kế chi tiết

| File | Trả lời câu hỏi | Liên quan |
|---|---|---|
| [03. Mô hình dữ liệu](./03-data-model.md) | Bảng, quan hệ và quy ước dữ liệu của từng module? | [ADR 0008](../adr/0008-uuid-v7-primary-keys.md), [ADR 0010](../adr/0010-stock-decremented-at-order-awaiting-dispatch.md) |
| [04. API contract](./04-api-contract.md) | Quy ước REST, lỗi, phân trang và danh sách endpoint? | |
| [05. Xác thực và bảo mật](./05-auth-security.md) | Session, JWT, phân quyền và bảo vệ hệ thống thế nào? | [ADR 0002](../adr/0002-auth-nextauth-session-django-jwt.md), [ADR 0009](../adr/0009-nextjs-bff-django-private.md) |
| [06. Tích hợp bên ngoài](./06-integrations.md) | Gọi VNPay, MoMo, GHN, Google, email ra sao và test thế nào? | [ADR 0005](../adr/0005-provider-adapters-fake-gateways.md) |
| [07. Sự kiện và job chạy nền](./07-async-events-jobs.md) | Outbox, Celery, sự kiện và job định kỳ hoạt động thế nào? | [ADR 0003](../adr/0003-postgres-redis-celery.md), [ADR 0007](../adr/0007-events-outbox-celery-no-kafka.md) |

## Vận hành và hạ tầng

| File | Trả lời câu hỏi | Liên quan |
|---|---|---|
| [08. Môi trường phát triển local](./08-local-development.md) | Dựng môi trường trên macOS/Windows và lệnh hằng ngày? | [ADR 0015](../adr/0015-local-postgres-on-host.md), [ADR 0017](../adr/0017-windows-native-dev-api-on-host.md) |
| [09. Triển khai trên AWS (mục tiêu)](./09-deployment-aws-target.md) | Hạ tầng đích và quy trình deploy (**chưa triển khai**)? | |
| [10. Yêu cầu phi chức năng](./10-nfr.md) | Mục tiêu hiệu năng, sẵn sàng, bảo mật cho MVP là gì? | |

## Quy trình làm việc

| File | Trả lời câu hỏi |
|---|---|
| [11. Quy ước Git](./11-git-workflow.md) | Nhánh, commit, PR, CI, release và hotfix thế nào? |
| [12. Chiến lược test](./12-testing-strategy.md) | Test gì, ở tầng nào, chạy ra sao, cổng CI nào? |
| [13. Coding style Python/Django](./13-python-django-coding-style.md) | Viết code Python/Django theo chuẩn nào? Nguồn chuẩn duy nhất; không định nghĩa style TypeScript/Next.js khi frontend chưa bootstrap. |
| [14. Package dùng và không dùng](./14-dependencies.md) | Vì sao chọn hoặc loại từng package? Phiên bản chính xác ở `pyproject.toml` và `uv.lock`. |
