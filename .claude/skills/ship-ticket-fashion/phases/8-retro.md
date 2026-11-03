# Phase 8 — retro theo đợt

Mục tiêu: từ bằng chứng của một đợt ticket, sửa chỗ gây làm lại trong môi trường agent (skill, script, check, tài liệu). Phiên chính thực hiện; mỗi đợt một PR.

## Phạm vi đợt

`python3 S/scripts/retro_batch.py status` trả `pending`, `due`, `batch`, `through` và `tickets` (tối đa 10 đường dẫn spec). Chỉ bắt đầu retro tự động khi `due: true`; dùng đúng 10 ticket trong `tickets`. Đợt mới: lưu output vào `notes` của state trước khi review. Làm tiếp: dùng snapshot đã lưu để giữ nguyên phạm vi qua phiên mới.

Checkpoint `S/reference/retro-batch.json` được commit cùng repo: `baseline` là mốc bắt đầu chính sách, `batches` giữ các đợt đã xử lý. Script lấy spec `Status: resolved` trong `origin/dev`, loại ticket đã resolved tại baseline và các đợt đã xử lý. Ticket chờ merge, PR tài liệu/retro và việc chạy lại cùng ticket không tăng bộ đếm. Thứ tự đợt theo đường dẫn ticket để chọn ổn định; nếu tồn hơn 10 thì phần dư ở đợt kế tiếp.

State cũ ở `retro` nhưng chưa đủ đợt → `transition --to closed --next "chọn ticket tiếp theo" --reason "hoãn retro tới đủ 10 ticket"`, báo `<pending>/10` rồi dừng. Lỗi Git/checkpoint cần sửa trước khi quyết định đợt; lỗi không có nghĩa là bộ đếm bằng 0.

## Review và cải thiện

1. **Bằng chứng.** Đọc `report.md`, đặc biệt *Ghi chú cho retro*, của đủ 10 ticket; bổ sung spec/plan, finding, commit → task trong thân squash commit và review/CI của PR khi cần xác minh. Log dùng chung bị lần chạy sau ghi đè, nên chỉ dùng khi còn khớp ticket. Claude Code: đề xuất người dùng gõ `/mattpocock-skills:retro` cho phiên hiện tại; ứng viên nó trình bày theo nhóm là bằng chứng cho bước 2. Có thể thêm `python3 S/scripts/user_prompts.py --last 3`; script chỉ in prompt đã che credential từ số phiên gần nhất (`--last` phải ≥ 1), không đại diện cả đợt. Codex lấy nguồn theo entrypoint Codex. Xong khi mỗi ghi chú có kết luận có bằng chứng hoặc ghi rõ chưa xác minh được.
2. **Gom vấn đề cùng nguyên nhân**, kèm ticket/PR và chi phí đã quan sát (lượt làm lại, debug, lệnh đắt, lời nhắc). Chọn nơi sửa hẹp nhất:
   - Máy kiểm được → test, script, lint hoặc hook hiện có; kiểm tra thứ đã có trước khi thêm mới.
   - Quy ước code hoặc thiết kế → `CONTRIBUTING.md` hoặc tài liệu architecture mà reviewer đọc.
   - Điều hướng/thao tác → một chỉ dẫn ở đúng phase dùng nó; output dài → lọc log qua `run_logged.py`.
   - Chỉ dẫn thừa, trùng hoặc lỗi thời → xoá hoặc sửa ngay tại nguồn chuẩn.
   - Gotcha chỉ khi nguyên nhân đã xác minh, sẽ lặp lại và có cách sửa cụ thể mà các chỗ trên chưa mã hoá được. Ghi `triệu chứng → nguyên nhân → cách sửa (ticket/PR)`, tối đa 2 dòng; mỗi file `gotchas/` ≤ 4 KB.
