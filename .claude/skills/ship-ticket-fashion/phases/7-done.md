# Phase 7 — done

1. Báo người dùng: URL PR, tiêu đề, trạng thái CI, từng AC → kết quả, việc chưa kiểm (AC `untestable`), ticket mới đã tạo. Nói thẳng phần nào chưa được kiểm chứng.
2. Hỏi bằng `AskUserQuestion`: merge ngay (khuyên dùng khi CI xanh và không còn mục mở), hay chờ (người dùng tự review hoặc merge sau).
3. Merge ngay:

   ```bash
   python3 S/scripts/commit_map.py <T> --md > .git/SQUASH_BODY.md
   GH_TOKEN="$(gh auth token --user LuongCongThanh)" gh pr merge <số> --squash --delete-branch -F .git/SQUASH_BODY.md
   git switch dev && git pull
   python3 S/scripts/progress.py
   ```

   Thân commit squash trên `dev` giữ bảng commit → task, nên sau khi nhánh bị xoá vẫn tra được commit nào thuộc task nào. Chờ: giữ phase `done`, ghi `next=chờ merge PR #<số>` rồi dừng. Lần chạy sau, `reference/resume.md` kiểm trạng thái PR.
4. **Sau merge**, `git fetch origin`, chạy `python3 S/scripts/retro_batch.py status`:
   - `due: false`: `state.py transition <T> --to closed --next "chọn ticket tiếp theo" --reason "merged; chưa đủ 10 ticket cho retro"`. Báo `<pending>/10 ticket cho đợt retro tiếp theo`, rồi kết thúc; phần phân tích retro chỉ được nạp khi đủ đợt.
   - `due: true`: kiểm PR đang mở có nhánh dạng `chore/skill-retro-<12 ký tự hex>` (đợt retro). Có rồi → báo URL, `transition --to closed` với lý do `đợt retro chờ merge`; phần dư sẽ được đếm khi checkpoint merge. Chưa có → `state.py transition <T> --to retro --next "retro đợt <batch>" --reason "đủ 10 ticket đã merge"`, rồi đọc `phases/8-retro.md`. Dùng `batch`, `through` và danh sách `tickets` script in ra làm phạm vi review.

## Xong khi

Chờ merge: `phase` là `done`. Đã merge: ticket `resolved` trên `origin/dev`, đã kiểm đếm retro; `phase` là `closed` khi chưa đủ đợt hoặc `retro` khi đủ đợt.
