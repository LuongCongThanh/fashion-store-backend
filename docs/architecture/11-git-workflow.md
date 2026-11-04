# 11. Quy ước Git

> Trạng thái: **Đã chốt cho MVP** ([quy ước](../../README.md#trạng-thái-tài-liệu)). Các file cấu hình theo tài liệu này đã có trong repo (mục 9).
> Ngôn ngữ: tên nhánh, commit message, tiêu đề PR viết **tiếng Anh**; mô tả PR có thể viết tiếng Việt.

## 1. Mô hình nhánh

Luồng: nhánh việc → `dev` (squash) → `uat` (merge commit) → `main` (merge commit, tag). Hotfix: `hotfix/*` → `main` (squash, tag) → back-merge `uat` → `dev`. Squash tạo **một commit mới** trên nhánh đích, không nối với nhánh nguồn. Chi tiết ở mục 4.1, 5.3, 5.4.

| Nhánh | Vai trò | Tách từ | Merge vào | Triển khai tới |
|---|---|---|---|---|
| `main` | Code đang chạy production. Mỗi release có một tag | — | — | production |
| `uat` | Bản ứng viên release đang nghiệm thu (UAT): doanh nghiệp kiểm tra nghiệp vụ trước production. Chỉ nhận merge từ `dev` và back-merge từ `main`, không commit thẳng | `main` (một lần) | `main` | staging ([09](./09-deployment-aws-target.md) mục 3) |
| `dev` | Gom các tính năng đã xong, chuẩn bị lên `uat` | `main` (một lần) | `uat` | — (chỉ CI; chưa có môi trường riêng) |
| `feat/*`, `fix/*`, `refactor/*`, `docs/*`, `chore/*`, `test/*` | Một tính năng, một lỗi hoặc một việc | `dev` | `dev` | — |
| `hotfix/*` | Sửa lỗi gấp trên production | `main` | `main`, rồi back-merge về `uat` rồi `dev` | production |

Lỗi phát hiện khi nghiệm thu: sửa bằng `fix/*` vào `dev`, rồi đưa `dev` lên `uat` lại. Không sửa thẳng trên `uat`, để `uat` luôn là một phiên bản đã có trên `dev`.

## 2. Đặt tên nhánh

`<loại>/<mô-tả-ngắn>`

- `<loại>`: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `hotfix`.
- `<mô-tả-ngắn>`: tiếng Anh, chữ thường, nối bằng `-`, tối đa khoảng 5 từ.
- Không chứa mã ticket. Ticket là thư mục trong `.scratch/` ([issue-tracker.md](../agents/issue-tracker.md)); đường dẫn ghi trong mô tả PR và footer `Refs:` của commit.

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

- Local: hook `commit-msg` trong `pre-commit` (`commitizen`) chặn commit sai định dạng.
- CI: kiểm tra **tiêu đề PR** cùng định dạng, vì khi squash tiêu đề PR thành commit message.

### 3.5. CI trên GitHub Actions

| Workflow | Job (tên status check) | Việc làm |
|---|---|---|
| `.github/workflows/ci.yml` | `secrets` | `gitleaks` quét toàn bộ lịch sử |
| | `pr-title` | Tiêu đề PR đúng Conventional Commits (chỉ chạy trên PR) |
| | `backend` | `ruff`, `mypy`, `gen_importlinter.py --check`, `lint-imports`, `gen_openapi.py --check`, `pytest`, coverage và `pip-audit` ([12-testing-strategy.md](./12-testing-strategy.md) mục 8). Tự bỏ qua khi chưa có `backend/pyproject.toml` |
| `.github/workflows/codeql.yml` | `codeql (actions)`, `codeql (python)` | CodeQL bộ `security-extended`, chạy trên PR, push lên `main` và mỗi thứ Hai |

- `ci.yml` chạy khi push lên `main`, `uat`, `dev` và trên mọi PR.
- `.github/dependabot.yml` (không phải workflow hay status check) cập nhật `github-actions`, `uv`, `docker` hằng tuần, chỉ đề xuất bản đã phát hành ít nhất 7 ngày.
- Gate chưa hoạt động: kiểm tra migration lệch/trùng số. Không đánh dấu đã qua trong PR cho tới khi command và workflow tồn tại. Khi thêm gate, cập nhật cả mục này và [12 mục 8](./12-testing-strategy.md#8-cổng-chặn-trong-ci).

Quy tắc cho mọi workflow (repo public):

- Chỉ dùng trigger `pull_request`, **không** dùng `pull_request_target` (chạy code từ fork với quyền của repo).
- `permissions: contents: read` ở cấp workflow; job cần thêm quyền tự khai báo kèm comment lý do.
- Action bên thứ ba pin theo commit SHA kèm comment phiên bản (`@<sha> # v7.0.1`); Dependabot cập nhật cả hai.
- `actions/checkout` dùng `persist-credentials: false`.

## 4. Pull Request và cách merge

### 4.1. Cách merge theo từng chặng

| Chặng | Cách merge | Lý do |
|---|---|---|
| `feat/*`, `fix/*`… → `dev` | **Squash merge** | Gộp commit lặt vặt thành **một commit** tiêu đề chuẩn; lịch sử `dev` sạch, dễ revert và `git bisect` |
| `dev` → `uat` (đưa lên nghiệm thu) | **Merge commit**, **không squash** | Squash tạo trên `uat` commit mà `dev` không có, hai nhánh **lệch nhau** và conflict ở mọi lần đưa lên sau |
| `uat` → `main` (release) | **Merge commit**, **không squash** | Cùng lý do; `main` chỉ nhận đúng bản đã nghiệm thu trên `uat` |
| `hotfix/*` → `main` | **Squash merge** | Giống nhánh tính năng |
| `main` → `uat` → `dev` (back-merge sau hotfix) | **Merge commit** | Đưa bản sửa về mà không lệch lịch sử |

Không dùng **rebase merge** trên GitHub.

### 4.2. Tiêu đề và nội dung PR

- **Tiêu đề** theo Conventional Commits, ví dụ `feat(ordering): add COD checkout`.
- **Nội dung** theo `.github/pull_request_template.md`:
  - *Summary* theo đúng các trường template; đường dẫn ticket `.scratch/`, user story (`US-xxx`), quy tắc (`BR-xxx`).
  - Cách kiểm: test chứng minh từng acceptance criterion, bước kiểm tay nếu có.
  - **Gap và lưu ý** (bắt buộc, mục trống ghi "Không"): chưa làm, gap / rủi ro, quyết định tạm, ticket mới, chỗ reviewer cần chú ý, việc sau khi merge.
  - Checklist: có test; có migration (nếu đổi model); với thay đổi code đã chạy `make fmt`, `make lint` và test tương xứng; full suite trước merge/release; đã cập nhật tài liệu, GLOSSARY hoặc ADR nếu cần; không lộ secret.
- PR nên nhỏ: **dưới khoảng 400 dòng thay đổi**, không tính migration và file sinh tự động.

Sidebar PR trên GitHub:

| Mục | Quy ước |
|---|---|
| Reviewers | Không gắn khi mới có một người làm; tự review bằng `/mattpocock-skills:code-review` trước khi merge. Có người thứ hai thì gắn họ và nâng số người duyệt lên 1 (mục 6) |
| Assignees | Luôn gán người mở PR: `gh pr create --assignee @me` |
| Labels | Không dùng. Loại PR ở tiêu đề, trạng thái ticket ở dòng `Status:` trong `.scratch/` |
| Projects, Milestone | Không dùng. Phiên bản theo tag và `CHANGELOG.md` (mục 7) |
| Development | Để trống (ticket không ở GitHub Issues); liên kết bằng đường dẫn `.scratch/` trong mô tả PR và footer `Refs:` |

### 4.3. PR đưa lên nghiệm thu `dev` → `uat` và PR release `uat` → `main`

| PR | Tiêu đề | Khi nào mở |
|---|---|---|
| `dev` → `uat` | `chore(uat): promote v0.2.0`, hoặc `chore(uat): promote <mô tả>` khi chưa có version (ví dụ chỉ có tài liệu) | `dev` đã gom đủ việc cho một bản và CI xanh |
| `uat` → `main` | `chore(release): v0.2.0` | Chỉ khi bản trên `uat` đã nghiệm thu trên staging |

- Không dùng `release: …`: `release` không phải `type` hợp lệ (mục 3.1), job `pr-title` sẽ chặn.
- Nội dung: danh sách thay đổi (phần mới của `CHANGELOG.md` vừa cập nhật trên `dev`, mục 5.3), migration cần chạy, cấu hình hoặc biến môi trường mới. PR release ghi thêm ai nghiệm thu, lúc nào.

## 5. Quy trình làm việc hằng ngày

### 5.0. Preflight an toàn

Trước `rebase`, bump version, merge hoặc tag, dừng nếu worktree không sạch hoặc sai branch:

```bash
git status --short
git branch --show-current
git fetch --prune --tags origin
```

- `git status --short` phải rỗng, trừ khi bước tiếp theo chủ ý commit đúng các file đang hiện.
- Không stash ngầm trong runbook release; commit hoặc cất thay đổi có chủ đích rồi chạy lại preflight.
- Dùng `git pull --ff-only`; không fast-forward được thì kiểm tra lịch sử, không tạo merge commit ngoài quy trình chỉ để lệnh chạy qua.
- Trước khi tag, xác nhận `HEAD`, `origin/main`, version trong `pyproject.toml` và commit đã nghiệm thu cùng phiên bản. Lệnh thành công không thay việc đọc SHA/commit message.
- Placeholder (`v0.2.0`, tên branch, số PR) phải thay bằng giá trị của release hiện tại; không chạy nguyên văn.

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

- **Không giới hạn** thời gian sống của nhánh; sống càng lâu càng phải rebase lên `dev` thường xuyên để tránh conflict lớn.
- Đã push mà phải rebase: `git push --force-with-lease`, không `--force`. Chỉ rewrite branch cá nhân; branch nhiều người làm phải phối hợp trước.
- Rebase conflict: sửa file, `git add <file>`, `git rebase --continue`; không chắc thì `git rebase --abort`.
- **Không bao giờ** force-push lên `dev`, `uat` hoặc `main`.
- Xoá nhánh sau khi merge (bật tự động xoá trên GitHub).

### 5.2. Push gấp vào `dev`

Được push thẳng vào `dev` khi **cả hai** điều kiện đúng:

1. Thay đổi **nhỏ và gấp**, ví dụ sửa test hỏng đang chặn người khác.
2. Với thay đổi code, đã chạy `make fmt`, `make lint` và full `make test` ở local.

Commit vẫn đúng Conventional Commits. CI vẫn chạy sau push; CI đỏ thì người push sửa ngay. Commit `chore(release): vX.Y.Z` (mục 5.3) cũng push thẳng vào `dev` vì chỉ đổi version và CHANGELOG.

### 5.3. Release

`uat` và `main` cấm push thẳng, nên version và CHANGELOG cập nhật trên `dev` **trước** khi lên `uat`; đúng bản đó đi qua `uat` vào `main`. Tag chỉ gắn sau khi merge, trên commit merge của `main`.

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

- Không tag chỉ vì PR đã đóng: phải **Merged**, commit trên `main` chứa đúng tip `uat` đã nghiệm thu và version khớp. Ghi SHA được nghiệm thu vào PR release để người gắn tag đối chiếu.
- Cờ `cz` đã kiểm với `commitizen` 4.19.3 (pin trong `backend/pyproject.toml` và `.pre-commit-config.yaml`). `--files-only` đã deprecate, thay bằng `--version-files-only`.

### 5.4. Hotfix

```bash
git switch main
git pull --ff-only origin main
git status --short
git switch -c hotfix/vnpay-signature
# … sửa, commit …
# cập nhật version và CHANGELOG trong nhánh hotfix: chạy đúng các lệnh từ `cd backend` tới `git commit` ở bước 1 mục 5.3
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

Không tạo PR `uat → dev` trước khi PR `main → uat` đã merge. Sau mỗi chặng, `git fetch origin` rồi `git merge-base --is-ancestor <sha-hotfix-trên-main> origin/<nhánh-đích>` để xác nhận hotfix đã có trong nhánh đích.

### 5.5. PR xếp chồng

Khi PR B cần dựa trên PR A chưa merge:

1. Tạo nhánh B từ nhánh A, mở PR B với base là nhánh A (reviewer chỉ thấy phần của B). Ghi "Merge sau #<A>" trong mô tả.
2. Sau khi A được squash merge vào `dev`, chạy lệnh dưới rồi đổi base PR B sang `dev`. Phải dùng `--onto` vì squash tạo commit mới, các commit cũ của A không có trong lịch sử `dev`.

```bash
git fetch origin
git switch <nhánh-B>
git rebase --onto origin/dev <nhánh-A> <nhánh-B>
git diff --stat origin/dev...HEAD
git diff origin/dev...HEAD
git push --force-with-lease
gh pr edit <PR-B> --base dev
```

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

Không dùng `git reset --hard` hoặc sửa lịch sử nhánh dùng chung để "rollback". Production rollback là quyết định deployment/data migration; Git revert chỉ tạo commit đảo code, không hoàn tác dữ liệu.

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

- Mỗi nhánh có một ruleset cùng tên (Settings → Rules → Rulesets), không ai được bypass.
- Ruleset `dev` chỉ cấm force-push và xoá nhánh, không bắt buộc status check để giữ push gấp (mục 5.2). Dù vậy PR thường vào `dev` **không được merge khi CI đỏ hoặc còn pending** (quy ước review); ngoại lệ duy nhất là push gấp đủ điều kiện, và người push phải theo dõi CI.

## 7. Phiên bản và CHANGELOG

- **SemVer** `vMAJOR.MINOR.PATCH`. Giữ `0.x.y` tới go-live; bản go-live là `v1.0.0`.
- Tag chỉ gắn trên `main`, **sau** khi merge, trên commit merge của PR release `uat` → `main` (hoặc commit squash của PR hotfix).
- Bản chỉ có tài liệu, trước khi có `backend/pyproject.toml`, đi qua `uat` và `main` như thường nhưng **không** tag, không bump version; `v0.1.0` dành cho release đầu tiên có code.
- `backend/CHANGELOG.md` sinh bằng `commitizen` từ commit Conventional Commits, cập nhật trên `dev` (release) hoặc trong `hotfix/*` (hotfix), rồi vào `main` qua PR.
- Version ở `backend/pyproject.toml`, `commitizen` cập nhật trong commit `chore(release): vX.Y.Z`; cấu hình đọc `[project].version`, tag dạng `v$version`.
- Không chạy `cz bump` chế độ mặc định (tự commit, tự tag), vì tag sẽ nằm trên `dev` chứ không phải `main`.

## 8. Những thứ không được commit

| Loại | Ví dụ |
|---|---|
| Secret | `.env`, `.secrets/`, khoá JWT, mật khẩu, secret VNPay/MoMo/GHN |
| File sinh ra khi chạy | `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `htmlcov/`, `.coverage` |
| Dữ liệu local | `media/`, file dump database |
| Cấu hình cá nhân | `.idea/` (PyCharm), `.vscode/` **trừ** `launch.json` và `extensions.json`, `.DS_Store`, `Thumbs.db` |
| Môi trường ảo | `.venv/` |

- Cấu hình IDE **được** commit: `.vscode/launch.json`, `.vscode/extensions.json`, `.run/*.run.xml` (run configuration PyCharm), `.editorconfig` ([08-local-development.md](./08-local-development.md) mục 6).
- `.gitattributes` có `* text=auto eol=lf`: mọi file dùng LF, tránh lỗi khi Windows và macOS cùng làm.
- Hook `pre-commit` (`.pre-commit-config.yaml`) chặn: `gitleaks` (secret dạng chuỗi: VNPay/MoMo/GHN, API key, token), `detect-private-key` (khoá PEM), `check-added-large-files` (file lớn).
- Repo public: dữ liệu mẫu trong test/fixture phải là giá trị giả rõ ràng (ví dụ `test-hash-secret`), không bao giờ là secret hay dữ liệu khách hàng thật. Không thêm allowlist rộng cho `gitleaks`; báo nhầm thì đổi giá trị mẫu.

## 9. Việc làm một lần khi áp dụng (đã xong)

Đã xong: không còn `master` và hai nhánh Frontend cũ, `main` có ruleset, các file cấu hình đã có. Giữ lại để biết repo được thiết lập thế nào.

1. Gộp `master` vào `main`, đặt `main` làm nhánh mặc định, xoá `master` (**sẽ hỏi lại trước khi thao tác trên remote**).
2. Tạo `dev` từ `main`.
3. Xử lý hai nhánh cũ `feature/create-header` và `feature/setup-method-api-and-error` (Frontend cũ): giữ tham khảo hay xoá.
4. Cấu hình bảo vệ nhánh như mục 6.
5. Tạo `.gitignore`, `.gitattributes`, `.editorconfig`, PR template, `CONTRIBUTING.md`, cấu hình IDE dùng chung (`.vscode/launch.json`, `.vscode/extensions.json`, `.run/*.run.xml`), thêm hook `commitizen` vào `.pre-commit-config.yaml`.
