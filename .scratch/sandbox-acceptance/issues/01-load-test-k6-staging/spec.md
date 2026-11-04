# 01 – Test tải bằng k6 trên staging

Status: needs-triage · Ưu tiên: 21 · Blocked by: — · **PR:**

## Mục tiêu
Trước đợt khuyến mãi lớn đầu tiên, biết hệ thống đạt mục tiêu hiệu năng và không bán vượt Tồn kho dưới tải. Việc sau MVP.

## Việc cần làm
- [ ] Viết kịch bản k6 theo [10-nfr.md mục 1](../../../../docs/architecture/10-nfr.md): p95 API đọc ≤ 300 ms, p95 `POST /store/checkout` ≤ 800 ms, 50 request/giây và 10 đơn/giây.
- [ ] Kịch bản checkout dồn vào một Biến thể có Tồn kho ít.
- [ ] Viết hướng dẫn chạy; chạy trên staging và ghi biên bản.

## Quyết định
- Chỉ chạy trên staging, dùng Fake Gateway; không chạy trên production.
- Cách làm theo [12-testing-strategy.md mục 9](../../../../docs/architecture/12-testing-strategy.md).

## Acceptance criteria
- [ ] Có kịch bản k6 commit trong repo và hướng dẫn chạy.
- [ ] Có biên bản kết quả một lần chạy trên staging, so với các mục tiêu ở `10-nfr.md`.
- [ ] Sau lần chạy, Tồn kho không âm và số đơn thành công không vượt Tồn kho ban đầu.
