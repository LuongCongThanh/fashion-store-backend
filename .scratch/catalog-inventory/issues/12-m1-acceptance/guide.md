# Guide ticket 12 — Acceptance M1

## Mục đích

Không viết feature mới. Chạy flow xuyên module, tìm gap và đóng mọi gate trước khi tuyên bố M1 hoàn tất.

## Bản đồ file

| Vị trí | Dùng làm gì | Mục đích |
|---|---|---|
| flow tests M1 | Admin→Staff→Storefront | Chứng minh outcome |
| `backend/openapi.yaml` | Contract đã triển khai | Frontend/drift gate |
| migration/import/query tests | Hardening | Chặn regression |
| ticket `report.md` | Kết quả lệnh/gap | Handoff trung thực |

## Cách viết code và thứ tự thực hiện

Ticket này không viết lại toàn hệ thống. Với mỗi failure, đọc traceback, xác định đúng module/tầng sở hữu, viết pseudo-code cho thay đổi nhỏ nhất rồi sửa production code. Không sửa test hợp lệ chỉ để xanh và không tạo abstraction khi mới có một trường hợp.

1. **Step 1:** Mentor viết/hoàn thiện flow acceptance test đỏ cho gap còn lại.
2. **Step 2:** Bạn chạy Admin login→Catalog→publish.
3. **Step 3:** Chạy Staff login→Nhập kho→GET stock→idempotency replay.
4. **Step 4:** Chạy storefront category/search/filter/detail→archive.
5. **Step 5:** Sửa production gap, không nới expectation/gate vô lý.
6. **Step 6:** Chạy migration DB rỗng/upgrade, OpenAPI, import-linter, query baseline.
7. **Step 7:** Chạy fmt/lint/full test, gửi diff review.
8. **Step 8:** Sau khi xanh mới viết report và đóng ticket/M1.

## Kiến thức

End-to-end test design, fixture/data isolation, contract drift, migration safety, performance baseline, release evidence.
