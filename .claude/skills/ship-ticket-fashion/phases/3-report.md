# Phase 3 — báo cáo

1. Viết báo cáo theo `templates/report.md` vào `report.md` của ticket (tạo file với dòng đầu `# Báo cáo` nếu chưa có), có ngày. Lần chạy sau (sau review, sync) **ghi đè** báo cáo này, không thêm bản mới: ticket chỉ giữ kết quả mới nhất.
   - Mỗi AC một dòng: test chứng minh (`file::test`, lấy từ state), hoặc lý do trong `untestable` và cách kiểm tay.
   - Số liệu lấy từ log `.git/ship-ticket-fashion/logs/lint.log` và `test.log` (số test, thời gian, coverage nếu có).
   - Mục *Commit*: output của `python3 S/scripts/commit_map.py <T> --md`.
   - *Ghi chú cho retro*: tối đa 3 dòng về việc đã tốn công và con trỏ bằng chứng, hoặc `Không`. Giữ và cập nhật khi ghi đè báo cáo ở review/sync; dùng bằng chứng còn lưu được thay vì chỉ trỏ log sẽ bị ticket sau ghi đè. Bước này chỉ ghi nhận, chưa phân loại hay đề xuất sửa skill.
2. Đưa người dùng bản báo cáo (in nguyên văn phần đã ghi vào `report.md`).
3. Để `report.md` chưa commit: report còn được ghi đè ở phase 4 và 5, rồi commit một lần trong task `sync`.
4. `state.py transition <T> --to review --next "chạy check máy rồi code-review" --reason "báo cáo đã ghi"`, in điểm clear.

## Xong khi

Mọi AC có một dòng trong bảng AC → bằng chứng; mục Đã làm, Chưa làm, Gap đều có nội dung hoặc ghi "Không"; mục *Commit* liệt kê mọi commit của nhánh; `phase` là `review`.
