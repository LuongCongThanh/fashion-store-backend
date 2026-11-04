# 01 — Staff/Admin đăng nhập back-office

**What to build:** Staff hoặc Admin nhập đúng email/mật khẩu tại back-office và nhận một cặp access/refresh token đúng audience. Customer, tài khoản vô hiệu hoặc credential sai nhận cùng lỗi đăng nhập chung; token back-office gọi được endpoint được bảo vệ.

Blocked by: None — can start immediately.

Status: ready-for-agent

**PR:** —

- [ ] Staff và Admin đăng nhập thành công, nhận đủ `TokenPairDTO` và dùng access token gọi `GET backoffice/auth/me`, endpoint trả `AccountDTO`.
- [ ] Customer, tài khoản vô hiệu, email/mật khẩu sai bị từ chối mà không lộ nguyên nhân.
- [ ] Token có đúng issuer/audience/`token_use`/kid/expiry và claims bắt buộc; token sai mục đích/audience/algorithm bị từ chối.
- [ ] `RefreshToken` và `RefreshReplay` có schema đúng data model; login chỉ tạo refresh family/hash, chưa tạo replay record và không lưu/log token thô.
- [ ] Failure ledger giới hạn đăng nhập sai theo email/IP, atomic khi Redis hoạt động, trả đúng `Retry-After` và fail-open có metric khi Redis lỗi.
- [ ] Mọi request back-office đọc trạng thái auth từ PostgreSQL; DB không xác minh được trả `503 AUTH_STATE_UNAVAILABLE`.
- [ ] OpenAPI và security/API tests chứng minh đầy đủ hành vi trên.
