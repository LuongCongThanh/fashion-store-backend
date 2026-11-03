# Backlog

Việc tốt nhưng ngoài phạm vi ticket, phát hiện khi làm hoặc review. Mỗi việc một dòng: `DD/MM/YYYY · <ticket nguồn> · <việc> · <mốc nên xem lại>`. Việc chặn mốc đang làm hoặc mốc kế tiếp thì thành ticket `needs-triage` và xoá dòng ở đây ([quy tắc](../.claude/skills/ship-ticket-fashion/reference/rules.md)).

- 30/10/2026 · backend-bootstrap/11 · Lease `Idempotency-Key` 60 giây không gia hạn khi tác động chạy lâu · M2 checkout
- 30/10/2026 · backend-bootstrap/11 · `claim` chờ khoá dòng thay vì trả 202 ngay khi worker kia đang commit · M2 checkout
- 30/10/2026 · backend-bootstrap/11 · `scope` vượt `varchar(255)` khi path dài hơn ~175 ký tự → 500 · M3 Thanh toán
- 30/10/2026 · backend-bootstrap/11 · Key `in_progress`, `resource_id` NULL, bị bỏ lại khi worker chết không bao giờ purge (03 §1.5, 07 §3.2 chỉ cho xoá `completed`) · trước go-live
- 30/10/2026 · backend-bootstrap/12 · `Account.objects.get_by_natural_key` khớp email phân biệt hoa thường; luồng đăng nhập phải tra theo email đã chuẩn hoá hoặc `iexact` · M1 identity (JWT login)
- 30/10/2026 · backend-bootstrap/12 · `create_staff --full-name` dài hơn 255 ký tự ném `DataError` thay vì lỗi rõ ràng; kiểm độ dài khi back-office có form tạo Staff · M6 quản lý Staff (US-1001)
- 01/11/2026 · backend-bootstrap/27 · Contract test trong CI: snapshot JSON schema của mỗi `(event_type, schema_version)` đã đăng ký, fail khi thêm/bỏ field bắt buộc của `…V1` (chặn từ gốc lỗi mà consumer chỉ bắt sau deploy) · M1 khi module đầu tiên thêm sự kiện
- 01/11/2026 · backend-bootstrap/23 · Sửa tận gốc lỗi mã hoá trên Windows thay cho đặt `PYTHONUTF8` ở từng entry point (Makefile, hook pre-commit, `env` của test, `run_logged.py`): đặt tên contract import-linter bằng ASCII (cùng `scripts/gen_importlinter.py`), hoặc 08 §2 hướng dẫn đặt `PYTHONUTF8=1` cho cả user · ticket 04
- 01/11/2026 · backend-bootstrap/22 · OpenAPI khai mặc định 401/403 cho view không `AllowAny` và 503 `AUTH_STATE_UNAVAILABLE` cho back-office trong `shared.api.schema.AutoSchema` · M1 identity (JWT login)
- 01/11/2026 · backend-bootstrap/22 · OpenAPI: header `Retry-After` cho 429 và ví dụ (`OpenApiExample`) cho mỗi operation (04 §5.6 đòi ví dụ trước khi frontend dùng) · trước khi frontend sinh TS client
- 01/11/2026 · backend-bootstrap/22 · `AutoSchema` bỏ response lỗi `ErrorDTO` mặc định cho operation webhook/HTML/CSV (04 §5.6) · M3 IPN, M5 xuất CSV
- 01/11/2026 · backend-bootstrap/01 · Test tất định cho nhánh `return` ở `shared/events/consumer.py:121` (thread trùng chen giữa hai transaction): hiện chỉ `test_concurrent_duplicate_dispatch_commits_once` (`shared/events/tests/test_consumer.py:502`) chạm nhánh này nhờ race, khoảng 1/4 lần không chạm, nên cổng coverage nhóm `shared` dao động 66–67/68 · khi nhóm `shared` sát ngưỡng 80% hoặc ticket kế tiếp sửa `shared/events`
- 02/11/2026 · backend-bootstrap/04 · `gen_importlinter.py` sinh `ignore_imports` cho FK model → model của module lớp dưới (02 §6.3, §8), kèm test trên cây package tạm · M1 khi model đầu tiên khai FK chéo module
- 02/11/2026 · backend-bootstrap/04 · Contract import-linter không cấm được re-export phần nội bộ ở `modules/<m>/__init__.py` (cấm package gốc là cấm luôn `contracts`); ghi quy ước "`__init__.py` của module không re-export" vào 02 §6.1 hoặc thêm check riêng · M1 khi làm module đầu tiên
- 02/11/2026 · backend-bootstrap/04 · Hook pre-commit `lint-imports` chưa chạy `gen_importlinter.py --check`, nên contract cũ chỉ bị bắt ở `make lint`/CI · khi có module thứ hai có phần nội bộ
- 03/11/2026 · backend-bootstrap/19 · Trả `X-Request-ID` trong response (receiver `bind_extra_request_finished_metadata` + `update_failure_response`) để BFF/browser đối chiếu khi không có body lỗi; sửa 04 và 10 §4 · khi Next.js BFF cần hiển thị mã tra cứu cho mọi response
- 03/11/2026 · backend-bootstrap/26 · `OutboxEvent.mark_listed(ids, *, now)`: ghi marker `deliveries_created_at` trong `relay.create_deliveries` qua model, cạnh `listed()`/`unlisted()` · khi làm ticket 28 (B5 sửa vị từ `listed` cạnh index)
