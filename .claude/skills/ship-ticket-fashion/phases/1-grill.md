# Phase 1 — grill + ⛔G1

Mục tiêu: hiểu ticket tới mức mỗi acceptance criterion có seam và tên test, mỗi lựa chọn mở có quyết định.

1. **Chuẩn bị nhánh và máy.** Làm lần lượt; mục nào gặp *Cần người dùng* thì dừng ở đó.
   - **1a. Việc dở.** `git status --short`: còn thay đổi chưa commit của việc khác → *Cần người dùng*. Xong khi working tree sạch hoặc chỉ còn file của ticket này.
   - **1b. PR của nhánh hiện tại.** `gh pr list --head <nhánh hiện tại> --state open` (tài khoản ở `phases/6-ship.md`). Còn PR mở → hỏi: merge PR đó trước (khuyên dùng khi ticket mới cần code của nó), hay tách nhánh mới từ `origin/dev` luôn. Xong khi người dùng đã chọn hoặc không có PR mở.
   - **1c. Nhánh.** `git fetch origin`, rồi từ `origin/dev` tạo `<type>/<mô-tả-ngắn>` (`docs/architecture/11-git-workflow.md` mục 2; ví dụ `feat/shared-api-layer`). Xong khi `git branch --show-current` là nhánh mới.
   - **1d. Hook và DB.** Cờ `NO HOOKS` (`state.py start`) → hỏi người dùng rồi chạy `uv run pre-commit install` trong `backend/`, để gitleaks, ruff và mypy chạy ở mỗi commit thay vì đợi CI. Rồi trong `backend/` chạy `uv run python manage.py check --database default`: lỗi kết nối → *Cần người dùng*, nhờ sửa `DATABASE_URL` trong `backend/.env` theo dạng của `.env.example` (agent không đọc `.env`). Xong khi lệnh `check` xanh.
2. **State.** `python3 S/scripts/state.py init <T> --branch <nhánh> --mode full` (mode tạm, G1 chốt). Đọc `reference/state.md`.
3. **Nguồn.** Đọc ticket, `spec.md` của feature, mọi tài liệu và ADR ticket trỏ tới, `GLOSSARY.md`. Ticket chạm quy tắc nghiệp vụ → thêm `docs/business/04-business-rules.md`, `05-order-lifecycle.md`. Vị trí test, marker, fixture: `docs/architecture/12-testing-strategy.md`. Sau bản đồ code (bước 4), tra `docs/architecture/README.md` để tìm *tài liệu chi phối* (`reference/rules.md`) của từng file sẽ đổi, đọc đúng các mục đó.
4. **Bản đồ code** (sub-agent `Explore`, full): code hiện có mà ticket sửa hoặc gọi, và ticket nào bị ticket này chặn (`Blocked by` trỏ về nó) để chốt API cho đúng chỗ dùng sau này. Ticket bọc việc một thư viện bên thứ ba đã làm (đồng bộ lịch, migrate, xác thực…) → `mattpocock-skills:research` tra tài liệu gốc của thư viện (đúng phiên bản trong `backend/uv.lock`) tìm hàm làm sẵn việc đó, ghi vào `.scratch/<feature>/research/<chủ-đề>.md`; grilling chốt dùng lại hay tự viết và vì sao, dòng `## Quyết định` trỏ tới file research. Kết quả: danh sách file sẽ đổi, chữ ký sẽ thêm, hàm thư viện dùng lại được.
5. **Grilling.** `mattpocock-skills:grilling` trong phạm vi ticket: chốt lựa chọn còn mở và các _seam_ sẽ test. Code chuyển ra khỏi một `except` rộng (`except Exception` của handler, của transaction): liệt kê mọi exception nó từng được bắt ở đó và chốt nơi mỗi loại rơi vào sau khi chuyển. Lite: chỉ hỏi phần mà ticket và tài liệu chưa trả lời.
   **Interface public** (ticket thêm hoặc đổi hàm public trong `contracts.py`, `services`, `selectors` của một module, hoặc interface public của `shared/`): thêm `mattpocock-skills:codebase-design`. Mỗi interface qua _deletion test_ và quy tắc "một adapter = seam giả định"; kết quả thành dòng `Interface / seam` trong `## Quyết định`. Ticket tạo `contracts.py` đầu tiên của một module: thêm *design-it-twice* của skill đó, tối đa 3 phương án, so sánh ở G1.
