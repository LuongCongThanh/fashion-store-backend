# 03 – Cấu hình bảo mật GitHub và `SECURITY.md`

Status: ready-for-human · Ưu tiên: 1 · Blocked by: — · **PR:**

Spec: [spec.md](../../spec.md) · Tiến độ: [report.md](./report.md)

## Mục tiêu
Repo có chính sách báo lỗ hổng và cấu hình GitHub chặn secret, chặn push thẳng `main`. Phần cấu hình đã xong; **chủ repo chỉ còn tự kiểm 3 AC chưa tick rồi đóng ticket**.

## Việc cần làm
- [x] Tạo `SECURITY.md` ở gốc (tiếng Việt): báo qua Private Vulnerability Reporting, **không** mở issue công khai; thời gian phản hồi dự kiến; phạm vi là repo boilerplate, không có production công khai.
- [x] Settings → Code security: bật Secret Scanning, Push Protection, Private Vulnerability Reporting, Dependabot alerts và security updates.
- [x] Settings → Actions → General: duyệt workflow từ fork cho mọi người ngoài (`all_external_contributors`); Workflow permissions = "Read repository contents".
- [x] Ruleset `main` (id 25858832): bắt buộc PR, 0 người duyệt; status check của ticket 02 + CodeQL; nhánh phải cập nhật với `main`; cấm force-push, cấm xoá.
- [x] Ghi chú ở `docs/architecture/11-git-workflow.md` mục 6: đang 0 người duyệt, nâng lên 1 khi có người thứ hai.
- [ ] Chủ repo tự kiểm 3 AC còn lại (xem dưới), rồi đóng ticket.

## Quyết định
- Agent chỉ chạy lệnh `gh` đổi cấu hình repo sau khi chủ repo xác nhận.
- 0 người duyệt là tạm thời, xem [spec](../../spec.md).
- Ruleset cho `dev` nằm ngoài phạm vi ticket.

## Acceptance criteria
- [ ] `SECURITY.md` hiện ở tab Security → Policy (sau khi PR #4 vào `main`).
- [ ] Push thử một secret giả lên nhánh nháp thì bị Push Protection chặn.
- [ ] Push thẳng lên `main` bị từ chối.
- [x] Nút "Report a vulnerability" hiện trong tab Security.

## Ghi chú
- Push Protection chỉ chặn secret đúng định dạng nhà cung cấp; secret giả tự chế sẽ lọt.
- Thử push thẳng `main` là thao tác không gỡ được nếu ruleset không chặn (đã cấm force-push). Cấu hình đã đọc lại qua `gh api /repos/{owner}/{repo}/rules/branches/main`.
