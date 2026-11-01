# Phase 0 — lập kế hoạch mốc tiếp theo

Dùng khi frontier của mốc hiện tại rỗng hoặc sắp rỗng, người dùng muốn làm một module chưa có ticket (lấy mốc chứa module đó), hoặc muốn tách lại ticket. Theo `.scratch/mvp-roadmap/map.md`, spec của mốc sau tạo khi mốc trước gần xong, để spec dựa trên code đã có. Không có state riêng: kết quả là các file trong `.scratch/`.

## Tạo spec cho mốc mới

1. Lấy dòng của mốc trong bảng **Notes** của `map.md`: thư mục, nội dung, user story, điều kiện "Xong khi". `progress.py` in những mốc chưa có thư mục.
2. Sub-agent `Explore` đọc và tóm tắt: các user story đó trong `docs/business/03-user-stories.md`, quy tắc liên quan trong `04-business-rules.md` và `05-order-lifecycle.md`, các tài liệu architecture và ADR của module chạm tới, code `backend/shared` hiện có.
3. `mattpocock-skills:grilling` để chốt phạm vi và quyết định.
4. Nhờ người dùng gõ `/mattpocock-skills:to-spec` (skill chỉ người dùng gọi được) → `.scratch/<slug>/spec.md`. Kiểm kết quả theo khung của `.scratch/backend-bootstrap/spec.md`: Bối cảnh, Phạm vi, Quyết định, Ticket (danh sách theo thứ tự làm, `progress.py` dùng thứ tự này cho frontier), Ngoài phạm vi.
5. Nhờ người dùng gõ `/mattpocock-skills:to-tickets` → `.scratch/<slug>/issues/NN-<slug>/spec.md`. Kiểm từng ticket theo khung dưới; `plan.md` và `report.md` sinh ra khi làm ticket.

## Điểm nóng

Khi gặp điều kiện điểm nóng ở `SKILL.md` (*Đầu mỗi lần chạy*), hoặc người dùng hỏi kiến trúc một khu vực → đề xuất người dùng gõ `/improve-codebase-architecture <khu vực>` trước khi tạo hay làm thêm ticket ở đó. Ứng viên người dùng chọn đi qua bước 5, thành ticket `needs-triage`; ticket cũ trùng việc thì gộp vào hoặc đóng `wontfix`.

## Khung `spec.md` của ticket

```markdown
# <Tiêu đề tiếng Việt>

Status: ready-for-agent

Blocked by: NN, NN

Spec: [spec.md](../../spec.md)

## Việc cần làm

## Acceptance criteria

- [ ] <hành vi kiểm chứng được bằng test>
```

- Mỗi ticket là một _tracer bullet_ vừa một PR (dưới khoảng 400 dòng, không tính migration), chạy được từ đầu tới cuối.
- Acceptance criteria viết thành hành vi đặt được thành tên test; ghi `US-xxx`, `BR-xxx` liên quan.
- Tách ticket lớn: giữ số cũ cho phần đầu, phần tách ra lấy số tiếp theo của feature, ghi `Tách từ ticket [NN](../NN-…/spec.md).` Không đánh số lại ticket đã có.

## Xong khi

- Mọi user story trong dòng của mốc được ít nhất một ticket nhắc tới.
- `progress.py` in frontier không rỗng cho mốc mới, không có cảnh báo.
- `map.md`: bảng Tiến độ có dòng của mốc, Decisions-so-far có dòng ngày tạo spec.

Ship phần kế hoạch như một PR tài liệu (nhánh `docs/<slug>-spec`) theo `phases/6-ship.md` mục 1, 2, 4, rồi chạy lại skill để chọn ticket.
