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
4. **Sau merge**: `state.py transition <T> --to closed --next "chọn ticket tiếp theo" --reason "merged"`.

## Xong khi

Chờ merge: `phase` là `done`. Đã merge: ticket `resolved` trên `origin/dev`, `phase` là `closed`.
