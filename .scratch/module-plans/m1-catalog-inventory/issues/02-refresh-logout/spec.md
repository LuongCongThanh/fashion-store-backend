# 02 — Xoay refresh token và đăng xuất

**What to build:** Người dùng back-office có thể dùng refresh token để nhận đúng một successor và đăng xuất để family hiện tại không cấp thêm token. Retry hợp lệ trong cửa sổ nhận lại đúng response; reuse đáng ngờ thu hồi family.

Blocked by: 01 — Staff/Admin đăng nhập back-office.

Status: ready-for-agent

**PR:** —

- [ ] Refresh lần đầu cấp một TokenPair mới và đánh dấu predecessor đúng transaction.
- [ ] Hai refresh đồng thời chỉ tạo một successor; retry trong 10 giây trả đúng cặp đã cấp.
- [ ] Successor đã dùng hoặc reuse ngoài cửa sổ xử lý đúng ADR 0014.
- [ ] Logout thu hồi family/replay và trả 204; không cần access token còn hạn.
- [ ] Crypto/concurrency/API/OpenAPI tests chứng minh hành vi, không lộ token/ciphertext plaintext.
