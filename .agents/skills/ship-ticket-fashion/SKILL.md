---
name: ship-ticket-fashion
description: Ship a Fashion Store `.scratch/` ticket from spec decisions to merge, with a retro that improves the skill inside the ticket's PR; plan spec and tickets for a new module; run a PR retro on request. Use when the user asks to work a ticket, continue a module, check ticket progress, or retro a PR in this repo.
---

# ship-ticket-fashion for Codex

Read the [shared workflow](../../../.claude/skills/ship-ticket-fashion/SKILL.md) and apply the Codex adjustments below wherever it names Claude Code tools or skills. They only change how things are done in Codex; phases, acceptance criteria, per-task commits and gates stay as the workflow defines them.

`S` is always `.claude/skills/ship-ticket-fashion`, from the repo root. Scripts, phases, templates, gotchas and the state schema are shared there; never copy them into `.agents/`. That is why `state.py` keeps printing correct `READ` paths without changing its `SKILL` constant. In sample commands replace `S` with the real path; `S` is not a declared shell variable.

Before working a ticket, read `CLAUDE.md` (project conventions) and `GLOSSARY.md`. Repo docs are written in Vietnamese; code, branch names, commits and PR titles in English. Do not read `.env*` (except `.env.example`), `.secrets/`, `*.pem`, or print tokens. Rules in `.claude/settings.json` apply only to Claude Code and grant Codex nothing.

## Start and resume

- Ticket, module or progress: run `python3 .claude/skills/ship-ticket-fashion/scripts/state.py start [<T>]` on its own, then read the `READ` files and follow `next`. State is shared with Claude; only one session owns a ticket at a time. Signs that another session is working the same ticket → confirm with the user before touching its state or files.
- Preflight (`S/scripts/preflight.py --fix`) runs as in the shared workflow; start `make run` with the background-process tool the session has.
- `retro #<PR>`: skip `start`, read `S/phases/8-retro.md` and use the Codex evidence sources under Retro below.
- After saving state and decisions, replace the `/clear` message with: `Đã lưu state (<phase>/<slice>). Có thể mở phiên mới rồi gọi $ship-ticket-fashion <T> để tiếp tục.` The new session rereads state and does not assume the old agent still exists.

## Tools and gates

| In the Claude workflow | In Codex |
| --- | --- |
| `Read`, `Bash`, `grep` | Read files with the filesystem tool or `Get-Content -LiteralPath`; run commands with the shell tool; search with `rg`. |
| `AskUserQuestion` | Use the session's ask-the-user tool. Without one, ask in a message and stop the work that depends on the answer. |
| `Agent`, `Explore`, `general-purpose` | Use the available sub-agent tool; state the Explore role in the prompt, without assuming an agent type of that name. Set no model. |
| `SendMessage`, `ListAgents`, `ToolSearch` | Use the matching tools for continuing work, listing agents and discovering tools. Do not call Claude tool names literally. |

G1, G2, choosing findings to fix, choosing retro improvements and the merge decision need a real answer from the user. Keep the approved scope; answers from an earlier session still count once saved in state and the ticket. A green check or a recommended option is not gate approval. Run `transition --gate g1|g2` only after the user approves. G2 allows push and opening the PR as phase 5 says; merge needs its own instruction from the user.

Fit the number of questions and options to the session's tool limits. Without multi-select, number the findings or proposals and ask the user to pick codes; never pick for them.

## Sub-agents

When the session has the tools and allows delegation, apply the shared workflow's work-split table. Each agent reads this file before `S/reference/sub-agent.md`, `S/reference/rules.md`, the phase, gotchas and the ticket; pass `<T>`, slice, mode and an explicit file scope. Dependent slices run in sequence. One agent keeps the work through fix rounds while it is alive; wake a waiting agent with the continue-work tool.

Without sub-agent support or permission, the main session plays every role in turn, still writing state and reports as the sub-agent contract says. State plainly that one agent did the review. On resume with `SLICE OPEN`, check whether the agent is alive if a tool allows; if it is gone, read handoff, diff, commits and test status before taking over the slice.

## Skill dependencies

Call only skills actually listed in the session; `mattpocock-skills:*` names are Claude references, not dependencies installed into Codex. If a matching skill exists, read its instructions. If not, produce the required outcome below directly; never skip a phase or ask the user to type a Claude slash command.