3. **Chọn cải tiến.** Trình một danh sách gọn: vấn đề, bằng chứng, nơi sửa, khuyến nghị theo chi phí/lần lặp. Hỏi bằng `AskUserQuestion` những đề xuất chưa được người dùng duyệt; chỉ sửa mục được chọn. Chưa có gì đáng sửa thì ghi kết luận đó và tiếp tục checkpoint, không hỏi chọn danh sách rỗng.
4. **Viết theo `mattpocock-skills:writing-for-agents`.** Đọc skill nếu có; dùng fallback của entrypoint Codex khi thiếu. Mỗi ý một nguồn; chỉ dẫn hành động và điều kiện hoàn tất cụ thể; phần chỉ dùng ở một nhánh đặt sau con trỏ của nhánh đó. Cắt dòng trùng, không còn tác dụng hoặc đã được cấu hình/script diễn đạt. Cải tiến chung ở `S`; phần riêng của Codex ở `.agents/skills/ship-ticket-fashion/`.
5. **Kiểm chứng và checkpoint.** Sửa script → `python3 -m unittest discover -s S/scripts`. Sửa hook/cấu hình backend → chạy lint/test liên quan qua `run_logged.py`. Luôn `git diff --check`. Khi mọi vấn đề đã có kết luận và sửa được chọn đã kiểm xong, dùng snapshot đã lưu:

   ```bash
   python3 S/scripts/retro_batch.py complete --through <through> --batch <batch>
   ```

   Lệnh chỉ ghi nhận 10 ticket của snapshot đó; chạy lại cùng `batch` giữ nguyên kết quả. Ticket merge sau `through` vẫn chờ đợt sau. Checkpoint không được ghi trước khi review xong.
6. **Một PR cho cả đợt.** Từ `origin/dev` mới nhất, nhánh `chore/skill-retro-<batch>`, commit `chore: refine ship-ticket-fashion after batch <batch>`. Commit checkpoint cùng các sửa đã duyệt; không có sửa thì PR chỉ checkpoint, thân PR ghi kết luận review. Tìm PR cùng nhánh trước để tiếp tục PR đang mở. Push, mở PR vào `dev`, kiểm CI và comment theo `phases/6-ship.md` (mục mở PR và kiểm CI); ghi đủ 10 ticket, bằng chứng, kết luận và cách kiểm trong thân PR. Merge vẫn theo chỉ thị người dùng. Kết thúc bằng `state.py transition <T> --to closed --next "chọn ticket tiếp theo" --reason "retro đợt <batch> có PR #<số>"`.

Chỉ ghi memory khi người dùng yêu cầu trực tiếp; bài học kỹ thuật nằm trong nguồn chuẩn của skill/repo.

## Xong khi

Đủ 10 ticket đã được review; mỗi vấn đề có kết luận; chỉ cải tiến đã duyệt được ghi và kiểm chứng; checkpoint và thay đổi nằm trong một PR, hoặc PR đợt có sẵn đã được cập nhật; state ticket là `closed`. Checkpoint có hiệu lực trên các nhánh mới sau khi PR merge vào `dev`.

## Retro một PR theo yêu cầu

`retro #<số>` chạy ngay, độc lập bộ đếm và không ghi nhận đợt 10 ticket. Không có state ticket.

1. Lấy bằng chứng bằng `gh pr view <số> --json title,commits,reviews,comments,statusCheckRollup` với tài khoản ở `phases/6-ship.md`; đọc thêm comment gắn dòng theo phần kiểm CI của phase đó và báo cáo ticket nếu có. Nguồn hội thoại theo môi trường như bước 1 ở trên.
2. Làm bước 2–4 và kiểm chứng ở bước 5 cho PR này. Người dùng yêu cầu cải tiến cụ thể là đã duyệt phần đó; chỉ hỏi phần đề xuất mới còn mở.
3. Có sửa → nhánh `chore/skill-retro-pr-<số>`, một PR theo bước 6, bỏ thao tác checkpoint và transition state. Không có sửa → báo kết luận rồi kết thúc.
