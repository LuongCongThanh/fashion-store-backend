# Phase 8 — retro skill + push skill

Mục tiêu: cải thiện **môi trường** (skill, script, check, tài liệu cho agent), không phải code của ticket. Chạy ở phiên chính.

1. **Bằng chứng.** Phiên này; sau một `/clear` thì state, `report.md` của ticket, log trong `.git/ship-ticket-fashion/logs/`, và:

   ```bash
   python S/scripts/user_prompts.py --last 3
   ```

   Cộng `python S/scripts/commit_map.py <T>` trước khi merge (sau merge: thân commit squash trên `dev`): task có hai commit và nhiều commit `ci` là dấu làm lại. Gom mọi vấn đề đã tốn một lần làm lại, một câu người dùng phải nhắc hoặc sửa ("sao chưa…", "từ từ hỏi lại"), một vòng debug, hoặc một lệnh đắt.
2. **Phân loại** mỗi vấn đề vào loại đầu tiên khớp:
   - **Check tự động**: lỗi máy bắt được → mã hoá ở chỗ hẹp nhất bắt được nó: test, script trong `S/scripts/` (bước shell lặp lại), rule ruff / import-linter, hook pre-commit. Check có sẵn nhưng chưa nối hoặc đang hỏng là phát hiện, không làm check mới.
   - **Chuẩn code**: review bắt muộn hoặc bỏ sót. Máy móc → check ở trên; cần phán đoán → `CONTRIBUTING.md` hoặc tài liệu architecture mà trục Standards đọc.
   - **Điều hướng**: tìm file hay thông tin lâu → một con trỏ trong file phase cần nó.
   - **Tiết kiệm token**: lệnh output dài, chạy lại toàn bộ không cần → bộ lọc trong lệnh của phase, hoặc dùng `run_logged.py`.
   - **Câu thừa**: dòng trong skill, `CLAUDE.md` không làm thay đổi gì agent làm, hoặc bị bỏ qua → xoá, hoặc viết sắc hơn.
   - **Gotcha**: chỉ khi không loại nào ở trên mã hoá được, và qua đủ 4 điều kiện: **mới** (chưa có trong `gotchas/`), **đã xác minh** (nguyên nhân chứng minh bằng thử, không đoán), **sẽ lặp lại** ở ticket khác, **cách sửa cụ thể** (lệnh, cấu hình). Dạng: `- **<triệu chứng>**: nguyên nhân: <…>. Sửa: <…>. (<T>)`, tối đa 2 dòng, mỗi file `gotchas/` ≤ 4 KB.
3. **Đề xuất, chưa ghi.** Một tin liệt kê mọi đề xuất, xếp theo mức đã tốn ở ticket này, mỗi mục có lý do. Hỏi bằng `AskUserQuestion` (multi-select, ≤ 4 mục mỗi câu, gom theo file khi nhiều). Không có vấn đề nào → báo "không có gì để cải thiện", `transition --to closed`, dừng.
4. **Ghi** chỉ mục được chọn, theo `mattpocock-skills:writing-for-agents`: mỗi ý một chỗ; viết điều cần làm thay vì điều cấm; thêm một dòng thì tìm một dòng đã thừa hoặc đã cũ để xoá. Script sửa thì chạy `python -m unittest discover -s S/scripts` cho xanh. Thay đổi ngoài `.claude/skills/` (hook, cấu hình lint) ảnh hưởng cả repo: chạy `make lint` và `make test`.
5. **Bộ nhớ**: chỉ lưu vào memory của agent khi người dùng sửa cách làm việc hoặc bảo nhớ; bài học kỹ thuật nằm trong skill.
6. **Push skill.** Từ `origin/dev` mới nhất, nhánh `chore/skill-retro-<feature>-<NN>` (tên riêng mỗi ticket, để PR retro trước chưa merge không đụng nhau), commit `chore: refine ship-ticket-fashion skill after <T>`, push và mở PR vào `dev` theo `phases/6-ship.md` mục 1, 2, 3. Báo người dùng URL PR.
7. `state.py transition <T> --to closed --next "chọn ticket tiếp theo" --reason "retro xong"`.

## Xong khi

Mọi vấn đề có loại và kết luận (đề xuất, hoặc bị bộ lọc gotcha loại); người dùng đã trả lời; chỉ mục được chọn được ghi và check của chúng xanh; có URL PR của skill (hoặc không có gì để sửa); `phase` là `closed`.

## Retro một PR

Cho PR không đi qua vòng của skill (sửa tay, review theo yêu cầu, PR tài liệu), khi người dùng gọi `retro #<số>`. Không có state; bước 2–6 như trên với `<T>` thay bằng `pr-<số>`.

1. Bằng chứng (tài khoản ở `phases/6-ship.md`):

   ```bash
   GH_TOKEN="$(gh auth token --user LuongCongThanh)" gh pr view <số> --json title,commits,reviews,comments,statusCheckRollup
   python S/scripts/user_prompts.py --last 3
   ```

   Thêm comment gắn dòng code theo `phases/6-ship.md` mục 3. Tìm những gì skill lẽ ra đã làm: commit sửa sau review, câu người dùng phải nhắc, check CI đỏ.
2. Thêm câu hỏi riêng: việc của PR này có nên đi qua skill không (ticket mới `needs-triage`, hay một nhánh mới trong `SKILL.md`)?
