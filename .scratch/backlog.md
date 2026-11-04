# Backlog

Việc tốt nhưng ngoài phạm vi ticket, phát hiện khi làm hoặc review. Mỗi việc một dòng: `DD/MM/YYYY · <ticket nguồn> · <việc> · <mốc nên xem lại>`. Việc chặn mốc đang làm hoặc mốc kế tiếp thì thành ticket `needs-triage` và xoá dòng ở đây ([quy tắc](../.claude/skills/ship-ticket-fashion/reference/rules.md)).

- 30/10/2026 · backend-bootstrap/11 · Lease `Idempotency-Key` 60 giây không gia hạn khi tác động chạy lâu · M2 checkout
- 30/10/2026 · backend-bootstrap/11 · `claim` chờ khoá dòng thay vì trả 202 ngay khi worker kia đang commit · M2 checkout
- 30/10/2026 · backend-bootstrap/11 · `scope` vượt `varchar(255)` khi path dài hơn ~175 ký tự → 500 · M3 Thanh toán
- 30/10/2026 · backend-bootstrap/11 · Key `in_progress`, `resource_id` NULL, bị bỏ lại khi worker chết không bao giờ purge (03 §1.5, 07 §3.2 chỉ cho xoá `completed`) · trước go-live
- 30/10/2026 · backend-bootstrap/12 · `create_staff --full-name` dài hơn 255 ký tự ném `DataError` thay vì lỗi rõ ràng; kiểm độ dài khi back-office có form tạo Staff · M6 quản lý Staff (US-1001)
- 01/11/2026 · backend-bootstrap/23 · Sửa tận gốc lỗi mã hoá trên Windows thay cho đặt `PYTHONUTF8` ở từng entry point (Makefile, hook pre-commit, `env` của test, `run_logged.py`): đặt tên contract import-linter bằng ASCII (cùng `scripts/gen_importlinter.py`), hoặc 08 §2 hướng dẫn đặt `PYTHONUTF8=1` cho cả user · ticket 04
- 01/11/2026 · backend-bootstrap/22 · `AutoSchema` bỏ response lỗi `ErrorDTO` mặc định cho operation webhook/HTML/CSV (04 §5.6) · M3 IPN, M5 xuất CSV
- 01/11/2026 · backend-bootstrap/01 · Test tất định cho nhánh `return` ở `shared/events/consumer.py:121` (thread trùng chen giữa hai transaction): hiện chỉ `test_concurrent_duplicate_dispatch_commits_once` (`shared/events/tests/test_consumer.py:502`) chạm nhánh này nhờ race, khoảng 1/4 lần không chạm, nên cổng coverage nhóm `shared` dao động 66–67/68 · khi nhóm `shared` sát ngưỡng 80% hoặc ticket kế tiếp sửa `shared/events`
- 02/11/2026 · backend-bootstrap/04 · Hook pre-commit `lint-imports` chưa chạy `gen_importlinter.py --check`, nên contract cũ chỉ bị bắt ở `make lint`/CI · khi có module thứ hai có phần nội bộ
- 03/11/2026 · backend-bootstrap/19 · Trả `X-Request-ID` trong response (receiver `bind_extra_request_finished_metadata` + `update_failure_response`) để BFF/browser đối chiếu khi không có body lỗi; sửa 04 và 10 §4 · khi Next.js BFF cần hiển thị mã tra cứu cho mọi response
- 03/11/2026 · backend-bootstrap/26 · `OutboxEvent.mark_listed(ids, *, now)`: ghi marker `deliveries_created_at` trong `relay.create_deliveries` qua model, cạnh `listed()`/`unlisted()` · khi làm ticket 28 (B5 sửa vị từ `listed` cạnh index)
- 04/11/2026 · m1-catalog-inventory/01 · `shared/api/permissions.py` `IsStaff`/`IsAdmin`/`IsCustomer` viết cứng audience; đọc từ settings (`JWT_AUDIENCE_BACKOFFICE` và setting audience `store` mới) để đổi env không làm `/me` trả 403 · khi thêm JWT storefront (M6) hoặc khi đổi audience
