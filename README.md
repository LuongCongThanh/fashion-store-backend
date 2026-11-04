# Fashion Store – Backend Django

Website bán lẻ thời trang B2C cho thị trường Việt Nam. Backend là **Django + Django REST Framework** (modular monolith), phục vụ storefront và back-office Next.js (làm sau).

Repo dành riêng cho **Fashion Store**, với nghiệp vụ thời trang, thanh toán VNPay/MoMo/COD và vận chuyển GHN; không đặt mục tiêu xây boilerplate ecommerce dùng chung cho nhiều dự án.

> Trạng thái: **tài liệu đã chốt cho MVP, bắt đầu code**. Thứ tự làm theo [roadmap MVP](./.scratch/mvp-roadmap/map.md), bắt đầu từ mốc M0 ([dựng khung backend](./.scratch/backend-bootstrap/spec.md)).

## Tóm tắt

| Hạng mục | Lựa chọn |
|---|---|
| Mô hình | B2C, một người bán, thời trang (Biến thể size × màu) |
| Thanh toán | VNPay, MoMo, COD |
| Vận chuyển | GHN |
| Backend | Python 3.14, Django 5.2 LTS, DRF, PostgreSQL 18, Redis, Celery |
| Kiến trúc | Modular monolith: mỗi module một Django app trong `apps/`, app `common` hạ tầng nội bộ |
| Local | PostgreSQL cài trên máy (macOS: Homebrew qua `scripts/setup/postgres.sh`; Windows: bộ cài EDB rồi `scripts/setup/postgres.ps1`, không dùng WSL2); API chạy trên máy bằng `uv run`; Celery, Redis, Mailpit chạy bằng Docker Compose |
| Production (mục tiêu) | AWS Singapore: ECS Fargate (Django và Next.js BFF, cùng VPC), RDS, ElastiCache, S3, SES |

## Tài liệu

Thuật ngữ chung: **[GLOSSARY.md](./GLOSSARY.md)** — đọc trước tiên.

### Trạng thái tài liệu

Toàn bộ tài liệu trong `docs/` ở trạng thái **Đã chốt cho MVP** từ 29/10/2026. Từ mốc này:

