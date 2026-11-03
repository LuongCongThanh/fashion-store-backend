# 11. Quy ước Git

> Trạng thái: **Đã chốt cho MVP** ([quy ước](../../README.md#trạng-thái-tài-liệu)). Các file cấu hình theo tài liệu này đã có trong repo (mục 9).
> Ngôn ngữ: tên nhánh, commit message, tiêu đề PR viết **tiếng Anh**; mô tả PR có thể viết tiếng Việt.

## 1. Mô hình nhánh

```mermaid
gitGraph
    commit id: "v0.1.0" tag: "v0.1.0"
    branch dev
    checkout dev
    commit id: "chore: init"
    branch feat/checkout-cod
    checkout feat/checkout-cod
    commit id: "wip"
    commit id: "add tests"
    checkout dev
    merge feat/checkout-cod id: "squash: feat(ordering)…" type: HIGHLIGHT
    branch fix/ipn-amount
    checkout fix/ipn-amount
    commit id: "fix"
    checkout dev
    merge fix/ipn-amount id: "squash: fix(payments)…" type: HIGHLIGHT
    commit id: "chore(release): v0.2.0"
    checkout main
    branch uat
    checkout uat
    merge dev id: "promote v0.2.0 lên uat"
    checkout main
    merge uat id: "release v0.2.0" tag: "v0.2.0"
    branch hotfix/vnpay-signature
    checkout hotfix/vnpay-signature
    commit id: "hotfix"
    commit id: "chore(release): v0.2.1"
    checkout main
    merge hotfix/vnpay-signature id: "squash: fix(payments)… " tag: "v0.2.1"
    checkout uat
    merge main id: "back-merge v0.2.1 vào uat"
    checkout dev
    merge uat id: "back-merge v0.2.1 vào dev"
```

> Trong sơ đồ, các merge có nhãn "squash" được vẽ như merge thường vì Mermaid không vẽ được squash. Trên thực tế, squash tạo **một commit mới** trên nhánh đích và không nối với nhánh nguồn.

| Nhánh | Vai trò | Tách từ | Merge vào | Triển khai tới |
|---|---|---|---|---|
| `main` | Code đang chạy production. Mỗi release có một tag | — | — | production |
| `uat` | Bản ứng viên release đang được nghiệm thu (UAT): người của doanh nghiệp kiểm tra nghiệp vụ trước khi lên production. Chỉ nhận merge từ `dev` và back-merge từ `main`, không commit thẳng | `main` (tạo một lần) | `main` | staging ([09](./09-deployment-aws-target.md) mục 3) |
| `dev` | Nơi gom các tính năng đã xong, chuẩn bị đưa lên `uat` | `main` (tạo một lần) | `uat` | — (chỉ CI; chưa có môi trường riêng) |
| `feat/*`, `fix/*`, `refactor/*`, `docs/*`, `chore/*`, `test/*` | Một tính năng, một lỗi hoặc một việc | `dev` | `dev` | — |
| `hotfix/*` | Sửa lỗi gấp trên production | `main` | `main`, sau đó back-merge về `uat` rồi `dev` | production |

Lỗi phát hiện khi nghiệm thu trên `uat` được sửa bằng nhánh `fix/*` vào `dev` như bình thường, rồi đưa `dev` lên `uat` lần nữa. Không sửa thẳng trên `uat`, để `uat` luôn là một phiên bản đã có trên `dev`.

## 2. Đặt tên nhánh

```
<loại>/<mô-tả-ngắn>
```

- `<loại>`: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `hotfix`.
- Tên nhánh không chứa mã ticket. Ticket là thư mục trong `.scratch/` (xem [docs/agents/issue-tracker.md](../agents/issue-tracker.md)); đường dẫn ticket ghi trong mô tả PR và footer `Refs:` của commit.
- `<mô-tả-ngắn>`: tiếng Anh, chữ thường, nối bằng dấu `-`, tối đa khoảng 5 từ.

| ✅ Đúng | ❌ Sai |
|---|---|
| `feat/checkout-cod` | `feature/Checkout_COD` |
| `fix/ipn-amount-mismatch` | `fix-bug` |
| `docs/adr-0013-payment-recovery` | `thanh/test` |
| `hotfix/vnpay-signature` | `hotfix` |

## 3. Commit message: Conventional Commits

```
<type>(<scope>)<!>: <mô tả ngắn, tiếng Anh, thì hiện tại, không viết hoa chữ đầu, không dấu chấm cuối>

[thân: giải thích VÌ SAO, có thể nhiều dòng]

[footer: BREAKING CHANGE: …, Refs: .scratch/checkout-cod/issues/02-reserve-stock]
```

### 3.1. `type`

| `type` | Khi nào | Ảnh hưởng phiên bản |
|---|---|---|
| `feat` | Thêm tính năng | Tăng MINOR |
| `fix` | Sửa lỗi | Tăng PATCH |
| `perf` | Cải thiện hiệu năng | Tăng PATCH |
| `refactor` | Sửa code, không đổi hành vi | — |
| `test` | Thêm hoặc sửa test | — |
| `docs` | Tài liệu, ADR, GLOSSARY | — |
| `build` | Dependency, Dockerfile, `pyproject.toml` | — |
| `ci` | Cấu hình CI | — |
| `chore` | Việc lặt vặt khác | — |
| `revert` | Hoàn tác một commit | Tuỳ commit bị hoàn tác |

Thay đổi làm gãy API hoặc contract sự kiện: thêm `!` sau scope **và** dòng `BREAKING CHANGE:` trong footer.

### 3.2. `scope`

Tên module hoặc khu vực: `identity`, `catalog`, `inventory`, `promotions`, `payments`, `shipping`, `ordering`, `notifications`, `shared`, `config`, `adr`, `glossary`, `ci`, `deps`. Không bắt buộc nhưng **nên có**.

### 3.3. Ví dụ

```
feat(ordering): add COD checkout with immediate stock decrement

fix(payments): reject VNPay IPN when amount mismatches

Previously the IPN handler trusted vnp_Amount. Now it compares against
payments_payment.amount and responds RspCode 04 (BR-PAY-04).

Refs: .scratch/vnpay-ipn/issues/01-check-amount

feat(ordering)!: split checkout and payment start into two endpoints

BREAKING CHANGE: POST /store/checkout no longer returns redirect_url;
call POST /store/orders/{code}/payments instead.

docs(adr): add 0007 events via outbox and celery
```

### 3.4. Kiểm tra tự động

- Hook `commit-msg` trong `pre-commit` (dùng `commitizen`) chặn commit sai định dạng ở máy local.
- CI kiểm tra **tiêu đề PR** theo cùng định dạng, vì khi squash thì tiêu đề PR trở thành commit message.

### 3.5. CI trên GitHub Actions

| Workflow | Job (tên status check) | Việc làm |
|---|---|---|
| `.github/workflows/ci.yml` | `secrets` | `gitleaks` quét toàn bộ lịch sử |
| | `pr-title` | Tiêu đề PR đúng Conventional Commits (chỉ chạy trên PR) |
| | `backend` | `ruff`, `mypy`, `gen_importlinter.py --check`, `lint-imports`, `gen_openapi.py --check`, `pytest`, coverage và `pip-audit` ([12-testing-strategy.md](./12-testing-strategy.md) mục 8). Tự bỏ qua khi chưa có `backend/pyproject.toml` |
| `.github/workflows/codeql.yml` | `codeql (actions)`, `codeql (python)` | CodeQL bộ `security-extended`, chạy trên PR, push lên `main` và mỗi thứ Hai |

`ci.yml` chạy khi push lên `main`, `uat`, `dev` và trên mọi PR.

`.github/dependabot.yml` cập nhật `github-actions`, `uv` và `docker` hằng tuần, chỉ đề xuất bản đã phát
hành ít nhất 7 ngày; đây không phải workflow hoặc status check.

Gate mục tiêu chưa hoạt động ở mốc hiện tại: kiểm tra migration lệch/trùng số. Không đánh dấu mục này đã
qua trong PR cho tới khi command và workflow tương ứng tồn tại. Khi thêm gate, cập nhật đồng thời mục này và
[12 mục 8](./12-testing-strategy.md#8-cổng-chặn-trong-ci).

Quy tắc cho mọi workflow, vì repo là public:

- Chỉ dùng trigger `pull_request`, **không** dùng `pull_request_target` (trigger này chạy code từ fork với quyền của repo).
- Khai báo `permissions: contents: read` ở cấp workflow; job nào cần thêm quyền thì tự khai báo kèm comment lý do.
- Action bên thứ ba được pin theo commit SHA, kèm comment phiên bản (`@<sha> # v7.0.1`). Dependabot cập nhật cả SHA và comment.
- `actions/checkout` dùng `persist-credentials: false`.

## 4. Pull Request và cách merge

### 4.1. Cách merge theo từng chặng

| Chặng | Cách merge | Lý do |
|---|---|---|
| `feat/*`, `fix/*`… → `dev` | **Squash merge** | Gộp các commit lặt vặt ("wip", "fix typo") thành **một commit** có tiêu đề chuẩn. Lịch sử `dev` sạch, dễ revert và dễ `git bisect` |
| `dev` → `uat` (đưa lên nghiệm thu) | **Merge commit**, **không squash** | Squash sẽ tạo trên `uat` một commit mà `dev` không có, khiến hai nhánh **lệch nhau** và sinh conflict ở mọi lần đưa lên sau |
| `uat` → `main` (release) | **Merge commit**, **không squash** | Cùng lý do; `main` chỉ nhận đúng bản đã được nghiệm thu trên `uat` |
| `hotfix/*` → `main` | **Squash merge** | Giống nhánh tính năng |
| `main` → `uat` → `dev` (back-merge sau hotfix) | **Merge commit** | Đưa bản sửa về `uat` và `dev` mà không làm lệch lịch sử |

Không dùng **rebase merge** trên GitHub.

### 4.2. Tiêu đề và nội dung PR

- **Tiêu đề** theo Conventional Commits, ví dụ `feat(ordering): add COD checkout`.
- **Nội dung** theo template `.github/pull_request_template.md`:
  - Mục *Summary* theo đúng các trường của template; đường dẫn ticket trong `.scratch/`, user story (`US-xxx`), quy tắc (`BR-xxx`).
  - Cách kiểm: test chứng minh từng acceptance criterion, bước kiểm tay nếu có.
  - **Gap và lưu ý** (bắt buộc, mục không có ghi "Không"): chưa làm, gap / rủi ro, quyết định tạm, ticket mới, chỗ reviewer cần chú ý, việc phải làm sau khi merge.
  - Checklist: có test; có migration (nếu đổi model); với thay đổi code đã chạy `make fmt`, `make lint`
    và test tương xứng; full suite trước merge/release; đã cập nhật tài liệu, GLOSSARY hoặc ADR nếu cần;
    không lộ secret.
- PR nên nhỏ: **dưới khoảng 400 dòng thay đổi**, không tính migration và file sinh tự động.

Các mục ở sidebar PR trên GitHub:

| Mục | Quy ước |
|---|---|
| Reviewers | Không gắn khi mới có một người làm. Tự review bằng `/mattpocock-skills:code-review` trước khi merge. Có người thứ hai thì gắn họ và nâng số người duyệt lên 1 (mục 6) |
| Assignees | Luôn gán người mở PR: `gh pr create --assignee @me` |
| Labels | Không dùng. Loại PR nằm ở tiêu đề, trạng thái ticket nằm ở dòng `Status:` trong `.scratch/` |
| Projects, Milestone | Không dùng. Phiên bản theo tag và `CHANGELOG.md` (mục 7) |
| Development | Để trống vì ticket không nằm trong GitHub Issues. Liên kết ticket bằng đường dẫn `.scratch/` trong mô tả PR và footer `Refs:` của commit |

### 4.3. PR đưa lên nghiệm thu `dev` → `uat` và PR release `uat` → `main`

| PR | Tiêu đề | Khi nào mở |
|---|---|---|
| `dev` → `uat` | `chore(uat): promote v0.2.0` (có version) hoặc `chore(uat): promote <mô tả>` (khi chưa có version, ví dụ chỉ có tài liệu) | Khi `dev` đã gom đủ việc cho một bản và CI xanh |
| `uat` → `main` | `chore(release): v0.2.0` | Chỉ khi bản trên `uat` đã được nghiệm thu trên staging |

- Không dùng `release: …` vì `release` không phải `type` hợp lệ (mục 3.1), job `pr-title` sẽ chặn.
- Nội dung: danh sách thay đổi (lấy từ phần mới của `CHANGELOG.md` vừa cập nhật trên `dev`, mục 5.3), migration cần chạy, cấu hình hoặc biến môi trường mới. PR release ghi thêm ai đã nghiệm thu và lúc nào.

## 5. Quy trình làm việc hằng ngày

### 5.0. Preflight an toàn

Trước `rebase`, bump version, merge hoặc tag, dừng nếu worktree không sạch hoặc đang ở sai branch:

```bash
git status --short
git branch --show-current
git fetch --prune --tags origin
```

- `git status --short` phải không có output, trừ khi bước tiếp theo chủ ý commit đúng các file đang hiện.
- Không stash ngầm trong runbook release. Commit hoặc cất thay đổi có chủ đích rồi chạy lại preflight.
- Dùng `git pull --ff-only`; nếu không fast-forward được thì kiểm tra lịch sử, không tạo merge commit ngoài
  quy trình chỉ để làm lệnh chạy qua.
- Trước khi tag, xác nhận `HEAD`, `origin/main`, version trong `pyproject.toml` và commit đã nghiệm thu là
  cùng phiên bản. Lệnh thành công không thay thế việc đọc SHA/commit message.
- Các placeholder như `v0.2.0`, tên branch và số PR phải được thay bằng giá trị của release hiện tại;
  không chạy nguyên văn.

### 5.1. Làm một tính năng

```bash
git switch dev
git pull --ff-only origin dev
git switch -c feat/checkout-cod
# … code, commit …
git fetch origin
git rebase origin/dev
git push -u origin feat/checkout-cod
```

- **Không giới hạn** thời gian sống của nhánh tính năng. Nhánh càng sống lâu thì càng phải cập nhật `dev` vào thường xuyên (như lệnh `rebase` ở trên) để tránh conflict lớn khi merge.
- Sau khi đã push mà phải rebase, dùng `git push --force-with-lease`; không dùng `--force`. Chỉ rewrite
  branch cá nhân; branch có người khác cùng làm phải phối hợp trước.
- Nếu rebase conflict: sửa file, `git add <file>`, `git rebase --continue`; không chắc cách giải thì
  `git rebase --abort` để trở về trạng thái trước rebase.
- **Không bao giờ** force-push lên `dev`, `uat` hoặc `main`.
- Xoá nhánh sau khi merge (bật tự động xoá trên GitHub).

### 5.2. Push gấp vào `dev`

Được phép push thẳng vào `dev` khi **cả hai** điều kiện sau đều đúng:

1. Thay đổi **nhỏ và gấp**, ví dụ sửa một test hỏng đang chặn người khác.
2. Với thay đổi code, đã chạy `make fmt`, `make lint` và full `make test` ở máy local.

Commit vẫn phải đúng Conventional Commits. CI vẫn chạy sau khi push; nếu CI đỏ thì người push phải sửa ngay.

Commit `chore(release): vX.Y.Z` ở mục 5.3 cũng được push thẳng vào `dev`, vì chỉ đổi version và CHANGELOG.

### 5.3. Release

`uat` và `main` cấm push thẳng, nên version và CHANGELOG được cập nhật trên `dev` **trước** khi đưa lên `uat`. Bản đi qua `uat` và vào `main` là đúng bản đó. Tag chỉ gắn sau khi merge, trên commit merge của `main`.

```bash
# 1. Trên dev: cập nhật version và CHANGELOG, KHÔNG tạo tag
git switch dev
git pull --ff-only origin dev
git status --short               # phải sạch
cd backend
cz bump --version-files-only     # tính version mới từ commit kể từ tag trước, ghi vào pyproject.toml
version="v$(cz version --project)"
cz changelog --incremental --unreleased-version "$version"
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): $version"
git push
# 2. Mở PR dev → uat, tiêu đề "chore(uat): promote v0.2.0", merge bằng merge commit
#    → triển khai lên staging, người của doanh nghiệp nghiệm thu
# 3. Mở PR uat → main, tiêu đề "chore(release): v0.2.0", merge bằng merge commit
# 4. Sau khi PR đã merge và CI production commit xanh, xác minh rồi gắn tag
git fetch --prune --tags origin
git switch main
git pull --ff-only origin main
git status --short               # phải sạch
git log -1 --oneline             # phải là merge commit của đúng PR release
git merge-base --is-ancestor origin/uat HEAD
version=v0.2.0                   # thay bằng version ghi trong PR release
test "$(cz version --project)" = "${version#v}"
test -z "$(git tag --list "$version")"
git tag -a "$version" HEAD -m "$version"
git push origin "$version"
```

Không tag chỉ vì PR đã đóng: phải là trạng thái **Merged**, commit trên `main` phải chứa đúng tip `uat` đã
nghiệm thu và version phải khớp. Ghi SHA được nghiệm thu vào PR release để người gắn tag đối chiếu.

Cờ của `cz` ở trên đã kiểm tra với `commitizen` 4.19.3, bản pin trong `backend/pyproject.toml` và `.pre-commit-config.yaml`. Cờ `--files-only` cũ đã bị deprecate, thay bằng `--version-files-only`.

### 5.4. Hotfix

```bash
git switch main
git pull --ff-only origin main
git status --short
git switch -c hotfix/vnpay-signature
# … sửa, commit …
# cập nhật version và CHANGELOG ngay trong nhánh hotfix, như bước 1 của mục 5.3
cd backend
cz bump --version-files-only
version="v$(cz version --project)"
cz changelog --incremental --unreleased-version "$version"
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): $version"
git push -u origin hotfix/vnpay-signature
# mở PR hotfix/vnpay-signature → main, chờ CI xanh và squash merge trên GitHub

# CHỈ chạy phần dưới sau khi PR ở trạng thái Merged
git fetch --prune --tags origin
git switch main
git pull --ff-only origin main
git log -1 --oneline             # phải là squash commit của đúng hotfix
version=v0.2.1                   # thay bằng version của hotfix vừa merge
test "$(cz version --project)" = "${version#v}"
test -z "$(git tag --list "$version")"
git tag -a "$version" HEAD -m "$version"
git push origin "$version"

# Back-merge tuần tự; mỗi PR phải được merge trước khi mở chặng tiếp theo
gh pr create --base uat --head main --title "chore: back-merge $version into uat"
# chờ CI xanh và merge PR main → uat bằng merge commit
gh pr create --base dev --head uat --title "chore: back-merge $version into dev"
# chờ CI xanh và merge PR uat → dev bằng merge commit
```

Không chạy lệnh tạo PR `uat → dev` trước khi PR `main → uat` đã merge. Sau mỗi chặng, `git fetch origin`
và dùng `git merge-base --is-ancestor <sha-hotfix-trên-main> origin/<nhánh-đích>` để xác nhận hotfix đã có
trong nhánh đích.

### 5.5. PR xếp chồng

Khi một PR mới cần dựa trên một PR khác chưa merge (ví dụ PR B sửa tiếp các file của PR A):

1. Tạo nhánh B từ nhánh A, mở PR B với base là nhánh A, để reviewer chỉ thấy phần của B. Ghi "Merge sau #<A>" trong mô tả.
2. Sau khi PR A được squash merge vào `dev`, chạy các lệnh dưới rồi đổi base PR B sang `dev`:

```bash
git fetch origin
git switch <nhánh-B>
git rebase --onto origin/dev <nhánh-A> <nhánh-B>
git diff --stat origin/dev...HEAD
git diff origin/dev...HEAD
git push --force-with-lease
gh pr edit <PR-B> --base dev
```

Phải dùng `--onto` vì squash merge tạo trên `dev` một commit mới, nên các commit cũ của nhánh A không có trong lịch sử của `dev`.

### 5.6. Dừng, phục hồi và hoàn tác

| Tình huống | Cách xử lý an toàn |
|---|---|
| Rebase đang conflict, chưa chắc cách giải | `git rebase --abort` |
| Merge local đang conflict, chưa commit | `git merge --abort` |
| Nhánh tính năng đã rebase | Kiểm tra `git range-diff`, rồi `git push --force-with-lease`; không `--force` |
| Squash commit đã merge cần hoàn tác | Tạo branch từ nhánh đích, chạy `git revert <sha>`, mở PR |
| Merge commit release/back-merge cần hoàn tác | Không tự chạy ngay; xác định mainline rồi dùng `git revert -m 1 <sha>` trong PR riêng |
| UAT không đạt | Không merge `uat → main`; sửa bằng branch từ `dev`, merge vào `dev`, rồi promote lại |
| Tag mới tạo local, chưa push, bị sai | Xoá tag local rồi tạo lại sau khi xác minh SHA |
| Tag đã push hoặc production đã deploy | Dừng; không tự xoá/di chuyển tag. Phối hợp release owner và tạo hotfix/release mới |

Không dùng `git reset --hard` hoặc sửa lịch sử nhánh dùng chung để “rollback”. Production rollback là một
quyết định deployment/data migration; Git revert chỉ tạo commit đảo code và không tự hoàn tác dữ liệu.

## 6. Bảo vệ nhánh (GitHub)

| Thiết lập | `main` | `uat` | `dev` |
|---|---|---|---|
| Cấm push thẳng, bắt buộc qua PR | ✅ | ✅ | — (cho phép push gấp, mục 5.2) |
| Cần ít nhất 1 người duyệt | ⏳ Tạm để 0 vì mới có một người làm; nâng lên 1 khi có người thứ hai | ⏳ Như `main` | — |
| Bắt buộc CI xanh trước khi merge (các check ở mục 3.5) | ✅ | ✅ | — (CI vẫn chạy sau khi push) |
| Nhánh phải cập nhật với nhánh đích trước khi merge | ✅ | ✅ | — |
| Cách merge được phép | Merge commit (PR release) và squash (hotfix) | Chỉ merge commit | — (quy ước: chỉ squash cho PR thường, mục 4.1; ruleset không ép để giữ quyền push gấp) |
| Cấm force-push | ✅ | ✅ | ✅ |
| Cấm xoá nhánh | ✅ | ✅ | ✅ |

Mỗi nhánh có một ruleset cùng tên (Settings → Rules → Rulesets), không ai được bypass. Ruleset `dev` chỉ gồm cấm force-push và cấm xoá nhánh; push thẳng vẫn được phép (mục 5.2).

Ruleset `dev` chưa bắt buộc status check để giữ ngoại lệ push gấp, nhưng PR thường vào `dev` **không được
merge khi CI đỏ hoặc còn pending**. Đây là quy ước review; ngoại lệ duy nhất là push gấp đủ điều kiện tại
mục 5.2, và người push phải theo dõi CI sau push.

## 7. Phiên bản và CHANGELOG

- **SemVer** `vMAJOR.MINOR.PATCH`. Giữ `0.x.y` cho tới khi go-live; bản go-live là `v1.0.0`.
- Tag chỉ gắn trên `main`, trên commit merge của PR release `uat` → `main` (hoặc commit squash của PR hotfix), và chỉ gắn **sau** khi merge.
- Bản chỉ có tài liệu, trước khi có `backend/pyproject.toml`, đi qua `uat` và `main` như bình thường nhưng **không** gắn tag và không bump version; tag `v0.1.0` dành cho release đầu tiên có code.
- `backend/CHANGELOG.md` sinh bằng `commitizen` từ các commit Conventional Commits, cập nhật trên `dev` (release) hoặc trong nhánh `hotfix/*` (hotfix), rồi đi vào `main` qua PR.
- Phiên bản ghi trong `backend/pyproject.toml`, được `commitizen` cập nhật trong commit `chore(release): vX.Y.Z`. `commitizen` cấu hình đọc version từ `[project].version` và dùng tag dạng `v$version`.
- Không chạy `cz bump` ở chế độ mặc định (tự commit và tự gắn tag), vì tag sẽ nằm trên `dev` chứ không phải `main`.

## 8. Những thứ không được commit

| Loại | Ví dụ |
|---|---|
| Secret | `.env`, `.secrets/`, khoá JWT, mật khẩu, secret VNPay/MoMo/GHN |
| File sinh ra khi chạy | `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `htmlcov/`, `.coverage` |
| Dữ liệu local | `media/`, file dump database |
| Cấu hình cá nhân | `.idea/` (PyCharm), `.vscode/` **trừ** `launch.json` và `extensions.json`, `.DS_Store`, `Thumbs.db` |
| Môi trường ảo | `.venv/` |

Cấu hình IDE **được** commit: `.vscode/launch.json`, `.vscode/extensions.json`, `.run/*.run.xml` (run configuration của PyCharm), `.editorconfig` (xem [08-local-development.md](./08-local-development.md) mục 6).

Repo có `.gitattributes` với `* text=auto eol=lf` để mọi file dùng ký tự xuống dòng LF, tránh lỗi khi người dùng Windows và macOS cùng làm việc.

Hook `pre-commit` (`.pre-commit-config.yaml`) chặn commit nhầm bằng:

- `gitleaks`: secret dạng chuỗi (secret VNPay/MoMo/GHN, API key, token).
- `detect-private-key`: khoá dạng PEM.
- `check-added-large-files`: file lớn.

Repo là public, nên dữ liệu mẫu trong test và fixture phải là giá trị giả rõ ràng (ví dụ `test-hash-secret`), không bao giờ là secret hay dữ liệu khách hàng thật. Không thêm allowlist rộng cho `gitleaks`; nếu bị báo nhầm thì đổi giá trị mẫu.

## 9. Việc làm một lần khi áp dụng (đã xong)

Các việc dưới đây đã làm xong: không còn nhánh `master` và hai nhánh Frontend cũ, `main` có ruleset, các file cấu hình đã có trong repo. Giữ lại để biết repo đã được thiết lập thế nào.

1. Gộp nội dung `master` vào `main`, đặt `main` làm nhánh mặc định trên GitHub, rồi xoá `master` (**sẽ hỏi lại trước khi thao tác trên remote**).
2. Tạo `dev` từ `main`.
3. Xử lý hai nhánh cũ `feature/create-header` và `feature/setup-method-api-and-error` (thuộc Frontend cũ): giữ lại để tham khảo hay xoá.
4. Cấu hình bảo vệ nhánh như mục 6.
5. Tạo `.gitignore`, `.gitattributes`, `.editorconfig`, PR template, `CONTRIBUTING.md`, cấu hình IDE dùng chung (`.vscode/launch.json`, `.vscode/extensions.json`, `.run/*.run.xml`), và thêm hook `commitizen` vào `.pre-commit-config.yaml`.
