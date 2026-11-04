# Phase 4 — review ba trục + vòng sửa

Mục tiêu: code **và test** đúng ticket và đúng chuẩn của repo. Bắt buộc ở mọi mode.

1. **Check máy trước** (rẻ hơn reviewer; output đưa cho reviewer). `make lint` / `make test` đã xanh ở cuối phase 2, không chạy lại:

   ```bash
   python3 S/scripts/state.py check <T>
   python3 S/scripts/check_ac_trace.py <T>
   python3 S/scripts/check_ship.py <T>
   ```

   Lỗi → sửa trước khi review. `WARN ticket chưa commit` là đúng: `report.md` commit ở task `sync`.
2. **Review.** `.git/ship-ticket-fashion/<K>-review.md` đã có đủ trục (làm tiếp sau `/clear` hoặc bị ngắt) → bỏ qua bước này, đọc file đó. Mỗi báo cáo nhận về được ghi ngay vào file dưới heading `## Spec`, `## Standards`, `## Bug`. Xong khi file có đủ ba heading.

   Full: trong cùng một lượt, gọi song song 2a và 2b, brief riêng. Lite: một agent `general-purpose` làm cả ba trục với brief của 2a và 2b.

   **2a. Spec + Standards**: `mattpocock-skills:code-review`, fixed point `origin/dev`; spec là `spec.md` của ticket (gồm `## Quyết định`) cùng `userRequested` trong state (thuộc phạm vi). Nguồn chuẩn: `docs/architecture/13-python-django-coding-style.md`, `CONTRIBUTING.md`, `docs/architecture/02-backend-structure.md`, `docs/architecture/12-testing-strategy.md`, checklist của `.github/pull_request_template.md`. Dặn thêm:
   - **Spec**: "Với mỗi AC, nêu test khẳng định kết quả của nó. Báo AC hoặc nhánh của AC không có test, và test chỉ kiểm mock được gọi thay vì kết quả." Đính kèm output `check_ac_trace.py`.
   - **Standards**: "File test thuộc phạm vi review. Đối chiếu diff với từng mục *Tài liệu chi phối* trong `## Quyết định`; báo chỗ code trái tài liệu mà ticket không ghi lý do. Soát từng gạch đầu dòng của `CONTRIBUTING.md` mục *Quy ước code* trên mọi file test đổi." Có dòng `Interface / seam` → thêm: "Đối chiếu interface mới với dòng đó và áp _deletion test_; báo hàm public chỉ chuyển tiếp lời gọi, và seam chỉ có một adapter mà không ghi lý do."

   **2b. Bug**: một sub-agent `general-purpose`, nhận `git diff origin/dev...HEAD`, danh sách commit, `spec.md` của ticket và `<K>-map.md`. Brief: "Săn lỗi chạy sai mà Spec và Standards không soi: dữ liệu bị bỏ khi ghi, guard an toàn bị lọt, logic viết lại thứ thư viện đã có. Đọc code quanh mỗi hunk và caller của nó. Commit plan đổi dòng `Status:` của ticket đã triage là đúng quy trình. Mỗi finding mã `B1`, `B2`…, kèm `file:line` và kịch bản cụ thể gây sai."

   Dặn chung: báo cáo tiếng Việt, dưới 600 từ, mỗi finding có `file:line` và dòng chuẩn / AC được trích; file tạm ghi vào `.git/ship-ticket-fashion/`, xong thì `git status --short` chỉ còn file của ticket.
3. **Xác minh** finding sẽ đổi code: tự mở dòng được trích trước khi làm; reviewer có thể sai. Finding `B<n>` → `mattpocock-skills:diagnosing-bugs` tới hết phase 1 của skill đó: một test đỏ đúng kịch bản lỗi, chạy qua `run_logged.py --label <K>-R<n>-red` (log là bằng chứng red của vòng sửa). Không dựng được → *chỉ báo*.
4. **Phân loại** mỗi finding:
   - *sửa*: vi phạm chuẩn trong diff; code trái AC hoặc `## Quyết định`; thiếu test hoặc test yếu cho một AC.
   - *hoàn tác*: thứ agent tự thêm ngoài phạm vi (không có AC, không có yêu cầu), kể cả vô hại.
   - *chỉ báo*: smell, lỗi có từ trước, điểm cần người dùng quyết. Mục ngoài phạm vi còn đáng làm → backlog (`reference/rules.md`, *Phạm vi*).

   Trình bảng finding (mã, `file:line`, phân loại, cách sửa) và hỏi bằng `AskUserQuestion` (multi-select) mục nào sửa ngay; mục *sửa* để sẵn là khuyên dùng. Chỉ liệt kê nhóm sửa, không thêm lựa chọn "Không sửa gì": người dùng bỏ hết thì ghi ở Other. Mục trong `userRequested` hỏi trước khi hoàn tác. Ghi lựa chọn vào cuối `<K>-review.md`.
5. **Vòng sửa, tối đa 2 vòng.** Full: gửi cho implementer của phase 2 bằng `SendMessage` (agent đã có context code), kèm đường dẫn `<K>-review.md` và mã finding đã chọn; `ListAgents` không còn agent đó thì tạo mới theo `SKILL.md` → *Sub-agent*. Lite: phiên chính.
   - Vòng 1 làm hết mục đã chọn thành một lô; vòng 2 chỉ xử lý thứ vòng 1 để lại đỏ hoặc làm hỏng.
   - Mục đổi hành vi: test red trước khi sửa.
   - Mỗi vòng một commit: `commit.py <T> --task R1` (vòng 2: `R2`), subject `fix(<scope>): address review findings on <chủ đề>`, thân liệt kê mã finding đã sửa (`B1`, `S2`…).
   - Cuối vòng: `make fmt`, `make lint --keep-going`, `make test`, `check_ac_trace.py`.

   Còn mở sau vòng 2 → đưa lên G2.
6. **Ghi** bảng kết luận vào `report.md` (mục *Review*): mỗi finding một dòng (mã, `file:line`, đã sửa / chỉ báo / hoàn tác / bác, lý do vài chữ); gom smell vào một dòng. Cập nhật bảng AC → bằng chứng nếu test đổi.
7. `state.py transition <T> --to sync --next "đồng bộ tài liệu" --reason "review xong"`, in điểm clear.

## Xong khi

Check máy xanh; `<K>-review.md` có đủ ba trục; mọi finding có kết luận trong báo cáo; tối đa 2 vòng sửa đã chạy và vòng cuối xanh; `phase` là `sync`.
