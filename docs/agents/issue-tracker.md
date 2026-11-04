# Issue tracker: Markdown trong repo

Spec và ticket của repo này là file Markdown trong `.scratch/`, được commit lên git như tài liệu thường.

## Quy ước

- Mỗi feature một thư mục: `.scratch/<feature-slug>/`
- Spec nằm ở `.scratch/<feature-slug>/spec.md`
- Mỗi ticket là một thư mục `.scratch/<feature-slug>/issues/<NN>-<slug>/`, đánh số từ `01`, gồm:
  - `spec.md`: tiêu đề, dòng `Status: … · Ưu tiên: N · Blocked by: … · **PR:**`, các mục `## Mục tiêu`, `## Việc cần làm`, `## Quyết định`, `## Acceptance criteria`, `## Ghi chú`. Viết ngắn, đọc là làm được ngay; phần trùng `docs/` thì thay bằng link. Có từ khi tạo ticket.
  - `plan.md`: kế hoạch làm (slice, test, commit), có khi bắt đầu làm ticket.
  - `report.md`: báo cáo kết quả, trao đổi và bình luận, có khi đã làm xong.

## Thứ tự ưu tiên

- Mỗi ticket mở có `Ưu tiên: N`. N đánh liên tục qua mọi feature trong `.scratch/`, số nhỏ làm trước; ticket làm song song được có thể cạnh nhau.
- Thêm hoặc đổi chỗ một ticket thì đánh lại `Ưu tiên:` của mọi ticket mở đứng sau trong cùng PR, và cập nhật bảng **Tiến độ** trong `.scratch/mvp-roadmap/map.md`.
- Ticket `resolved` bỏ dòng `Ưu tiên:`.

## Ngôn ngữ

- Nội dung spec và ticket viết tiếng Việt; từ khoá kỹ thuật và tên trong code giữ tiếng Anh.
- Tên thư mục và tên file viết tiếng Anh, chữ thường, nối bằng `-`, ví dụ `checkout-cod/issues/02-reserve-stock/`.

## Liên kết với nhánh và PR

- Tên nhánh không chứa mã ticket, ví dụ `feat/checkout-cod`.
- Mô tả PR ghi thư mục ticket ở dòng **Closes**, ví dụ `.scratch/checkout-cod/issues/02-reserve-stock/`.

## Đóng ticket

Làm ngay trong PR của ticket đó, trên `spec.md`, để ticket được merge vào `dev` cùng lúc với code:

1. Đổi thành `Status: resolved`.
2. Tick hết các acceptance criteria.
3. Thêm dòng `**PR:** #<số>`.
4. Thêm ticket vào cuối phần **Đã xong** của feature trong [`ticket-history.md`](./ticket-history.md) và bỏ khỏi phần **Còn mở**.

`resolved` là trạng thái đóng, không thuộc 5 trạng thái triage.

## Khi skill nói "publish to the issue tracker"

Spec của feature là file mới `.scratch/<feature-slug>/spec.md`; mỗi ticket là thư mục mới `issues/<NN>-<slug>/` chứa `spec.md`. Tạo thư mục nếu chưa có.

## Khi skill nói "fetch the relevant ticket"

Đọc mọi file trong thư mục ticket được đưa. Thường người dùng sẽ đưa đường dẫn hoặc số ticket.

## Wayfinding (dùng cho `/wayfinder`)

**Map** là một file, mỗi ticket con là một thư mục riêng.

- **Map**: `.scratch/<effort>/map.md`, gồm các phần Notes / Decisions-so-far / Fog.
- **Ticket con**: `.scratch/<effort>/issues/NN-<slug>/spec.md`, đánh số từ `01`, câu hỏi nằm trong thân file. Dòng `Type:` ghi loại ticket (`research`/`prototype`/`grilling`/`task`); dòng `Status:` ghi `claimed`/`resolved`.
- **Chặn nhau**: dòng `Blocked by: NN, NN` gần đầu file. Ticket hết bị chặn khi mọi file nó liệt kê đều `resolved`.
- **Frontier**: quét `.scratch/<effort>/issues/` tìm file còn mở, không bị chặn và chưa ai nhận; số nhỏ nhất được làm trước.
- **Nhận việc**: đặt `Status: claimed` và lưu file trước khi bắt đầu.
- **Giải quyết**: ghi câu trả lời dưới heading `## Answer`, đặt `Status: resolved`, rồi thêm một dòng tóm tắt kèm đường dẫn vào phần Decisions-so-far của `map.md`.
