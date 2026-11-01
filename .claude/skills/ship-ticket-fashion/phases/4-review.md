# Phase 4 — review ba trục + vòng sửa

Mục tiêu: code **và test** đúng ticket và đúng chuẩn của repo. Bắt buộc ở mọi mode.

1. **Check máy trước** (rẻ hơn reviewer; output của chúng đưa cho reviewer):

   ```bash
   python S/scripts/state.py check <T>
   python S/scripts/check_ac_trace.py <T>
   python S/scripts/check_ship.py <T>
   ```

   `make lint` đã gồm `ruff`, `mypy`, `lint-imports` (ranh giới module). Lỗi → sửa trước khi review. `check_ship.py` báo `WARN ticket chưa commit` là đúng: `report.md` commit ở task `sync`.
2. **Review.** `mattpocock-skills:code-review` với fixed point `origin/dev`, spec là `spec.md` của ticket (mục `## Quyết định` là một phần của spec) cùng `userRequested` trong state (thuộc phạm vi, không phải lan man). Nguồn chuẩn: `CONTRIBUTING.md`, `docs/architecture/02-backend-structure.md`, `docs/architecture/12-testing-strategy.md`, checklist trong `.github/pull_request_template.md`. Dặn thêm:
   - trục **Spec**: "Với mỗi AC, nêu test khẳng định kết quả của nó. Báo AC hoặc nhánh của AC không có test, và test chỉ kiểm mock được gọi thay vì kết quả." Đính kèm output `check_ac_trace.py`.
   - trục **Standards**: "File test thuộc phạm vi review. Đối chiếu diff với từng mục *Tài liệu chi phối* trong `## Quyết định`; báo chỗ code trái tài liệu mà ticket không ghi lý do. Soát từng gạch đầu dòng của `CONTRIBUTING.md` mục *Quy ước code* trên mọi file test đổi (`pytest.raises`, thứ tự assert)." `## Quyết định` có dòng `Interface / seam` → thêm: "Đối chiếu interface mới với dòng đó và áp _deletion test_; báo hàm public chỉ chuyển tiếp lời gọi, và seam chỉ có một adapter mà không ghi lý do."
   - cả hai báo cáo tiếng Việt, dưới 600 từ, mỗi finding có `file:line` và dòng chuẩn / AC được trích.
   - mọi reviewer ghi file tạm (schema sinh ra, output lệnh) vào `.git/ship-ticket-fashion/`; ba trục xong thì `git status --short` chỉ còn file của ticket.
   - trục **Bug**: skill `code-review` dựng sẵn của Claude Code (khác `mattpocock-skills:code-review`), `args: "high <nhánh>, so với origin/dev; commit plan đổi dòng Status: của ticket đã triage là đúng quy trình"` (không nêu gốc thì skill so với `main`). Trục này săn lỗi chạy sai mà Spec và Standards không soi: dữ liệu bị bỏ khi ghi, guard an toàn bị lọt, logic viết lại thứ thư viện đã có. Finding mã `B1`, `B2`…
3. **Xác minh** finding sẽ đổi code: tự mở dòng được trích trước khi làm; reviewer có thể sai.
4. **Phân loại** mỗi finding:
   - *sửa*: vi phạm chuẩn trong diff; code trái AC hoặc `## Quyết định`; thiếu test hoặc test yếu cho một AC.
   - *hoàn tác*: thứ agent tự thêm ngoài phạm vi (không có AC, không có yêu cầu), kể cả vô hại.
   - *chỉ báo*: smell, lỗi có từ trước, điểm cần người dùng quyết. Mục ngoài phạm vi ticket còn đáng làm → backlog (`reference/rules.md`, *Phạm vi*).

   Trình bảng finding (mã, `file:line`, phân loại, cách sửa) và hỏi bằng `AskUserQuestion` (multi-select) những mục người dùng muốn sửa ngay; mục *sửa* để sẵn là khuyên dùng. Chỉ liệt kê nhóm sửa, không thêm lựa chọn "Không sửa gì": người dùng bỏ hết thì ghi ở Other. Mục trong `userRequested` hỏi trước khi hoàn tác.
5. **Vòng sửa, tối đa 2 vòng**, một sub-agent cho mọi vòng (vòng 2 gửi bằng `SendMessage`). Vòng 1 làm hết mục đã chọn thành một lô; vòng 2 chỉ xử lý thứ vòng 1 để lại đỏ hoặc làm hỏng. Mỗi mục đổi hành vi: test red trước khi có seam. Mỗi vòng một commit: `commit.py <T> --task R1` (vòng 2: `R2`), subject `fix(<scope>): address review findings on <chủ đề>`, thân liệt kê mã finding đã sửa (`B1`, `S2`…). Cuối mỗi vòng: `make lint`, `make test` qua `run_logged.py`, `check_ac_trace.py`. Còn mở sau vòng 2 → đưa lên G2.
6. **Ghi** bảng kết luận vào `report.md` (mục *Review*): mỗi finding một dòng (mã, `file:line`, đã sửa / chỉ báo / hoàn tác / bác, lý do vài chữ); gom smell vào một dòng. Cập nhật bảng AC → bằng chứng nếu test đổi.
7. `state.py transition <T> --to sync --next "đồng bộ tài liệu" --reason "review xong"`, in điểm clear.

## Xong khi

Check máy xanh; mọi finding có kết luận trong báo cáo; tối đa 2 vòng sửa đã chạy và vòng cuối xanh; `phase` là `sync`.