- Tài liệu được cập nhật **cùng PR với code** khi code chạm tới phần đó. Code và tài liệu lệch nhau thì sửa cho khớp trong cùng PR, không để tài liệu đi sau.
- Quyết định khó đảo ngược, có đánh đổi thật thì thêm ADR mới trong `docs/adr/`; không sửa lại ADR cũ để đổi quyết định.
- Mỗi quy tắc có **một nơi sở hữu**; nơi khác chỉ tóm tắt một câu và dẫn link. Ví dụ checkout: luồng ở [`ordering` mục 5.1](./docs/architecture/modules/ordering.md#51-luồng-checkout), thứ tự khoá ở [13 mục 4](./docs/architecture/13-python-django-coding-style.md#4-service-transaction-và-tác-vụ-bên-ngoài), `quote_token` ở [04 mục 5.3](./docs/architecture/04-api-contract.md#53-vòng-đời-quote_token).

Hai loại nhãn còn lại trong tài liệu:

| Nhãn | Nghĩa |
|---|---|
| **[Giả định · kiểm chứng: …]** | Con số đã chốt để code, sẽ được kiểm lại bằng số liệu ở nơi ghi trong nhãn. Kết quả khác thì sửa con số trong một PR, không cần ADR |
| **[Cần xác minh]** | Phụ thuộc bên ngoài (tài liệu nhà cung cấp, sandbox, pháp lý). Mỗi mục được gắn vào mốc cần nó trong [roadmap](./.scratch/mvp-roadmap/map.md); `[Cần xác minh trước go-live]` không chặn code, là điều kiện go-live ([06-compliance mục 6](./docs/business/06-compliance.md#6-điều-kiện-go-live)) |

### Business (`docs/business/`)

1. [Tầm nhìn và phạm vi](./docs/business/01-vision-scope.md)
2. [Vai trò người dùng và phân quyền](./docs/business/02-actors-permissions.md)
3. [User stories](./docs/business/03-user-stories.md)
4. [Quy tắc nghiệp vụ](./docs/business/04-business-rules.md)
5. [Vòng đời Đơn hàng](./docs/business/05-order-lifecycle.md)
6. [Tuân thủ pháp lý](./docs/business/06-compliance.md)

### Architecture (`docs/architecture/`)

1. [Bối cảnh hệ thống (C4)](./docs/architecture/01-system-context.md)
2. [Cấu trúc Backend: thư mục, module, vai trò từng file](./docs/architecture/02-backend-structure.md) ⭐ và [từng module](./docs/architecture/modules/README.md)
3. [Mô hình dữ liệu](./docs/architecture/03-data-model.md)
4. [API contract](./docs/architecture/04-api-contract.md)
5. [Xác thực và bảo mật](./docs/architecture/05-auth-security.md)
6. [Tích hợp bên ngoài](./docs/architecture/06-integrations.md)
7. [Sự kiện và job chạy nền](./docs/architecture/07-async-events-jobs.md)
8. [Môi trường phát triển local](./docs/architecture/08-local-development.md)
9. [Triển khai AWS (mục tiêu)](./docs/architecture/09-deployment-aws-target.md)
10. [Yêu cầu phi chức năng](./docs/architecture/10-nfr.md)
11. [Quy ước Git](./docs/architecture/11-git-workflow.md)
12. [Chiến lược test](./docs/architecture/12-testing-strategy.md)
13. [Coding style Python/Django](./docs/architecture/13-python-django-coding-style.md)
14. [Package dùng và không dùng](./docs/architecture/14-dependencies.md)

### Quyết định kiến trúc (`docs/adr/`)

| ADR | Quyết định |
|---|---|
| [0001](./docs/adr/0001-nextjs-frontend-django-api.md) | Frontend Next.js tách riêng, Backend là Django API |
| [0002](./docs/adr/0002-auth-nextauth-session-django-jwt.md) | NextAuth giữ session, Django tự phát hành JWT bằng PyJWT |
| [0003](./docs/adr/0003-postgres-redis-celery.md) | PostgreSQL, Redis và Celery làm runtime |
| [0004](./docs/adr/0004-custom-nextjs-admin.md) | Back-office tự xây bằng Next.js thay vì Django Admin |
| [0005](./docs/adr/0005-provider-adapters-fake-gateways.md) | Adapter cho nhà cung cấp, cổng giả lập và job đối soát |
| [0006](./docs/adr/0006-modular-monolith.md) | Modular monolith: một app `modules` chia module con (đã thay bởi 0018) |
| [0007](./docs/adr/0007-events-outbox-celery-no-kafka.md) | Sự kiện qua Outbox + Celery, chưa dùng Kafka |
| [0008](./docs/adr/0008-uuid-v7-primary-keys.md) | Khoá chính UUID v7, sinh qua hàm bọc `common.models.uuid7` (dùng `uuid.uuid7()` của Python 3.14) |
| [0009](./docs/adr/0009-nextjs-bff-django-private.md) | Next.js là BFF cho mọi request, Django chỉ mở webhook ra internet |
| [0010](./docs/adr/0010-stock-decremented-at-order-awaiting-dispatch.md) | Trừ Tồn kho khi bán, theo dõi Hàng chờ xuất tới lúc Bàn giao |
| [0011](./docs/adr/0011-audit-field-allowlist.md) | Audit theo danh sách field, không sao chép raw payload chứa PII |
| [0012](./docs/adr/0012-checkout-price-snapshot.md) | Kiểm tra lại giá và điều kiện bán dưới khoá Biến thể khi checkout |
| [0013](./docs/adr/0013-recoverable-payment-initiation.md) | Khởi tạo Thanh toán có thể phục hồi bằng cùng Payment và mã nhà cung cấp |
| [0014](./docs/adr/0014-refresh-single-successor.md) | Refresh chỉ có một successor, trả lại response mã hoá trong cửa sổ 10 giây |
| [0015](./docs/adr/0015-local-postgres-on-host.md) | PostgreSQL ở local cài trên máy, bản major mới nhất |
| [0016](./docs/adr/0016-erasure-evidence-phone-hmac.md) | Bằng chứng tuân thủ giữ HMAC số điện thoại, không giữ số thô sau khi ẩn danh |
| [0017](./docs/adr/0017-windows-native-dev-api-on-host.md) | Windows dev không qua WSL2, API chạy trên máy |
| [0018](./docs/adr/0018-one-django-app-per-module.md) | Mỗi module là một Django app; `common` và `infrastructure` |

### Cấu hình cho agent (`docs/agents/`)

Quy ước để Claude Code và các skill engineering đọc repo này. Điểm vào là [CLAUDE.md](./CLAUDE.md).

1. [Issue tracker](./docs/agents/issue-tracker.md): spec và ticket dạng Markdown trong `.scratch/`, cách đóng ticket
2. [Trạng thái triage](./docs/agents/triage-labels.md)
3. [Tài liệu domain](./docs/agents/domain.md): agent đọc GLOSSARY, ADR và quy tắc nghiệp vụ thế nào

### Tài liệu Frontend cũ

Bộ tài liệu Next.js cũ (`docs/README.md`, `ARCHITECTURE.md`, `DOCS_INDEX.md`, `MIGRATION.md`, `PERFORMANCE.md`, `IMPORT_ALIAS_GUIDE.md`, `MCP_GUIDE.md`) đã được xoá vì không còn khớp với các quyết định trên. Khi làm Frontend có thể xem lại trong lịch sử git (commit `0f83e4c`).
