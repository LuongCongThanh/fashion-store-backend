# 14 – Quét image bằng trivy và xác nhận Dependabot cho `backend/`

Status: ready-for-agent · Ưu tiên: 16 · Blocked by: [15](../15-docker-compose-local/spec.md) (đã resolved) · **PR:**

Spec: [spec.md](../../spec.md)

## Mục tiêu
CI chặn image có lỗ hổng nghiêm trọng đã có bản vá, và Dependabot theo dõi đủ `uv`, `docker`, `github-actions` mà không báo lỗi. Tách từ [dev-security-baseline/02](../../../dev-security-baseline/issues/02-ci-and-dependabot/spec.md) vì cần `pyproject.toml` và `Dockerfile` (ticket 07, 15).

## Việc cần làm
- [ ] Thêm job `trivy` vào `.github/workflows/ci.yml`: build image từ `Dockerfile` rồi quét, fail khi có `CRITICAL`/`HIGH` đã có bản vá (`ignore-unfixed: true`). Pin action theo commit SHA kèm comment phiên bản.
- [ ] Thêm `trivy` vào required status checks của ruleset `main` (id 25858832).
- [ ] Ghi `trivy` vào danh sách check bắt buộc ở [11-git-workflow.md](../../../../docs/architecture/11-git-workflow.md).
- [ ] Kiểm tra Dependabot nhận đủ 3 hệ sinh thái `uv`, `docker`, `github-actions`.

## Quyết định
- Tên job cố định là `trivy` (ruleset bám theo tên job).
- Agent chỉ chạy lệnh `gh` đổi ruleset sau khi chủ repo xác nhận.

## Acceptance criteria
- [ ] Job `trivy` chạy xanh trên PR có `Dockerfile`.
- [ ] `trivy` nằm trong required status checks của ruleset `main`.
- [ ] Dependabot nhận đủ 3 hệ sinh thái (Insights → Dependency graph → Dependabot), không còn lỗi ở `uv` và `docker`.

## Ghi chú
- Nếu [one-app-per-module/01](../../../one-app-per-module/issues/01-flatten-repo-root/spec.md) đã merge thì `Dockerfile` và `directory` của Dependabot ở gốc repo, không còn `backend/`.
