# Chọn ticket

Đọc khi `state.py start` in `NO STATE` kèm `FRONTIER`: chưa có ticket đang làm. Mọi câu hỏi dưới đây gom vào **một** lần hỏi (khuôn ở `SKILL.md` → *Gate*, phần *Quyết định*).

1. **Tiến độ.** Chạy `python3 S/scripts/progress.py`, báo tóm tắt cho người dùng.
2. **Ticket nên làm.** Khuyên dùng theo thứ tự ưu tiên mới nhất trong *Decisions-so-far* của `.scratch/mvp-roadmap/map.md`. Chưa có thứ tự thì đề xuất: lỗi thật trước, rồi tới cổng chặn CI; người dùng duyệt thì ghi thứ tự đó vào *Decisions-so-far*.
3. **Ticket `needs-triage`** (nếu có): đề xuất người dùng gõ `/mattpocock-skills:triage <thư mục ticket>`. Người dùng muốn trả lời ngay thì hỏi từng ticket: `ready-for-agent`, `ready-for-human`, `wontfix` hay để sau (`docs/agents/triage-labels.md`). Ghi dòng `Status:` theo kết quả; file này commit cùng commit `plan` ở phase 1 (bước *Duyệt xong*).
4. **Điểm nóng.** Một package đã có từ 3 ticket trở lên sửa (`git log --oneline origin/dev -- <package>`) và frontier còn ticket ở đó → đề xuất theo `phases/0-plan.md` mục *Điểm nóng*.

Frontier rỗng, hoặc mốc chỉ còn ticket bị chặn hay cần người → `phases/0-plan.md` thay cho các bước trên.

## Xong khi

Người dùng đã chọn ticket, mọi ticket `needs-triage` có câu trả lời hoặc được để sau; vào `phases/1-grill.md` với ticket đó.
