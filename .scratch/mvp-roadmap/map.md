# Roadmap MVP

Thứ tự làm backend cho MVP, theo các lát dọc: mỗi mốc chạy được từ đầu tới cuối và có test flow riêng, không làm xong từng module theo lớp rồi mới ghép. Mỗi mốc là một thư mục `.scratch/<slug>/` có `spec.md` và ticket ([issue-tracker](../../docs/agents/issue-tracker.md)). Chỉ M0 đã có spec; các mốc sau tạo spec khi mốc trước gần xong, để spec dựa trên code đã có.

## Notes

| Mốc | Thư mục | Nội dung | User story | Xong khi |
|---|---|---|---|---|
| **M0** | [`backend-bootstrap`](../backend-bootstrap/spec.md) | Khung Django, `shared` (BaseModel, events/outbox, idempotency, API cơ sở, địa giới), Docker Compose, CI, các cổng chặn | — | `make up`, `make lint`, `make test` xanh ở local và CI; test flow outbox (publish → relay → handler) qua |
| **M1** | `catalog-inventory` | identity lõi (Account, JWT login/refresh/logout cho cả hai nhánh, ADR 0002/0014), catalog (Danh mục, Sản phẩm, Biến thể, size, màu, ảnh, Giá khuyến mãi), inventory (StockItem, Nhập kho, điều chỉnh, Kiểm kê), storefront đọc và tìm kiếm | US-101 → 104, 701 → 703, 801 → 805 | Admin tạo được Sản phẩm, Staff nhập kho, storefront lọc/tìm đúng BR-CAT-13 |
| **M2** | `checkout-cod` | Giỏ hàng, Voucher, báo giá phí ship qua Fake GHN, Tính thử + `quote_token`, checkout COD, email "Đặt đơn thành công", cấu hình vận hành | US-201 → 204, 301 → 305, 307, 308, 901, 1002 | Test concurrency hai Người mua cùng mua Biến thể cuối cùng qua; flow COD tạo đơn `PLACED` và EmailLog |
| **M3** | `online-payment` | Thanh toán online qua Fake Gateway, IPN, khởi tạo có thể khôi phục (ADR 0013), Đối soát, T3/T4/T5, tiền về sai số tiền hoặc cho đơn không còn chờ thanh toán, Hoàn tiền `requested` | US-306, 403, 608 | Flow online thành công, hết hạn, trả hai lần, sai số tiền đều qua với Fake Gateway |
| **M4** | `order-fulfillment` | Back-office xử lý đơn T6 → T14, Bàn giao và Vận đơn qua Fake GHN, webhook GHN, Cờ cần xử lý, xác nhận nhập lại kho, Khách vãng lai tra cứu, lịch sử đơn | US-401, 402, 601 → 604, 607, 609, 1004 | Flow checkout → giao → Hoàn tất (T13) chạy hết bằng Fake provider |
| **M5** | `returns-refunds` | Đổi trả theo dòng, Hoàn tiền thủ công, báo cáo Doanh thu, xuất đơn đã thu tiền | US-605, 606, 1003 | Ví dụ làm tròn ở BR-RET-07 và BR-REV-01 thành test qua |
| **M6** | `identity-privacy` | Đăng ký (US-501 AC2 không lộ email), xác thực email, Google, quên mật khẩu, hồ sơ, sổ địa chỉ, gắn đơn vãng lai, quản lý Staff, Yêu cầu xoá dữ liệu (ADR 0016), log truy cập | US-501 → 506, 1001, 1101, 1102 | Flow ẩn danh hoàn tất chỉ khi mọi handler bắt buộc `completed`; không còn số điện thoại thô trong bằng chứng |
| **M7** | `sandbox-acceptance` | Nghiệm thu VNPay, MoMo, GHN sandbox qua tunnel ([06 mục 8](../../docs/architecture/06-integrations.md#8-nghiệm-thu-với-sandbox-thật-trước-khi-lên-aws)), test tải k6 (ticket [01](../sandbox-acceptance/issues/01-load-test-k6-staging/spec.md)), danh sách go-live ([06-compliance mục 6](../../docs/business/06-compliance.md#6-điều-kiện-go-live)) | — | Mọi mục **[Cần xác minh]** đã gỡ hoặc có quyết định ghi lại |

M1 có identity lõi vì endpoint back-office của catalog và inventory cần xác thực Staff/Admin. Các luồng còn lại của identity để tới M6, vì checkout của Khách vãng lai không cần Tài khoản.

## Tiến độ

Cập nhật trong cùng PR đóng ticket. Nguồn sự thật là dòng `Status:` và `Ưu tiên:` của từng ticket; bảng này chỉ để nhìn nhanh, ticket mở xếp theo `Ưu tiên`. Ngày và PR ở [`ticket-history.md`](../../docs/agents/ticket-history.md).

| Ưu tiên | Mốc / feature | Ticket mở | Ghi chú |
|---|---|---|---|
| 1 | [`dev-security-baseline`](../dev-security-baseline/spec.md) | 🟡 03 | Chủ repo tự kiểm tra 3 AC; 01, 02 ✅ |
| 2–4 | [`one-app-per-module`](../one-app-per-module/spec.md) | ⬜ 01 → 02 → 03 | Chặn M1 02–04 |
| 5–15 | **M1** [`catalog-inventory`](../catalog-inventory/spec.md) | ⬜ 02, 03, 04, 05, 07, 06, 08, 09, 10, 11, 12 | 03 và 04 làm song song được; 01, 13 ✅ |
| 16–17 | **M0** [`backend-bootstrap`](../backend-bootstrap/spec.md) | ⬜ 14, 20 | Cần chủ repo sửa ruleset; làm xen kẽ |
| 18–20 | **M0** [`backend-bootstrap`](../backend-bootstrap/spec.md) | ⏸ 28 → 25, 13 | Trước go-live; mốc chính M0 đã xong (23 ticket ✅) |
| 21 | **M7** [`sandbox-acceptance`](../sandbox-acceptance/issues/01-load-test-k6-staging/spec.md) | ⏸ 01 k6 | `needs-triage`, chờ M2 và staging |
| — | **M2** – **M6** | — | Tạo spec khi mốc trước gần xong |

Ký hiệu: ✅ `resolved` · 🟡 đang dở · ⬜ chưa làm · ⏸ để sau.

## Decisions-so-far

### Quy tắc chung

- 29/10/2026: Tài liệu `docs/` chốt cho MVP; code tới đâu cập nhật tài liệu tới đó trong cùng PR ([README](../../README.md#trạng-thái-tài-liệu)).
- 29/10/2026: Python 3.14, bỏ `uuid-utils` ([ADR 0008](../../docs/adr/0008-uuid-v7-primary-keys.md)).
- 29/10/2026: Con số nghiệp vụ `[Giả định]` đã chốt; con số kỹ thuật mang nhãn `[Giả định · kiểm chứng: …]`.
- 29/10/2026: Đăng ký luôn trả `202` như nhau, không lộ email đã tồn tại (US-501 AC2).
- 29/10/2026: Bằng chứng tuân thủ giữ HMAC số điện thoại sau ẩn danh ([ADR 0016](../../docs/adr/0016-erasure-evidence-phone-hmac.md)).
- 29/10/2026: Hoá đơn điện tử xuất thủ công ở MVP; kế toán xác nhận trước go-live.
- 29/10/2026: Không dùng Django Admin ở mọi môi trường ([ADR 0004](../../docs/adr/0004-custom-nextjs-admin.md)).
- 29/10/2026: Biến môi trường và lệnh `Makefile` thêm ở mốc dùng tới, không khai báo trước ([08](../../docs/architecture/08-local-development.md) mục 2.3, 3).
- 30/10/2026: Ticket sinh ra từ review không chặn mốc đang làm: đưa vào backlog làm xen kẽ hoặc để trước go-live. Lý do: M0 phình từ 4 lên 27 ticket vì mỗi review sinh ticket mới.
- 03/11/2026: `backend/openapi.yaml` là hợp đồng API đã commit; đổi endpoint hoặc serializer thì chạy `make openapi` và commit cùng PR ([03](../backend-bootstrap/issues/03-openapi-schema-drift-check/spec.md)).
- 02/11/2026: Contract import-linter đặt tên ASCII tiếng Anh; contract `forbidden` do `scripts/gen_importlinter.py` sinh, không sửa tay ([04](../backend-bootstrap/issues/04-import-linter-test-factories/spec.md)).
- 05/11/2026: Mỗi ticket mở có `Ưu tiên: N` đánh liên tục qua mọi feature ([issue-tracker](../../docs/agents/issue-tracker.md#thứ-tự-ưu-tiên)). Kế hoạch M1 chuyển về `.scratch/catalog-inventory/`, kế hoạch 8 module chuyển về [`module-plan.md`](module-plan.md).

### API nền mà module sau phải dùng

Mỗi dòng: ticket chốt gì; chi tiết ở mục `## Quyết định` của ticket.

- [09](../backend-bootstrap/issues/09-shared-core/spec.md#quyết-định): API `shared` (keyring, `Money`, `DomainError.http_status`, `redact_pii`, manager giữ `updated_at`).
- [16](../backend-bootstrap/issues/16-shared-api-layer/spec.md#quyết-định): `shared.api` (`page_size` tối đa 100, 405 `METHOD_NOT_ALLOWED`, mặc định `IsAuthenticated`, tối đa 2 `BFF_SHARED_SECRET`, throttle theo `pii_hmac(client_ip)`).
- [19](../backend-bootstrap/issues/19-trust-upstream-request-id/spec.md#quyết-định): chỉ `bff_secret_matches(request)` so `X-BFF-Secret`; `X-Request-ID` từ BFF chỉ tin khi secret đúng.
- [15](../backend-bootstrap/issues/15-docker-compose-local/spec.md): Compose có service `migrate` chạy trước app; lệnh `reset_db` cho `make db-reset`.
- [17](../backend-bootstrap/issues/17-shared-geo/spec.md#quyết-định): mã địa giới theo Cục Thống kê, giữ số 0 đầu; FK `ward_code` dùng dạng này.
- [10](../backend-bootstrap/issues/10-shared-events-outbox/spec.md#quyết-định): `publish` chỉ trong `transaction.atomic`; `@handles(…, name=…)` bắt buộc `name`; `enqueue_on_commit`; flow test dùng `drain_events()`.
- [18](../backend-bootstrap/issues/18-outbox-operations/spec.md#quyết-định): `delivery_lag()`, `get_delivery_outcomes()`; lệnh `retry_failed_events`, `replay_events`; Beat `purge_old_outbox_events` 03:30.
- [27](../backend-bootstrap/issues/27-outbox-invalid-payload-fails-fast/spec.md#quyết-định): payload sự kiện sai thì delivery `failed` ngay, không retry; sửa `…V1` lỡ phá vỡ thì đưa về hình dạng cũ.
- [26](../backend-bootstrap/issues/26-outbox-refactor-smells/spec.md#quyết-định): chuyển trạng thái là method trên model (`save(update_fields)`, nhận `now`, không log); QuerySet chỉ chứa vị từ, cạnh `Meta.indexes` (13 mục 7.1).
- [11](../backend-bootstrap/issues/11-shared-idempotency/spec.md): lõi idempotency ở `shared/idempotency.py`, không import DRF; service gọi `claim.complete()` trong transaction của mình.
- [12](../backend-bootstrap/issues/12-account-bootstrap/spec.md#quyết-định): `Account`, `create_staff_account(...)` với lỗi `InvalidEmail`/`WeakPassword`/`EmailAlreadyUsed`.
- [22](../backend-bootstrap/issues/22-openapi-error-responses/spec.md#quyết-định): `AutoSchema` tự thêm `ErrorDTO` 400/500/429/404; view chỉ khai mã đặc thù.
- [23](../backend-bootstrap/issues/23-makefile-utf8-output/spec.md): entry point mới in tiếng Việt ra pipe phải đặt `PYTHONUTF8=1`.
- [01](../backend-bootstrap/issues/01-services-coverage-gate/spec.md): branch coverage ≥ 80% cho `services/` + `handlers.py` từng module và nhóm hạ tầng `shared`.
- [M1/01](../catalog-inventory/issues/01-backoffice-login/spec.md#quyết-định): view back-office tự khai `JWTAuthentication` + `IsStaff`/`IsAdmin`; fixture `staff_client`/`admin_client` dùng token thật; `AutoSchema` thêm 401/403/503.
- [M1/13](../catalog-inventory/issues/13-openapi-docs-quality/spec.md#quyết-định): chỉ `JSONParser`; tag `<store|backoffice> · <module>` tự suy; mỗi operation cần `summary` và ví dụ tiếng Anh; `gen_openapi.py --check` chặn thiếu.

## Fog

Các mục phụ thuộc bên ngoài, gắn vào mốc cần chúng. Không mục nào chặn M0.

| Mục | Nguồn | Mốc cần |
|---|---|---|
| Container gọi được PostgreSQL trên host: Windows (bộ cài EDB; đã xác minh 2026-10-29, không cần sửa `pg_hba.conf`) | [08](../../docs/architecture/08-local-development.md), ticket [08](../backend-bootstrap/issues/08-local-postgres-installer/spec.md) | M0 |
| Container gọi được PostgreSQL trên host: macOS | [08](../../docs/architecture/08-local-development.md), ticket [13](../backend-bootstrap/issues/13-local-postgres-installer-macos/spec.md) | Khi có người dùng Mac, không chặn mốc nào |
| Tham số, mã kết quả, chữ ký hiện hành của VNPay và MoMo | [06 mục 2–3](../../docs/architecture/06-integrations.md) | M3 (Fake theo tài liệu), M7 (sandbox) |
| GHN: địa chỉ 2 cấp, cơ chế xác thực webhook, chống trùng `client_order_code` | [06 mục 4](../../docs/architecture/06-integrations.md#4-ghn), [04 mục 4.3](../../docs/architecture/04-api-contract.md#43-webhook-apiv1webhooks) | M4 (Fake), M7 (sandbox); US-1004 bỏ được nếu GHN đã dùng 2 cấp |
| Cổng thanh toán có yêu cầu IP server cố định | [09](../../docs/architecture/09-deployment-aws-target.md) | Trước khi lên AWS |
| Pháp lý: dữ liệu cá nhân, hoá đơn điện tử, thông báo Bộ Công Thương, thời hạn lưu payload | [06-compliance](../../docs/business/06-compliance.md#6-điều-kiện-go-live) | Go-live |
