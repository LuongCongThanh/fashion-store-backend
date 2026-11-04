# Kế hoạch thực hiện ticket 01

Spec: [spec.md](./spec.md)

Hướng dẫn người học: [guide.md](./guide.md)

## Checkpoints

| Step | Người thực hiện | Kết quả | Review gate |
|---:|---|---|---|
| 1 | Người học | Baseline + mô tả flow/code seam | Mentor xác nhận trước khi tạo file |
| 2 | Mentor | Test đỏ login thành công | Người học chạy và giải thích failure |
| 3 | Người học | Dependencies + typed config + Argon2/startup checks | Config tests xanh, không hard-code secret |
| 4 | Người học | `RefreshToken`/`RefreshReplay` + migration | Mentor review schema/constraint; login chưa tạo replay record |
| 5 | Người học | Token codec | JWT security matrix xanh |
| 6 | Người học | Failure ledger đăng nhập | Boundary/concurrency/fail-open tests xanh |
| 7 | Người học | Login service | Mentor review transaction/error boundary |
| 8 | Người học | Serializer/view/URL/OpenAPI login | API happy-path test xanh |
| 9 | Người học | `JWTAuthentication` + `GET backoffice/auth/me` | DB auth state và permission tests xanh |
| 10 | Mentor + người học | Edge cases + fmt/lint/tests/OpenAPI | Security matrix xanh, không còn blocker |

## Quy tắc

- Mentor viết test; người học viết production code.
- Không sang step tiếp theo khi review gate hiện tại chưa đạt.
- Không tạo `report.md` trước khi implementation/gates hoàn tất.
- File path chi tiết và lệnh nằm trong `guide.md`; nếu code thật khác, cập nhật guide trước khi đi tiếp.
