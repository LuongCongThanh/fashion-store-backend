# Retro

Mục tiêu: từ bằng chứng của ticket vừa làm, sửa ngay chỗ gây làm lại hoặc tốn token trong môi trường agent (skill, script, check, tài liệu) và đưa vào cùng PR. Phiên chính làm. Phase 5 gọi bước 1–3 trước G2, bước 4–5 sau khi G2 duyệt; `retro #<PR>` dùng mục cuối.

1. **Bằng chứng.**
   - `python3 S/scripts/metrics.py <T>`: token theo phase và agent. Phase hoặc agent tốn nhất là ứng viên đầu tiên.
   - *Ghi chú cho retro* trong `report.md`, finding review, vòng sửa, check chạy lại (log ở `.git/ship-ticket-fashion/logs/`).
   - `python3 S/scripts/user_prompts.py --last 1`: lời nhắc lặp lại, chỗ người dùng phải sửa hướng.

   Xong khi mỗi điểm tốn công có nguyên nhân kèm bằng chứng, hoặc ghi rõ chưa xác minh được.
2. **Nơi sửa hẹp nhất** cho mỗi nguyên nhân:
   - Máy kiểm được → test, script, lint hoặc hook hiện có.
   - Quy ước code hoặc thiết kế → `CONTRIBUTING.md` hoặc tài liệu architecture mà reviewer đọc.
   - Điều hướng, thao tác → một chỉ dẫn ở đúng phase dùng nó; output dài → lọc qua `run_logged.py`.
   - Chỉ dẫn thừa, trùng hoặc lỗi thời → xoá hoặc sửa tại nguồn.
   - Gotcha khi nguyên nhân đã xác minh, sẽ lặp lại và các chỗ trên chưa mã hoá được: `triệu chứng → nguyên nhân → cách sửa (ticket)`, tối đa 2 dòng; mỗi file `gotchas/` ≤ 4 KB.
3. **Đề xuất.** Danh sách gọn (vấn đề, bằng chứng, token hoặc lượt đã tốn, nơi sửa, khuyến nghị) đi vào G2 của phase 5. Không có gì đáng sửa → ghi `Retro: không` vào *Ghi chú cho retro*.
4. **Viết** cải tiến đã duyệt theo `mattpocock-skills:writing-for-agents`: mỗi ý một nguồn; chỉ dẫn hành động có tiêu chí xong; phần chỉ một nhánh dùng đặt sau con trỏ của nhánh đó; cắt dòng trùng, no-op hoặc đã được script, cấu hình diễn đạt. Phần riêng của Codex ở `.agents/skills/ship-ticket-fashion/`.
5. **Kiểm và commit.** Sửa script → `python3 -m unittest discover -s S/scripts`; sửa hook hoặc cấu hình backend → check tương ứng (*Check máy*); luôn `git diff --check`. Ghi cải tiến đã làm vào *Ghi chú cho retro*, rồi `commit.py <T> --task retro -m "chore: refine ship-ticket-fashion after <chủ đề> ticket" -- <file>… <report.md>`.

Bài học ghi vào nguồn chuẩn của skill hoặc repo; memory chỉ ghi khi người dùng yêu cầu.

## Xong khi

Mỗi điểm tốn công có kết luận; chỉ cải tiến đã duyệt được sửa, đã kiểm và nằm trong commit `Task: retro`, hoặc báo cáo ghi `Retro: không`.

## Retro một PR (`retro #<số>`)

Chạy ngay, không cần state.

1. Bằng chứng: `gh pr view <số> --json title,commits,reviews,comments,statusCheckRollup` (tài khoản ở `phases/6-ship.md`), comment gắn dòng theo mục CI của phase đó, báo cáo ticket nếu có, `user_prompts.py`.
2. Làm bước 2 và 4, kiểm theo bước 5. Cải tiến người dùng đã yêu cầu cụ thể là đã duyệt; đề xuất mới hỏi bằng `AskUserQuestion`.
3. Có sửa → nhánh `chore/skill-retro-pr-<số>` từ `origin/dev`, commit `chore: refine ship-ticket-fashion after PR #<số>`, PR theo `phases/6-ship.md` mục 1–3. Không có sửa → báo kết luận.
