# Phase 5 — đồng bộ tài liệu và code + ⛔G2

Mục tiêu: sau PR này, `docs/` và `.scratch/` mô tả đúng code trên nhánh.

1. **Danh sách thay đổi.** Từ `git diff origin/dev...HEAD --stat` và diff của code: tên công khai mới hoặc đổi (hàm, lớp, setting), lệnh `make`, biến môi trường, file / thư mục mới, endpoint, model, hành vi đổi khi review.
2. **Dò chỗ cũ.** Với từng mục, `grep -rn "<tên>" docs GLOSSARY.md .scratch CONTRIBUTING.md README.md` rồi sửa chỗ mô tả hành vi cũ. Các tài liệu hay lệch:
   - `docs/architecture/02-backend-structure.md`: cây thư mục, module, API của `shared`.
   - `03-data-model.md`: field, ràng buộc, migration.
   - `04-api-contract.md`: endpoint, định dạng lỗi, phân trang.
   - `08-local-development.md`: lệnh `make` (bảng ở mục 3), biến môi trường (mục 2.3), `.env.example`.
   - `12-testing-strategy.md`: marker, fixture, cổng chặn CI.
3. **Domain.** Thuật ngữ mới → `GLOSSARY.md`; quyết định kiến trúc lâu dài → ADR; cả hai qua `mattpocock-skills:domain-modeling`.
4. **Ticket.** `## Quyết định` trong `spec.md` khớp code cuối cùng (chữ ký hàm, hành vi đổi khi review). Việc ngoài phạm vi phát hiện được → backlog theo `reference/rules.md` (*Phạm vi*).
5. **Code nhỏ cùng loại**: thứ phase này lộ ra trong phạm vi ticket (tên lệch tài liệu đã chốt, comment sai) thì sửa code, chạy lại test liên quan.
6. Ghi mục *Tài liệu đã cập nhật* và làm mới mục *Commit* của báo cáo (`commit_map.py <T> --md`), rồi commit tài liệu, code nhỏ của bước 5 và thư mục ticket trong một lần: `commit.py <T> --task sync -m "docs: sync docs and report for <chủ đề> ticket" -- <file>…`.
7. **Check cuối**: `make lint --keep-going` và `make test` khi bước 5 hoặc vòng sửa có đổi code sau lần xanh gần nhất (`reference/rules.md` → *Check máy*); luôn chạy `check_ac_trace.py` và `check_ship.py <T>`. Mỗi dòng `WARN` / `FAIL` là một điểm của G2.
8. **⛔G2** (khuôn ở SKILL.md → *Gate*). Tin tóm tắt: bảng AC → bằng chứng; kết luận review (mục còn mở); tài liệu đã cập nhật; ticket mới đã tạo; số test; dòng `WARN` / `FAIL` của `check_ship.py`; tiêu đề PR đề xuất. Nói rõ: duyệt G2 cho phép phase 6 push, mở PR và đóng ticket mà không hỏi thêm; merge vẫn hỏi riêng. Hỏi: duyệt ship (khuyên dùng khi không có `FAIL`), sửa thêm, hay dừng.
9. Người dùng yêu cầu sửa thêm → ghi `userRequested`, sửa (đổi hành vi thì `--to code` rồi đi lại các phase), trình G2 lại. Duyệt xong:

   ```bash
   python3 S/scripts/state.py transition <T> --to ship --gate g2 --next "push và mở PR" --reason "G2 approved"
   ```

## Xong khi

Mọi mục trong danh sách thay đổi đã grep, không còn chỗ nào trong tài liệu mô tả hành vi cũ; check cuối xanh hoặc từng `WARN` đã được trả lời ở G2; `gates.g2` có ngày và `phase` là `ship`.
