# Phase 6 — ship

Base conventions: `docs/architecture/11-git-workflow.md`. This file covers only what is specific to this machine and repo. G2 is approved, so this phase does not ask again, except for a `FAIL` line from `check_ship.py`.

## `gh` account

The machine has several GitHub accounts. Every `gh` command runs through the Bash tool with the prefix:

```bash
GH_TOKEN="$(gh auth token --user LuongCongThanh)" gh …
```

Repo `LuongCongThanh/fashion-store-backend`; remote `origin` uses the SSH alias `github-thanh`.

## 1. Push

```bash
git fetch origin && git rebase origin/dev
# rebase pulled new commits → full check (reference/rules.md → Machine checks)
git push -u origin <branch>        # own branch: --force-with-lease after a rebase
```

## 2. Open the PR

1. Conventional Commits title, scope = module (`shared`, `catalog`…); this title becomes the squash commit on `dev`.
2. PR body per `.github/pull_request_template.md`, in Vietnamese, written to `.git/PR_BODY.md` (reason in `gotchas/windows-shell.md`). **Closes** is the ticket folder. **Làm gì** and **Vì sao** come from *Việc cần làm* and `## Quyết định` in `spec.md`. From `report.md`: **Kết quả** ← *Đã làm*, written as Before → After behaviour; *Cách kiểm* ← the AC → evidence table; *Gap và lưu ý* ← Chưa làm, Gap, new tickets, `untestable` ACs, each line with content or "Không"; **Notes** ← review verdicts and the *Commit* table. Tick the checklist truthfully, N/A where it does not apply. Write the content per `mattpocock-skills:pr` inside the repo template: **Giải pháp** uses the skill's smallest shape (pseudocode, call tree, diff-sketch); *Cách kiểm* gives Before/After (red → green test); *Reviewer cần chú ý* states Door (one-way / two-way) and Blast Radius.
3. Create it, then record the PR number in state:

```bash
GH_TOKEN="$(gh auth token --user LuongCongThanh)" gh pr create -B dev -H <branch> -t "<title>" -F .git/PR_BODY.md --assignee @me
python3 S/scripts/state.py set <T> pr=<number>
```

## 3. CI

```bash
GH_TOKEN="$(gh auth token --user LuongCongThanh)" gh pr checks <number> --watch
```

`no checks reported` (run right after the push, before the workflow registered checks) → run it again.

Red → `gh run view <id> --log-failed > .git/ship-ticket-fashion/logs/ci.log`, read the failing part (cause unclear or red only on CI → `mattpocock-skills:diagnosing-bugs`). Full: send the log path to the implementer (`SKILL.md` → *Sub-agents*). Lite: the main session fixes. Fix within the ticket's scope, commit `--task ci`, push. Red outside scope → *Needs user*.

The SonarCloud check stays green even with issues (Quality Gate still passes), so also read the bot's comment:

```bash
GH_TOKEN="$(gh auth token --user LuongCongThanh)" gh pr view <number> --json comments --jq '.comments[] | select(.author.login=="sonarqubecloud") | .body' | grep -oE '[0-9]+ (New issues?|Security Hotspots?)'
```

Line comments (bots, reviewers) are not in `comments` above; read them separately and handle them like phase 4 findings:

```bash
GH_TOKEN="$(gh auth token --user LuongCongThanh)" gh api repos/LuongCongThanh/fashion-store-backend/pulls/<number>/comments --jq '.[] | "\(.path):\(.line) \(.user.login): \(.body)"'
```

SonarCloud count above 0 → list the issues from the check-run annotations (the Sonar project is private, so Sonar's API returns 0 issues):

```bash
export GH_TOKEN="$(gh auth token --user LuongCongThanh)"; sha=$(gh pr view <number> --json headRefOid -q .headRefOid)
id=$(gh api repos/LuongCongThanh/fashion-store-backend/commits/$sha/check-runs --jq '.check_runs[] | select(.name=="SonarCloud Code Analysis") | .id')
gh api repos/LuongCongThanh/fashion-store-backend/check-runs/$id/annotations --jq '.[] | "\(.path):\(.start_line) \(.title)"'
```

Handle each issue as a phase 4 *fix* finding and record it under *Thay đổi theo yêu cầu* in the report. An issue reflecting a code convention not yet in `CONTRIBUTING.md` section *Quy ước code* → propose adding it in retro.

Every later push to the open PR: update the PR body (`gh pr edit <number> -F .git/PR_BODY.md`) and add a comment summarising what was fixed (`gh pr comment <number> -F <file>`).

## 4. Close the ticket in the PR, once CI is green

```bash
python3 S/scripts/close_ticket.py <T> --pr <number>
python3 S/scripts/progress.py --feature <feature>
python3 S/scripts/metrics.py <T> --write   # metrics.md: the ticket's token usage up to closing
```

`close_ticket.py` fails closed when state, phase `ship`, G2, a PR matching state, finished slices or the AC trace are missing. It prints the ACs it ticked; compare them with the AC → evidence table. `untestable` ACs are not ticked and are printed separately: already checked by hand, or a CI AC that section 3 turned green → tick them; otherwise note them in the PR's Notes.

In the same commit, update `.scratch/mvp-roadmap/map.md`: the milestone's row in the **Tiến độ** table matches `progress.py`; **Decisions-so-far** gets `DD/MM/YYYY: …` for each decision reaching beyond the ticket. Update `docs/agents/ticket-history.md`: append the ticket to the end of the feature's **Đã xong** (`link · description · PR #<number> · DD/MM/YYYY`), remove it from **Còn mở**.

`commit.py <T> --task close -m "docs: close <topic> ticket" -- <ticket folder> .scratch/mvp-roadmap/map.md docs/agents/ticket-history.md`, push.

## 5. Change phase

`state.py transition <T> --to done --next "hỏi merge" --reason "PR #<number> mở, CI xanh"`.

## Done when

PR open against `dev`, its number in state; ticket `resolved` with `**PR:**` in the PR; `metrics.md` in the ticket folder; `map.md` matches `progress.py`; CI green; SonarCloud 0 New issues and 0 Security Hotspots; `phase` is `done`.
