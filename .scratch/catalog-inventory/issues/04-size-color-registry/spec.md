# 04 – Quản lý danh sách size và bảng màu

Status: ready-for-agent · Ưu tiên: 7 · Blocked by: [01](../01-backoffice-login/spec.md), [13](../13-openapi-docs-quality/spec.md), [one-app-per-module/03](../../../one-app-per-module/issues/03-mirror-test-layout/spec.md) · **PR:**

## Mục tiêu
Admin quản lý danh sách size và bảng màu chuẩn (tạo, đọc, sửa, ẩn) để Biến thể và bộ lọc dùng mã chuẩn, không dùng chuỗi tuỳ ý (US-805).

## Việc cần làm
- [ ] `modules/catalog/models/size.py`, `color.py`: `code` unique, `is_active`, thứ tự size, hex màu (constraint).
- [ ] Migration tạo bảng + data migration idempotent seed `FREESIZE`.
- [ ] `modules/catalog/services/`: create/update/ẩn; chặn xoá khi đã dùng.
- [ ] `modules/catalog/api/backoffice/`: `GET/POST sizes|colors` (phân trang), `PATCH sizes/{id}|colors/{id}`.
- [ ] Audit cho mọi write.

## Quyết định
- Quy tắc: BR-CAT-11, BR-CAT-02 (`FREESIZE`) — [04-business-rules](../../../../docs/business/04-business-rules.md).
- Schema: [03 §3.3–3.4](../../../../docs/architecture/03-data-model.md); seed: [03 §0.7](../../../../docs/architecture/03-data-model.md).
- Không có DELETE; ẩn bằng `is_active = false` — [04-api-contract](../../../../docs/architecture/04-api-contract.md).
- Validate tách field-level (serializer) và invariant cần DB (constraint/service).

## Acceptance criteria
- [ ] Admin tạo/list/patch size và màu; `code` unique, màu đúng định dạng hex.
- [ ] `FREESIZE` tồn tại sau migrate; chạy lại không tạo trùng.
- [ ] Size/màu đã gắn Biến thể chỉ chuyển inactive, không hard delete.
- [ ] Staff/Customer/anonymous không ghi được; write có audit.
- [ ] Migration, pagination, API/OpenAPI test xanh; `make fmt`, `make lint` sạch.

## Ghi chú
- Mentor viết test đỏ (create/list trước, rồi duplicate/hex/hide-used); người làm viết production code.
