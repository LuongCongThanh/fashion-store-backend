---
name: ship-ticket-fashion
description: Ship a Fashion Store `.scratch/` ticket from grilling to merge, or plan spec + tickets for a new module. Use when the user says "làm ticket NN", "làm tiếp", "làm module X", "retro PR #N", or asks about progress / the next ticket.
argument-hint: "[<feature>/<NN> | <NN> | <module>] [grill|code|report|review|sync|ship|done] | retro #<PR>"
---

# ship-ticket-fashion

Write every message to the user in Vietnamese. Each run takes **one** ticket through the loop below; stop only at a gate, at *Needs user* (`reference/rules.md`), or when done.

- `S` = `.claude/skills/ship-ticket-fashion` (from repo root) · `<T>` = `<feature>/<NN>` · `<K>` = `<feature>-<NN>`.
- `.git/ship-ticket-fashion/` holds state `<K>.json`, code map `<K>-map.md`, review findings `<K>-review.md` and `logs/`: outside git, survives `/clear`.

**Codex:** read `.agents/skills/ship-ticket-fashion/SKILL.md` first.

## Start

Windows: read `gotchas/windows-shell.md`, use `python` instead of `python3`.

1. `python3 S/scripts/state.py start [<T>]`. Its output (ticket, phase, `next`, slices, gates, flags, `READ` lines) replaces reading the state file.
   - `NO STATE` + `FRONTIER` → `reference/pick-ticket.md`.
   - Module or milestone without tickets (`catalog`, `M1`) → `phases/0-plan.md`.
   - `retro #<PR>` → skip `start`, run `phases/8-retro.md` section *PR retro*.
2. **Preflight** (phases `grill` → `ship`): `python3 S/scripts/preflight.py --fix` checks Docker services, PostgreSQL, migrations, seed data, Redis, API and Mailpit URLs, and runs `make up` / `make migrate` / `make load-geo` when needed. Then `FAIL api` → start `make run` in `backend/` as a background process (Bash `run_in_background`) and rerun until it passes; any other `FAIL` left → *Needs user* with its `fix:` command. Ticket work starts only after `PREFLIGHT OK`.
3. Read every file listed after `READ`.
4. Continue from `next`. A `[phase]` argument overrides the phase unless a gate is still unapproved.

## Loop

```
0 plan (empty frontier)
1 grill → ⛔G1 → 2 code → 3 report → 4 review → 5 sync + retro → ⛔G2 → 6 ship → 7 done → closed
                    ↑                         │          │
                    └── review / sync changes behaviour ─┘
```

Phase `n` lives in `phases/<n>-<name>.md`. Retro (`phases/8-retro.md`) runs inside phase 5 of every ticket; skill fixes ship in the ticket's PR, and the ticket's token usage lands in `metrics.md`. A skill written `/mattpocock-skills:<name>` is user-invoked only: suggest the user type it; a skill without `/` is called with the Skill tool.

## Mode

**lite** when all three hold: ≤ 3 acceptance criteria, no new model or migration, no new endpoint. Otherwise **full**. Phase 1 proposes, G1 decides. Lite: one slice, the main session codes and fixes, grilling asks only what is still open, one review agent covers all three axes.

## Sub-agents

The main session orchestrates and owns gates, docs, ship, done and retro. Sub-agents are `general-purpose` with no `model` set:

| Work | Full | Lite |
| --- | --- | --- |
| Phase 1, code map | `Explore`; main session saves the result to `<K>-map.md` | same as full |
| Phase 2, all slices | **one** *implementer* does every slice in DAG order | main session |
| Phase 4, review | `code-review` (Spec + Standards) in parallel with one Bug agent | one agent, all three axes |
| Phase 4 fix rounds, phase 6 CI red | the phase 2 *implementer* | main session |

- **Prompt is an address**: `<T>`, the job (slice / fix round / CI log), mode, and paths to read in order: `S/reference/sub-agent.md`, `S/reference/rules.md`, the phase file, `.git/ship-ticket-fashion/<K>-map.md`, the ticket folder. The agent reads file contents itself.
- **Announce = call**: the message announcing a delegation contains the `Agent` call.
- **Keep the implementer**: save its agent id. *Needs user* answers, fix rounds and CI failures go to it via `SendMessage` (load with `ToolSearch "select:SendMessage"`). If `ListAgents` no longer shows it → spawn a new one with the same address prompt; it reads `handoff` in state, the commits and `<K>-map.md`, then continues.
- The main session trusts returned results and state; it does not re-read files a sub-agent already read.

## Gate

A *gate* (G1, G2) is the user's decision; a green / red script is only a *check*.

1. **Summary**: a compact table of the items the phase lists, each open point with a recommendation.
2. **Ask**: `AskUserQuestion` with only the points needing an answer; ≤ 4 questions per call, 2–4 options, recommended option first with "(khuyên dùng)". Group related points into one question.

The gate is done when every open point has an answer recorded in the ticket or state.

## State, ticket, commit

- State schema: `reference/state.md`; write fields with `state.py set` / `push`. Change phase only with `python3 S/scripts/state.py transition <T> --to <phase> --next "<one concrete task>" --reason "<criterion met / gate>" [--gate g1|g2]`; the script rejects out-of-order moves and missing gates.
- A ticket is the folder `.scratch/<feature>/issues/NN-<slug>/`: `spec.md` (phase 1 adds `## Quyết định`), `plan.md` (generated by `plan.py`), `report.md` (written in phase 3, overwritten in phases 4 and 5).
- One *task* is exactly one commit, via `python3 S/scripts/commit.py <T> --task <task> -m "<subject>" [--body "…"] -- <file>…` (adds `Refs:`, `Task:` trailers; re-adds files a hook rewrote). Tasks and subjects: `templates/commit-msg.md`. `commit_map.py <T> [--md]` prints commit → task → AC.

**Clear point** (where a phase says so): print `Đã lưu state (<phase>/<slice>). Có thể /clear rồi chạy lại /ship-ticket-fashion <T> để tiếp tục.`, then keep going unless the user interrupts. If context is not yet in state or the ticket (grilling in progress), add: `Cần mang ngữ cảnh đó sang phiên mới thì gõ /mattpocock-skills:handoff <T> <phase>.`