| Skill named | Outcome to produce when missing |
| --- | --- |
| `grilling` | Read code and docs, find open decisions within the ticket's scope, present options with a recommendation, record answers in `## Quyết định`. |
| `to-spec`, `to-tickets` (user-invoked) | Write the spec per `S/phases/0-plan.md` and the sample `.scratch/backend-bootstrap/spec.md`; create tickets in phase 0's shape with testable ACs and blocking relations. Settle open scope with the user before writing. |
| `codebase-design` | Settle interfaces and seams in the spec; assess hidden complexity and what is lost if the abstraction is deleted (deletion test). A seam with one adapter needs a reason. A module's first `contracts.py` compares at most three options at G1. |
| `tdd` | Loop: red test on the behaviour gap → minimal code to green → refactor; test at the seam and per AC as in phase 2. |
| `mattpocock-skills:code-review` + Bug-axis sub-agent | Cover all three axes Spec, Standards, Bug per `S/phases/4-review.md`, against `origin/dev`. Spec checks each AC and assertion quality; Standards checks the governing docs; Bug reads the diff and related code for behaviour bugs. Each finding has a code, `file:line`, evidence and a verdict. |
| `domain-modeling` | Read `docs/agents/domain.md`, update `GLOSSARY.md` for new terms and ADRs for lasting architecture decisions, check names in code. |
| `improve-codebase-architecture` (user-invoked) | Survey the hotspot and its callers, show problems with concrete code, propose scope and trade-offs. The user chooses before `needs-triage` tickets are created per phase 0. |
| `research` | Read primary sources (official docs, library source at the version in `backend/uv.lock`), write cited findings to `.scratch/<feature>/research/<topic>.md`. |
| `diagnosing-bugs` | First build a runnable command that goes red on the bug (test, script), then hypothesise and fix; if it cannot be built, say what was tried. |
| `pr` | Keep the `.github/pull_request_template.md` frame; *Giải pháp* uses the smallest pseudocode / call tree, *Cách kiểm* gives Before/After, *Reviewer cần chú ý* states Door and Blast Radius. |
| `triage`, `retro`, `handoff` (user-invoked) | Drop the type-this-command suggestion: triage asks directly per `S/reference/pick-ticket.md` step 3; retro uses the evidence sources under Retro; handoff becomes state + a new-session message. |
| `writing-for-agents` | Write exactly the chosen retro improvements: one home per idea, concrete actionable instructions; drop duplicate or stale lines. Keep rules and examples in one source. |

## Shell and GitHub

The session's default shell may be PowerShell. `GH_TOKEN="$(gh auth token --user LuongCongThanh)" gh …` in phases 6–8 is Bash syntax: use it verbatim only when the shell tool runs Bash. In PowerShell, put the token in an environment variable for the `gh` process, keep it out of output, and restore the previous value with `try/finally`. Never change the machine-wide default GitHub account.

Keep tokens in the process environment, never interpolated into command strings or written to files. Write PR bodies and squash commit bodies as UTF-8 and pass them with `--body-file`/`-F` as the phases say. Use the shell tools available; do not require a separate `Bash tool`. Keep `run_logged.py` for long checks and read `S/gotchas/windows-shell.md` on shell errors.

## Retro

Retro runs in phase 5 of every ticket per `S/phases/8-retro.md`; `retro #<PR>` uses that file's last section. Each ticket's notes follow the report template.

`S/scripts/user_prompts.py` and `S/scripts/metrics.py` read only Claude transcripts. In Codex, skip both (including `metrics.py --write` in phase 6); never use Claude history as evidence for a Codex session and never scan other users' session folders.

Use `report.md` and the ticket's *Ghi chú cho retro*, spec, plan, commit → task, and the PR's review/CI. Conversation, state/handoff and surviving check logs are supporting evidence. After a session change, without the user's exact words, conclude only from saved evidence and name what cannot be verified. Never invent what the user said.

General process improvements go in `S`; Codex-only adjustments go in this file. Changes under `.agents/skills/` count as skill changes in retro; only hook or backend config changes require the matching backend check. Script changes → run the shared unittest suite. Always `git diff --check`; keep the step where the user picks proposals before changes, and the `retro #<PR>` PR flow.

Write memory only when the user asks directly, under the Codex session's memory permissions and mechanism.
