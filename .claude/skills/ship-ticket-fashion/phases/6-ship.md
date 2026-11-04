# Phase 6 — ship

Base conventions: `docs/architecture/11-git-workflow.md`. This file covers only what is specific to this machine and repo. G2 is approved, so this phase does not ask again, except for a `FAIL` line from `check_ship.py`.

## `gh` account

The machine has several GitHub accounts. `ci.py` and `merge.py` handle the account themselves (`scripts/github.py`). Every other `gh` command runs through the Bash tool with the prefix:

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

1. Conventional Commits title, scope = module (`common`, `catalog`…); this title becomes the squash commit on `dev`.
2. PR body per `.github/pull_request_template.md`, in Vietnamese, written to `.git/PR_BODY.md` (reason in `gotchas/windows-shell.md`). **Closes** is the ticket folder. **Làm gì** and **Vì sao** come from *Việc cần làm* and `## Quyết định` in `spec.md`. From `report.md`: **Kết quả** ← *Đã làm*, written as Before → After behaviour; *Cách kiểm* ← the AC → evidence table; *Gap và lưu ý* ← Chưa làm, Gap, new tickets, `untestable` ACs, each line with content or "Không"; **Notes** ← review verdicts and the *Commit* table. Tick the checklist truthfully, N/A where it does not apply. Write the content per `mattpocock-skills:pr` inside the repo template: **Giải pháp** uses the skill's smallest shape (pseudocode, call tree, diff-sketch); *Cách kiểm* gives Before/After (red → green test); *Reviewer cần chú ý* states Door (one-way / two-way) and Blast Radius.
3. Create it, then record the PR number in state:

```bash
GH_TOKEN="$(gh auth token --user LuongCongThanh)" gh pr create -B dev -H <branch> -t "<title>" -F .git/PR_BODY.md --assignee @me
python3 S/scripts/state.py set <T> pr=<number>
```

## 3. CI

`python3 S/scripts/ci.py <T>` waits for the checks (minutes: run it in the background or with a long timeout), then prints `CI OK | RED | WAIT`, each failing check, SonarCloud counts, failed Quality Gate conditions with their `SONAR <path>:<line>` annotations, and `COMMENT <path>:<line>` line comments from bots and reviewers. Exit 0 = every check green and SonarCloud clean.

- `RED` → read `.git/ship-ticket-fashion/logs/ci.log` (cause unclear or red only on CI → `mattpocock-skills:diagnosing-bugs`). Full: send the log path to the implementer (`SKILL.md` → *Sub-agents*). Lite: the main session fixes. Fix within the ticket's scope, commit `--task ci`, push, rerun `ci.py`. Red outside scope → *Needs user*.
- Each `SONAR` and `COMMENT` line → handle like a phase 4 *fix* finding and record it under *Thay đổi theo yêu cầu* in the report. An issue reflecting a code convention not yet in `CONTRIBUTING.md` section *Quy ước code* → propose adding it in retro.
- Every later push to the open PR: update the PR body (`gh pr edit <number> -F .git/PR_BODY.md`) and add a comment summarising what was fixed (`gh pr comment <number> -F <file>`).

## 4. Close the ticket in the PR, once `ci.py` exits 0

```bash
python3 S/scripts/close_ticket.py <T> --pr <number>
python3 S/scripts/metrics.py <T> --write   # metrics.md: the ticket's token usage up to closing
```

`close_ticket.py` fails closed when state, phase `ship`, G2, a PR matching state, finished slices or the AC trace are missing. It marks the ticket `resolved`, ticks ACs, appends the ticket to **Đã xong** in `docs/agents/ticket-history.md` (dropping it from **Còn mở**) and adds its number to the ✅ group of the milestone's row in the **Tiến độ** table of `.scratch/mvp-roadmap/map.md`. Then:

- Compare the ticked ACs with the AC → evidence table. `untestable` ACs are printed separately: already checked by hand, or a CI AC that section 3 turned green → tick them; otherwise note them in the PR's Notes.
- Each `WARN` line (the number still sits in another group such as `⬜ 02–12`, a missing section) → fix that spot by hand.
- **Decisions-so-far** in `map.md` gets `DD/MM/YYYY: …` for each decision reaching beyond the ticket.

`commit.py <T> --task close -m "docs: close <topic> ticket" -- <ticket folder> .scratch/mvp-roadmap/map.md docs/agents/ticket-history.md`, push.

## 5. Change phase

`state.py transition <T> --to done --next "hỏi merge" --reason "PR #<number> mở, CI xanh"`.

## Done when

PR open against `dev`, its number in state; ticket `resolved` with `**PR:**` in the PR; `metrics.md` in the ticket folder; `map.md` matches `progress.py`; CI green; SonarCloud 0 New issues and 0 Security Hotspots; `phase` is `done`.
