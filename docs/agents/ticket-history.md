# Lịch sử ticket

Thứ tự hoàn thành thực tế của ticket trong `.scratch/`, theo thời điểm PR merge vào `dev`. Số ticket là ID cố định, không đánh lại; vì vậy thứ tự ở đây khác thứ tự số. Nguồn sự thật vẫn là dòng `Status:` của từng ticket ([issue-tracker](./issue-tracker.md)).

Đóng ticket thì thêm một dòng vào cuối phần **Đã xong** của feature và bỏ ticket khỏi phần **Còn mở**, trong cùng PR.

## `dev-security-baseline`

[Spec](../../.scratch/dev-security-baseline/spec.md)

### Đã xong

1. [01](../../.scratch/dev-security-baseline/issues/01-pre-commit-and-agent-guard/spec.md) · `pre-commit`, ruff `S`, rule deny cho Claude Code · PR #4 · 26/10/2026
2. [02](../../.scratch/dev-security-baseline/issues/02-ci-and-dependabot/spec.md) · CI workflow, CodeQL, Dependabot, trivy · PR #4 · 26/10/2026

### Còn mở

- [03](../../.scratch/dev-security-baseline/issues/03-github-settings-and-security-policy/spec.md) · cấu hình GitHub và `SECURITY.md` · `ready-for-human`

## `backend-bootstrap` (M0)

[Spec](../../.scratch/backend-bootstrap/spec.md)

### Đã xong

1. [06](../../.scratch/backend-bootstrap/issues/06-align-local-env-docs/spec.md) · thống nhất tài liệu môi trường local và hook pre-commit · PR #16 · 29/10/2026
2. [07](../../.scratch/backend-bootstrap/issues/07-project-skeleton/spec.md) · pyproject, settings, health check, `make lint`/`test`/`fmt`, job CI `backend` · PR #20 · 29/10/2026
3. [08](../../.scratch/backend-bootstrap/issues/08-local-postgres-installer/spec.md) · bộ cài PostgreSQL trên Windows (`postgres.ps1`, không dùng WSL2) · PR #21 · 29/10/2026
4. [09](../../.scratch/backend-bootstrap/issues/09-shared-core/spec.md) · BaseModel, Money, phones, privacy, lỗi, logging, extension PostgreSQL · PR #22 · 29/10/2026
5. [16](../../.scratch/backend-bootstrap/issues/16-shared-api-layer/spec.md) · `ErrorDTO`, pagination, permissions, `client_ip`, throttling, i18n · PR #24 · 29/10/2026
6. [15](../../.scratch/backend-bootstrap/issues/15-docker-compose-local/spec.md) · Dockerfile, Compose, lệnh Makefile dùng container, `sync_beat_schedule` · PR #27 · 30/10/2026
7. [17](../../.scratch/backend-bootstrap/issues/17-shared-geo/spec.md) · địa giới hành chính, `load_geo` · PR #31 · 30/10/2026
8. [10](../../.scratch/backend-bootstrap/issues/10-shared-events-outbox/spec.md) · outbox, relay, consumer, retry · PR #36 · 30/10/2026
9. [18](../../.scratch/backend-bootstrap/issues/18-outbox-operations/spec.md) · lệnh vận hành và theo dõi outbox · PR #38 · 30/10/2026
10. [11](../../.scratch/backend-bootstrap/issues/11-shared-idempotency/spec.md) · `Idempotency-Key` · PR #40 · 30/10/2026
11. [12](../../.scratch/backend-bootstrap/issues/12-account-bootstrap/spec.md) · model `Account` và `create_staff` · PR #42 · 31/10/2026
12. [21](../../.scratch/backend-bootstrap/issues/21-validate-database-url/spec.md) · từ chối `DATABASE_URL` sai định dạng ngay khi đọc env · PR #45 · 31/10/2026
13. [24](../../.scratch/backend-bootstrap/issues/24-outbox-killed-handler-redispatch/spec.md) · delivery bị kill liên tục chuyển `failed` sau 3 lần chạy dở (`interrupted_runs`) · PR #47 · 31/10/2026
14. [27](../../.scratch/backend-bootstrap/issues/27-outbox-invalid-payload-fails-fast/spec.md) · payload không parse được bằng class sự kiện thì delivery `failed` ngay, không retry · PR #49 · 01/11/2026
15. [23](../../.scratch/backend-bootstrap/issues/23-makefile-utf8-output/spec.md) · `Makefile` và hook `lint-imports` chạy Python ở chế độ UTF-8 trên Windows · PR #52 · 01/11/2026
16. [22](../../.scratch/backend-bootstrap/issues/22-openapi-error-responses/spec.md) · `ErrorDTO` và response lỗi mặc định trong OpenAPI (`shared.api.schema.AutoSchema`) · PR #54 · 01/11/2026

### Còn mở

Chia nhóm theo quyết định 30/10/2026 trong [roadmap](../../.scratch/mvp-roadmap/map.md).

Làm xen kẽ, không chặn mốc:

- [01](../../.scratch/backend-bootstrap/issues/01-services-coverage-gate/spec.md) · cổng coverage cho `services` và `handlers` · `ready-for-agent`
- [02](../../.scratch/backend-bootstrap/issues/02-pytest-markers-and-br-report/spec.md) · marker pytest và `make br-report` · `ready-for-agent`
- [03](../../.scratch/backend-bootstrap/issues/03-openapi-schema-drift-check/spec.md) · commit `openapi.yaml` và chặn schema lệch · `ready-for-agent`
- [04](../../.scratch/backend-bootstrap/issues/04-import-linter-test-factories/spec.md) · `gen_importlinter.py` và import-linter · `ready-for-agent`
- [14](../../.scratch/backend-bootstrap/issues/14-trivy-and-dependabot-backend/spec.md) · quét image bằng trivy, Dependabot cho `backend/` · `ready-for-agent`
- [19](../../.scratch/backend-bootstrap/issues/19-trust-upstream-request-id/spec.md) · dùng `X-Request-ID` từ BFF làm `request_id` · `ready-for-agent`
- [20](../../.scratch/backend-bootstrap/issues/20-dependabot-compose-images/spec.md) · Dependabot theo dõi image trong Compose · `ready-for-agent`

Trước go-live:

- [13](../../.scratch/backend-bootstrap/issues/13-local-postgres-installer-macos/spec.md) · bộ cài PostgreSQL trên macOS · `ready-for-human`
- [25](../../.scratch/backend-bootstrap/issues/25-outbox-relay-throughput/spec.md) · relay xả tồn đọng nhanh hơn 100 delivery mỗi giây · `ready-for-agent`
- [26](../../.scratch/backend-bootstrap/issues/26-outbox-refactor-smells/spec.md) · gom chuyển trạng thái delivery và helper test · `ready-for-agent`
- [28](../../.scratch/backend-bootstrap/issues/28-outbox-operations-hardening/spec.md) · độ bền của theo dõi và purge outbox khi tồn đọng lớn · `ready-for-agent`

## `sandbox-acceptance` (M7)

Chưa có spec.

### Còn mở

- [01](../../.scratch/sandbox-acceptance/issues/01-load-test-k6-staging/spec.md) · test tải bằng k6 trên staging · `needs-triage`
