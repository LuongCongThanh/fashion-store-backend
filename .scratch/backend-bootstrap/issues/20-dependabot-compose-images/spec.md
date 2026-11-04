# 20 – Dependabot theo dõi image trong `docker-compose.yml`

Status: ready-for-agent · Ưu tiên: 17 · Blocked by: [15](../15-docker-compose-local/spec.md) (đã resolved) · **PR:**

Spec: [spec.md](../../spec.md)

## Mục tiêu
Image ghim trong Compose (`valkey/valkey:8.1.11`, `axllent/mailpit:v1.31.6`) được Dependabot đề xuất cập nhật, và Valkey của Compose luôn cùng bản với CI. Tách từ review ticket 15 ngày 29/10/2026.

## Việc cần làm
- [ ] Thêm hệ sinh thái `docker-compose` vào `.github/dependabot.yml`, cùng `cooldown` 7 ngày và cách gom PR như các mục khác.
- [ ] Chọn cách giữ Valkey của Compose và service trong `.github/workflows/ci.yml` cùng bản khi Dependabot chỉ sửa một chỗ.
- [ ] Ghi cách đó vào [08 mục 7](../../../../docs/architecture/08-local-development.md).

## Quyết định
- Hệ `docker` chỉ đọc `Dockerfile`, không đọc `docker-compose.yml`, nên phải thêm hệ `docker-compose` riêng.
- Ticket [14](../14-trivy-and-dependabot-backend/spec.md) chỉ kiểm 3 hệ `uv`, `docker`, `github-actions`; `docker-compose` thuộc ticket này.

## Acceptance criteria
- [ ] Dependabot nhận hệ sinh thái `docker-compose` và không báo lỗi.
- [ ] Có cách giữ bản Valkey của Compose và CI trùng nhau, ghi trong 08 mục 7.

## Ghi chú
- `directory` là `/backend` nếu chưa merge [one-app-per-module/01](../../../one-app-per-module/issues/01-flatten-repo-root/spec.md), là `/` nếu đã merge.
