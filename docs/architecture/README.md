# Tài liệu kiến trúc Backend

Thư mục này mô tả **kiến trúc kỹ thuật của backend Django** cho Fashion Store: hệ thống gồm những phần nào, code tổ chức ra sao, dữ liệu và API trông thế nào, chạy và triển khai ở đâu, làm việc với Git và test theo quy ước nào.

README chỉ là bản đồ để biết file nào trả lời câu hỏi nào. Nội dung chi tiết nằm trong từng file.

## Vị trí trong bộ tài liệu

| Thư mục | Trả lời câu hỏi |
|---|---|
| [`GLOSSARY.md`](../../GLOSSARY.md) | Thuật ngữ nghiệp vụ nghĩa là gì, gọi tên thế nào cho đúng |
| [`docs/business/`](../business/) | Hệ thống phải làm gì: phạm vi, vai trò, user story, quy tắc nghiệp vụ, vòng đời Đơn hàng, tuân thủ pháp lý |
| [`docs/adr/`](../adr/) | Vì sao chọn cách làm này: mỗi quyết định kiến trúc kèm lý do và phương án đã loại |
| `docs/architecture/` (thư mục này) | Hệ thống được xây dựng như thế nào |

## Trạng thái

Mọi file ở trạng thái **Đã chốt cho MVP**, riêng [09](./09-deployment-aws-target.md) là kiến trúc đích **chưa triển khai**: hạ tầng AWS chưa tồn tại, file đó chỉ để định hướng. Quy ước cập nhật và ý nghĩa các nhãn: [README gốc](../../README.md#trạng-thái-tài-liệu).

## Đọc gì trước

Dev mới vào dự án nên đọc theo thứ tự **01 → 02 → 13 → 08 → 11**: hiểu bức tranh chung, nắm cấu trúc và coding style, dựng được môi trường local, rồi biết cách tạo nhánh và PR. Các file còn lại đọc khi làm tới phần liên quan.

## Tổng quan

### [01. Bối cảnh hệ thống](./01-system-context.md)

Sơ đồ C4 ở mức 1, 2 và 3. Mức 1 gồm các bên liên quan: Người mua, Staff/Admin, VNPay, MoMo, GHN, Google, email, Sentry; file nói rõ bên nào gọi vào và bên nào được gọi ra. Mức 2 gồm các container: Next.js BFF, Django API, Celery worker, Celery Beat, Outbox relay, PostgreSQL, Redis. Mức 3 là các module bên trong backend. File kết thúc bằng sơ đồ luồng đặt hàng thanh toán qua VNPay.
Liên quan: [ADR 0001](../adr/0001-nextjs-frontend-django-api.md), [ADR 0009](../adr/0009-nextjs-bff-django-private.md).

### [02. Cấu trúc Backend](./02-backend-structure.md)

Bản đồ của repo. Backend là modular monolith: một Django project ở gốc repo, mỗi module nghiệp vụ là một Django app trong `apps/` (`geo`, `identity`, `catalog`, `inventory`, `promotions`, `payments`, `shipping`, `ordering`, `notifications`), cùng `common/` (hạ tầng nội bộ) và `infrastructure/` (code gọi API bên thứ ba). File này ghi:

- cây thư mục của toàn repo, mỗi file một dòng vai trò;
- thứ tự phụ thuộc giữa các module;
- khuôn mẫu một module theo HackSoft Styleguide (`models`, `services`, `selectors`, `contracts`, `events`…), khi nào dùng file hay package, và test đặt ở đâu;
- quy tắc FK sang module khác và cách `import-linter` kiểm tra ranh giới module;
- settings theo môi trường và các bước thêm module mới.

Hay tra cứu nhất khi viết code.
Liên quan: [ADR 0018](../adr/0018-one-django-app-per-module.md), [ADR 0007](../adr/0007-events-outbox-celery-no-kafka.md).

### [Các module](./modules/README.md)

Mỗi module một file: sở hữu gì, cây thư mục, sơ đồ quan hệ với module khác, public API (`contracts`, `events`, `exceptions`), quy tắc riêng và job. Luồng checkout nằm ở [`ordering`](./modules/ordering.md#51-luồng-checkout).

## Thiết kế chi tiết

### [03. Mô hình dữ liệu](./03-data-model.md)

ERD của từng module, theo thứ tự `shared`, `identity`, `catalog`, `inventory`, `promotions`, `payments`, `shipping`, `ordering`, `notifications`. Các quy ước chung:

- tên bảng có tiền tố theo module;
- khoá chính `id` dùng UUID;
- tiền lưu bằng `bigint` VND;
- thời gian lưu theo UTC.

Mục cuối mô tả cách ẩn danh dữ liệu khi có yêu cầu xoá dữ liệu cá nhân (CMP-05).
Liên quan: [ADR 0008](../adr/0008-uuid-v7-primary-keys.md), [ADR 0010](../adr/0010-stock-decremented-at-order-awaiting-dispatch.md).

### [04. API contract](./04-api-contract.md)

Quy ước REST chung: có ba gốc URL là `/api/v1/store/`, `/api/v1/backoffice/` và `/api/v1/webhooks/`; phiên bản ghi trên URL; field viết `snake_case`; định dạng tiền và thời gian thống nhất. File còn mô tả cách phân trang, định dạng lỗi và danh sách endpoint theo từng nhóm. OpenAPI được sinh tự động bằng `drf-spectacular`.

### [05. Xác thực và bảo mật](./05-auth-security.md)

NextAuth giữ session phía trình duyệt, còn Django cấp JWT gồm access token 10 phút và refresh token 30 ngày. Các phần chính:

- xoay vòng refresh token và phát hiện token bị dùng lại;
- thu hồi token tức thì;
- tách token của storefront và back-office;
- mật khẩu, phân quyền, throttling, bảo vệ webhook;
- không ghi dữ liệu cá nhân vào log.

Liên quan: [ADR 0002](../adr/0002-auth-nextauth-session-django-jwt.md), [ADR 0009](../adr/0009-nextjs-bff-django-private.md).

### [06. Tích hợp bên ngoài](./06-integrations.md)

Mô hình adapter tự viết bằng `httpx` cho VNPay, MoMo và GHN, vì các bên này không có SDK Python được duy trì. File còn mô tả cách ánh xạ trạng thái GHN, Đối soát chỉ hỏi lại Vận đơn lâu không có cập nhật, rủi ro mở về đối chiếu tiền COD, rủi ro về địa chỉ 2 cấp và 3 cấp, Google OAuth, email, Fake Gateway dùng ở local và test, và quy trình nghiệm thu với sandbox thật.
Liên quan: [ADR 0005](../adr/0005-provider-adapters-fake-gateways.md).

### [07. Sự kiện và job chạy nền](./07-async-events-jobs.md)

Luồng Transactional Outbox: service ghi sự kiện vào PostgreSQL, relay đẩy sự kiện sang Celery, handler xử lý. File ghi rõ cơ chế này bảo đảm gì và không bảo đảm gì, cách retry, cùng danh mục sự kiện, trong đó payload không chứa secret hay PII. Phần Celery mô tả các queue, lịch job của Celery Beat và cấu hình quan trọng.
Liên quan: [ADR 0003](../adr/0003-postgres-redis-celery.md), [ADR 0007](../adr/0007-events-outbox-celery-no-kafka.md).

## Vận hành và hạ tầng

### [08. Môi trường phát triển local](./08-local-development.md)

Cách dựng môi trường trên macOS và trên Windows (không dùng WSL2). PostgreSQL cài trên máy ([ADR 0015](../adr/0015-local-postgres-on-host.md), [ADR 0017](../adr/0017-windows-native-dev-api-on-host.md)); API chạy trên máy bằng `uv run`; worker, beat, relay, Redis (Valkey), Mailpit chạy bằng Docker Compose. File hướng dẫn cài đặt lần đầu, đặt biến môi trường, các lệnh `Makefile` hằng ngày, debug, chạy test và cấu hình VS Code hoặc PyCharm.

### [09. Triển khai trên AWS (mục tiêu)](./09-deployment-aws-target.md)

Kiến trúc đích ở region Singapore, **chưa triển khai**. Thành phần gồm CloudFront kèm WAF, ALB, ECS Fargate (chạy api, worker, beat, relay và Next.js), RDS PostgreSQL Multi-AZ, ElastiCache for Valkey, S3, SES, Secrets Manager. File còn mô tả các môi trường staging và production, quy trình deploy (migration chạy trước, phải tương thích ngược) và lý do beat và relay deploy theo hai cách khác nhau.

### [10. Yêu cầu phi chức năng](./10-nfr.md)

Mục tiêu cho MVP với tải khoảng 500–5.000 đơn/ngày. Gồm hiệu năng (p95 API, tải đỉnh khi có khuyến mãi), độ sẵn sàng (RPO, RTO, hệ thống vẫn chạy khi GHN, cổng thanh toán hoặc Redis lỗi), bảo mật, observability, khả năng mở rộng, chất lượng code và bản địa hoá. Các con số có nhãn **[Giả định · kiểm chứng: …]** sẽ được kiểm bằng test tải và số liệu production.

## Quy trình làm việc

### [11. Quy ước Git](./11-git-workflow.md)

Mô hình nhánh `main`/`uat`/`dev`, cách đặt tên nhánh và commit message theo Conventional Commits (bằng tiếng Anh), CI trên GitHub Actions. File còn mô tả cách merge PR theo từng chặng, quy trình làm tính năng, release và hotfix, cách bảo vệ nhánh, versioning và CHANGELOG, và những thứ không được commit.

### [12. Chiến lược test](./12-testing-strategy.md)

Test chạy trên PostgreSQL thật, chỉ giả lập hệ thống bên ngoài, và kiểm tra nghiệp vụ ở tầng service. Các loại test gồm service, concurrency, handler/outbox, API, auth/JWT, adapter và flow xuyên module. File còn mô tả marker của pytest, dữ liệu test, hợp đồng OpenAPI với frontend, test migration và các cổng chặn trong CI.

### [13. Coding style Python/Django](./13-python-django-coding-style.md)

Nguồn chuẩn duy nhất cho code Python/Django: ngôn ngữ, type hints, ranh giới tầng, transaction, naming,
Ruff/mypy, model và migration, docstring, test, logging và checklist dành cho AI agent. Tài liệu không
định nghĩa style TypeScript/Next.js khi frontend chưa được bootstrap.

### [14. Package dùng và không dùng](./14-dependencies.md)

Vì sao chọn hoặc loại từng package runtime và dev. Phiên bản chính xác ở `pyproject.toml` và `uv.lock`, không chép vào tài liệu.
