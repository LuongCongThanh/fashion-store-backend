# Hợp đồng sub-agent

Mọi sub-agent skill này tạo ra đọc file này trước. Phiên chính chỉ đọc kết quả trả về và state: thứ gì không nằm trên đĩa hoặc trong kết quả trả về sẽ mất.

- **Bản đồ trước, khám phá sau.** `.git/ship-ticket-fashion/<K>-map.md` đã liệt kê file, chữ ký, caller, test và fixture của ticket: dùng nó làm điểm xuất phát, chỉ đọc file đang sửa và file bản đồ chưa có. File mới phát hiện mà slice sau cần → thêm một dòng vào bản đồ.
- **Implementer giữ việc tới hết.** Phase 2 làm mọi slice theo DAG (`dependsOn` xong mới bắt đầu), mỗi slice một commit, rồi trả về một lần. Vòng sửa review và lỗi CI tới sau bằng `SendMessage`, dùng lại context code đã có.
- **Ghi trước khi trả về.** Mọi thứ bước sau cần đều ghi xuống đĩa: state (`slices.<id>.status`, `handoff`, `tests`, `next`, `untestable`) và commit. Reviewer chỉ trả báo cáo; phiên chính ghi `<K>-review.md`.
- **Quyết định thuộc về người dùng.** Gặp *Cần người dùng* (`reference/rules.md`): ghi vào `notes` của state, trả về ở dòng *Cần người dùng* rồi dừng. Câu trả lời quay lại bằng `SendMessage`.
- **Field của người dùng**: `gates`, `userRequested` do phiên chính ghi.
- **Sửa `backend/shared/` ngoài kế hoạch**: *Cần người dùng* kèm phạm vi ảnh hưởng (`grep -rl "<module>" backend --include=*.py | wc -l` và các module nào), cùng lựa chọn *giữ nguyên `shared`* và AC mất gì nếu chọn nó.
- **Trả về ≤ 15 dòng**, đúng khuôn:

  ```
  <Slice / vòng>: <xong / bị chặn>
  File đổi: <tên> (<n> file)
  Test: <x/y xanh> · lint: <ok / lỗi>
  check_ac_trace: <ok / AC thiếu>
  Lệch kế hoạch: <không / gì + "đã cập nhật state">
  Cần người dùng: <không / mỗi câu một dòng, có lựa chọn và khuyến nghị>
  ```