6. **Ghi quyết định** vào `spec.md` của ticket, mục `## Quyết định` đặt trước `## Acceptance criteria`: dòng đầu `Chốt khi grilling ngày DD/MM/YYYY.`, rồi bảng Chủ đề | Quyết định. Dòng `Tài liệu chi phối` dùng đúng reference máy đọc được (`docs/architecture/13-python-django-coding-style.md::3.1`, `docs/adr/0007-events-outbox-celery-no-kafka.md`). Model và test luôn tham chiếu mục tên/đường dẫn test; test thêm mục factory và tài liệu sở hữu kịch bản. Quyết định khác *Việc cần làm* thì ghi rõ khác ở đâu và vì sao.
7. **Thiết kế slice.** Chia AC thành slice dọc (lite: một slice). Mỗi slice là một commit và khai báo `acs`, `seam`, `files`, `dependsOn`. Hành vi đổi thì `rg -n "<trạng thái hoặc field bị ảnh hưởng>" docs`; đưa code, test, sơ đồ và kịch bản liên quan vào `files`. Xong khi mỗi AC có đúng chỗ thực hiện hoặc nằm trong `untestable` kèm cách kiểm tay.
8. **Thiết kế bằng chứng.** `tests` là hợp không trùng của `tddTests` (test mới phải red/green) và `verificationTests` (test sẵn có chỉ cần green). Mỗi `tddTests` có `expectedRed` là `AssertionError` hoặc exception nghiệp vụ dự kiến; lỗi setup/hạ tầng không hợp lệ. I/O phá huỷ được test ở seam bằng kết nối giả. Xong khi mỗi AC tự động có test id và loại bằng chứng rõ ràng.
9. **Ánh xạ tài liệu.** `governingDocs` ánh xạ từng file tới reference `đường/dẫn.md::số-mục`, ví dụ `docs/architecture/13-python-django-coding-style.md::9`; ADR áp dụng toàn file có thể bỏ `::`. Ghi cùng reference vào dòng `Tài liệu chi phối` của `## Quyết định`. Xong khi file và heading đều tồn tại, mọi file có ít nhất một reference.
10. **Ghi plan.** Push nguyên slice trong một lần, chạy `state.py check <T>`, `check_ac_trace.py <T> --planned`, rồi `plan.py <T>`. Slice đổi sau G1 thì cập nhật state và sinh lại plan trước khi code/commit. Xong khi cả ba lệnh xanh và `plan.md` hiển thị AC → seam → loại test → file/tài liệu → dependency.
11. **⛔G1** (khuôn ở SKILL.md → *Gate*). Tin tóm tắt: `plan.md`; tài liệu chi phối; quyết định mới; file sẽ đổi (đánh dấu `backend/shared/`); mode; AC `untestable`. Hỏi duyệt slice và mode, cùng các quyết định còn mở.
12. **Duyệt xong.** Commit *spec* + *plan* (và dòng `Status:` đã triage), rồi chuyển phase; script từ chối khi spec/plan/state không khớp hoặc chưa commit:

   ```bash
   python3 S/scripts/commit.py <T> --task plan -m "docs: plan <chủ đề> ticket" -- <thư mục ticket> [<spec.md của ticket đã triage>…]
   python3 S/scripts/state.py transition <T> --to code --gate g1 --next "S1: viết test red đầu tiên" --reason "G1 approved"
   ```

   In điểm clear.

## Xong khi

Mọi AC nằm trong một slice hoặc trong `untestable`; mọi file sẽ đổi có tài liệu chi phối và mọi lựa chọn mở có dòng trong `## Quyết định`; `plan.md` khớp state và commit `Task: plan` đã có; `state.py check` và `check_ac_trace.py --planned` xanh; `gates.g1` có ngày và `phase` là `code`.
