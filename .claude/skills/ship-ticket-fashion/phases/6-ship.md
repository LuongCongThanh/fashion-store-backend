# Phase 6 — ship

Quy ước gốc: `docs/architecture/11-git-workflow.md`. File này chỉ ghi phần riêng của máy và repo này. G2 đã duyệt nên phase này không hỏi lại, trừ dòng `FAIL` của `check_ship.py`.

## Tài khoản `gh`

Máy có nhiều tài khoản GitHub. Mọi lệnh `gh` chạy qua Bash tool với tiền tố:

```bash
GH_TOKEN="$(gh auth token --user LuongCongThanh)" gh …
```

Repo `LuongCongThanh/fashion-store-backend`; remote `origin` dùng SSH alias `github-thanh`.

## 1. Push

```bash
git fetch origin && git rebase origin/dev
python S/scripts/run_logged.py --label test --cwd backend -- make test   # chỉ khi rebase kéo về commit mới
git push -u origin <nhánh>        # nhánh của mình: --force-with-lease sau rebase
```

## 2. Mở PR

1. Tiêu đề Conventional Commits, scope là module (`shared`, `catalog`…); tiêu đề này thành commit squash trên `dev`.
2. Thân PR theo `.github/pull_request_template.md`, ghi vào `.git/PR_BODY.md` (lý do ở `gotchas/windows-shell.md`). **Closes** là thư mục ticket. Lấy từ `report.md`: *Cách kiểm* ← bảng AC → bằng chứng; *Gap và lưu ý* ← Chưa làm, Gap, ticket mới, AC `untestable`, mỗi dòng có nội dung hoặc "Không"; **Notes** ← kết luận review và bảng *Commit*. Checklist tick theo sự thật, mục không áp dụng ghi N/A.
3. Tạo, rồi ghi số PR vào state:

```bash
GH_TOKEN="$(gh auth token --user LuongCongThanh)" gh pr create -B dev -H <nhánh> -t "<tiêu đề>" -F .git/PR_BODY.md --assignee @me
python S/scripts/state.py set <T> pr=<số>
```

## 3. Đóng ticket trong PR

```bash
python S/scripts/close_ticket.py <T> --pr <số>
python S/scripts/progress.py --feature <feature>
```

`close_ticket.py` in các AC vừa tick: đối chiếu với bảng AC → bằng chứng. AC nằm trong `untestable` (đọc từ state) không được tick và in riêng: đã kiểm tay thì tự tick, chưa thì ghi vào Notes của PR.

Cùng commit, sửa `.scratch/mvp-roadmap/map.md`: dòng của mốc trong bảng **Tiến độ** khớp `progress.py`; **Decisions-so-far** thêm `DD/MM/YYYY: …` cho mỗi quyết định ảnh hưởng ngoài ticket. Sửa `docs/agents/ticket-history.md`: thêm ticket vào cuối **Đã xong** của feature (`link · mô tả · PR #<số> · DD/MM/YYYY`), bỏ khỏi **Còn mở**.

`commit.py <T> --task close -m "docs: close <chủ đề> ticket" -- <thư mục ticket> .scratch/mvp-roadmap/map.md docs/agents/ticket-history.md`, push.

## 4. CI

```bash
GH_TOKEN="$(gh auth token --user LuongCongThanh)" gh pr checks <số> --watch
```

In `no checks reported` (chạy ngay sau push, workflow chưa đăng ký check) → chạy lại lệnh trên.

Đỏ → `gh run view <id> --log-failed > .git/ship-ticket-fashion/logs/ci.log`, đọc đoạn lỗi, sửa trong phạm vi ticket, commit `--task ci`, push. Đỏ ngoài phạm vi → *Cần người dùng*.

Check SonarCloud xanh cả khi còn issue (Quality Gate vẫn passed), nên đọc thêm comment của bot:

```bash
GH_TOKEN="$(gh auth token --user LuongCongThanh)" gh pr view <số> --json comments --jq '.comments[] | select(.author.login=="sonarqubecloud") | .body' | grep -oE '[0-9]+ (New issues?|Security Hotspots?)'
```

Comment gắn vào dòng code (bot, reviewer) không nằm trong `comments` ở trên; đọc riêng và xử lý như finding của phase 4:

```bash
GH_TOKEN="$(gh auth token --user LuongCongThanh)" gh api repos/LuongCongThanh/fashion-store-backend/pulls/<số>/comments --jq '.[] | "\(.path):\(.line) \(.user.login): \(.body)"'
```

SonarCloud số khác 0 → lấy danh sách issue từ annotation của check-run (project Sonar private nên API của Sonar trả 0 issue):

```bash
export GH_TOKEN="$(gh auth token --user LuongCongThanh)"; sha=$(gh pr view <số> --json headRefOid -q .headRefOid)
id=$(gh api repos/LuongCongThanh/fashion-store-backend/commits/$sha/check-runs --jq '.check_runs[] | select(.name=="SonarCloud Code Analysis") | .id')
gh api repos/LuongCongThanh/fashion-store-backend/check-runs/$id/annotations --jq '.[] | "\(.path):\(.start_line) \(.title)"'
```

Xử lý từng issue như finding *sửa* của phase 4 và ghi vào *Thay đổi theo yêu cầu* của báo cáo. Issue thuộc một quy ước code chưa có trong `CONTRIBUTING.md` mục *Quy ước code* → đề xuất thêm ở retro.

Mỗi lần push thêm vào PR đã mở: cập nhật thân PR (`gh pr edit <số> -F .git/PR_BODY.md`) và thêm comment tóm tắt đã sửa gì (`gh pr comment <số> -F <file>`).

## 5. Chuyển phase

`state.py transition <T> --to done --next "hỏi merge" --reason "PR #<số> mở, CI xanh"`.

## Xong khi

PR mở vào `dev`, số PR nằm trong state; ticket `resolved` với `**PR:**` trong PR; `map.md` khớp `progress.py`; CI xanh; SonarCloud 0 New issues và 0 Security Hotspots; `phase` là `done`.
