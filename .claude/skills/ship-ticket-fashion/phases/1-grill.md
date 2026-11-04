# Phase 1 — grill + ⛔G1

Mục tiêu: mỗi acceptance criterion có seam và tên test, mỗi lựa chọn mở có quyết định, môi trường chạy được test.

1. **Nhánh.** Gặp *Cần người dùng* thì dừng ở đó.
   - `git status --short` còn thay đổi của việc khác → *Cần người dùng*.
   - `gh pr list --head <nhánh hiện tại> --state open` (tài khoản ở `phases/6-ship.md`). Còn PR mở → hỏi: merge PR đó trước (khuyên dùng khi ticket mới cần code của nó), hay tách nhánh từ `origin/dev` luôn.
   - `git fetch origin`, từ `origin/dev` tạo `<type>/<mô-tả-ngắn>` (`docs/architecture/11-git-workflow.md` mục 2).

   Xong khi `git branch --show-current` là nhánh mới và working tree chỉ còn file của ticket.
2. **Baseline.** Cờ `NO HOOKS` → hỏi rồi chạy `uv run pre-commit install` trong `backend/`. Chạy `make test` với `--label baseline` (`reference/rules.md` → *Check máy*); không dùng `manage.py check` thay, vì lệnh đó xanh cả khi DB hỏng. Lỗi kết nối DB, Redis hoặc thiếu biến môi trường → *Cần người dùng*: nhờ sửa `backend/.env` theo `.env.example` (agent không đọc `.env`) hoặc bật service (`make up`), rồi chạy lại. Test đỏ vì lý do khác là đỏ sẵn trên `origin/dev`: ghi id vào `notes.baselineRed` ở bước 3. Xong khi baseline xanh hoặc mọi test đỏ đã có trong `notes.baselineRed`.
3. **State.** `python3 S/scripts/state.py init <T> --branch <nhánh> --mode full` (mode tạm, G1 chốt). Read `reference/state.md`.
4. **Nguồn.** Read ticket, `spec.md` của feature, tài liệu và ADR ticket trỏ tới, `GLOSSARY.md`. Ticket chạm quy tắc nghiệp vụ → thêm `docs/business/04-business-rules.md`, `05-order-lifecycle.md`. Test: tra `docs/architecture/12-testing-strategy.md` theo cả loại test lẫn chủ đề ticket chạm (log, DB, cache, fixture).
5. **Bản đồ code** (sub-agent `Explore`). Brief: code ticket sửa hoặc gọi (file, chữ ký, số dòng), caller, test và fixture dùng lại được, ticket bị ticket này chặn (`Blocked by` trỏ về nó) để chốt API khớp chỗ dùng sau. Ticket bọc việc một thư viện đã làm (đồng bộ lịch, migrate, xác thực…) → `mattpocock-skills:research` tra tài liệu gốc đúng phiên bản trong `backend/uv.lock`, ghi `.scratch/<feature>/research/<chủ-đề>.md`.
   Phiên chính ghi kết quả vào `.git/ship-ticket-fashion/<K>-map.md` (≤ 150 dòng: file → chữ ký / dòng → vai trò; test, fixture, hàm thư viện dùng lại), rồi tra `docs/architecture/README.md` tìm *tài liệu chi phối* của từng file sẽ đổi và đọc đúng các mục đó. Xong khi bản đồ có mọi file sẽ đổi.
6. **Grilling.** `mattpocock-skills:grilling` trong phạm vi ticket: chốt lựa chọn còn mở và các _seam_ sẽ test. Lite: chỉ hỏi phần ticket và tài liệu chưa trả lời.
   - Code chuyển ra khỏi một `except` rộng (của handler, của transaction): liệt kê mọi exception nó từng được bắt ở đó và chốt nơi mỗi loại rơi vào sau khi chuyển.
   - **Interface public** (thêm hoặc đổi hàm public trong `contracts.py`, `services`, `selectors` của module, hoặc của `shared/`) → thêm `mattpocock-skills:codebase-design`: _deletion test_ và "một adapter = seam giả định" cho từng interface. `contracts.py` đầu tiên của một module → thêm *design-it-twice*, tối đa 3 phương án, so ở G1.
7. **`## Quyết định`** trong `spec.md` của ticket, đặt trước `## Acceptance criteria`: dòng `Chốt khi grilling ngày DD/MM/YYYY.`, rồi bảng Chủ đề | Quyết định gồm dòng `Tài liệu chi phối` (reference máy đọc: `docs/architecture/13-python-django-coding-style.md::3.1`, `docs/adr/0007-events-outbox-celery-no-kafka.md`), dòng `Interface / seam` nếu có, và mọi chỗ khác *Việc cần làm* kèm lý do. Model và test tham chiếu mục tên / đường dẫn test; test thêm mục factory và tài liệu sở hữu kịch bản.
8. **Slice** (schema ở `reference/state.md`). Chia AC thành slice dọc (lite: một slice), mỗi slice một commit:
   - `acs`, `seam`, `dependsOn`.
   - `files`: chỉ file thật sự sửa; `commit.py` từ chối commit khi thiếu hoặc thừa file. Hành vi đổi → `rg -n "<trạng thái / field bị ảnh hưởng>" docs`, đưa code, test, sơ đồ, kịch bản liên quan vào.
   - `tddTests` + `expectedRed`: `AssertionError` hoặc exception nghiệp vụ; lỗi setup / hạ tầng không hợp lệ. Method chưa tồn tại → khai chữ ký raise `NotImplementedError` trước, để red không thành `AttributeError`. I/O phá huỷ được test ở seam bằng kết nối giả.
   - `verificationTests`: test sẵn có chỉ cần green; id luôn ở cấp hàm (`file.py::test_x`).
   - `governingDocs`: file → `đường/dẫn.md::số-mục` (ADR áp dụng cả file bỏ được `::`); cùng reference phải có trong dòng `Tài liệu chi phối`.
   - AC không test tự động được → `untestable` kèm cách kiểm tay.

   Xong khi mỗi AC thuộc đúng một slice hoặc nằm trong `untestable`.
9. **Plan.** Push nguyên slice trong một lần, rồi chạy `state.py check <T>`, `check_ac_trace.py <T> --planned`, `plan.py <T>`. Slice đổi sau G1 → cập nhật state, sinh lại plan trước khi code. Xong khi cả ba xanh.
10. **⛔G1** (khuôn ở `SKILL.md` → *Gate*). Tóm tắt: `plan.md`; tài liệu chi phối; quyết định mới; file sẽ đổi (đánh dấu `backend/shared/`); mode; AC `untestable`; test trong `notes.baselineRed`. Hỏi duyệt slice và mode cùng các quyết định còn mở.
11. **Duyệt xong.** Commit *spec* + *plan* (và dòng `Status:` đã triage), chuyển phase, in điểm clear:

    ```bash
    python3 S/scripts/commit.py <T> --task plan -m "docs: plan <chủ đề> ticket" -- <thư mục ticket> [<spec.md của ticket đã triage>…]
    python3 S/scripts/state.py transition <T> --to code --gate g1 --next "S1: viết test red đầu tiên" --reason "G1 approved"
    ```

## Xong khi

Baseline đã chạy; `<K>-map.md` có mọi file sẽ đổi; mọi AC nằm trong một slice hoặc `untestable`; mọi file sẽ đổi có tài liệu chi phối, mọi lựa chọn mở có dòng trong `## Quyết định`; `state.py check` và `check_ac_trace.py --planned` xanh; commit `Task: plan` đã có; `gates.g1` có ngày và `phase` là `code`.
