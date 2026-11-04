# Fashion Store – Backend Django

## Quy tắc dự án

- Đọc `GLOSSARY.md` trước khi bắt đầu. Dùng đúng thuật ngữ trong đó và tránh các từ ở mục _Avoid_.
- Trước khi sửa Python/Django, đọc và tuân thủ `docs/architecture/13-python-django-coding-style.md`.
  Đây là cẩm nang tổng hợp convention; cấu hình thực thi và tài liệu kiến trúc được dẫn chiếu trong đó
  sở hữu các quy tắc tương ứng. Kiểm tra thêm tài liệu liên quan tới phần code sẽ sửa.
- Trước khi sửa, kiểm tra code lân cận và cấu hình thật; không tự tạo convention mới từ một ví dụ đơn lẻ.
- Không đọc hoặc in `.env*` (trừ `.env.example`), `.secrets/`, `*.pem` hay dữ liệu khách hàng thật.
- Tài liệu (business, architecture, ADR, spec, ticket) viết tiếng Việt; giữ tiếng Anh cho từ khoá kỹ thuật, tên trong code và tên package.
- Tên nhánh, commit message và tiêu đề PR viết tiếng Anh theo Conventional Commits. Xem `docs/architecture/11-git-workflow.md`.
- Không tuyên bố hoàn tất nếu chưa chạy kiểm tra phù hợp. Với thay đổi code, chạy ở gốc repo:
  `make fmt`, `make lint` và test tương xứng với rủi ro; full test suite là cổng trước merge/release.
  Nếu không chạy được lệnh nào, phải báo rõ lệnh và lý do.

## Agent skills

### Issue tracker

Spec và ticket là file Markdown trong `.scratch/<feature-slug>/`, commit lên git. Xem `docs/agents/issue-tracker.md`.

### Triage labels

5 trạng thái mặc định, ghi ở dòng `Status:` của mỗi ticket. Xem `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` và `docs/adr/` ở gốc repo. Xem `docs/agents/domain.md`.
