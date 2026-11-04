# Retro

Goal: from the evidence of the ticket just done, fix right away whatever caused rework or token waste in the agent environment (skill, scripts, checks, docs) and ship it in the same PR. The main session does it. Phase 5 runs steps 1–3 before G2 and steps 4–5 after G2 approval; `retro #<PR>` uses the last section.

1. **Evidence.**
   - `python3 S/scripts/metrics.py <T>`: tokens by phase and agent. The costliest phase or agent is the first candidate.
   - *Ghi chú cho retro* in `report.md`, review findings, fix rounds, reruns of checks (logs in `.git/ship-ticket-fashion/logs/`).
   - `python3 S/scripts/user_prompts.py --last 1`: repeated reminders, places where the user had to redirect.

   Done when every costly point has a cause backed by evidence, or is marked as not verifiable.
2. **Narrowest fix** for each cause:
   - Machine-checkable → an existing test, script, lint or hook.
   - Code convention or design → `CONTRIBUTING.md` or the architecture doc reviewers read.
   - Navigation or procedure → one instruction in the phase that uses it; long output → filter through `run_logged.py`.
   - Redundant, duplicated or stale instructions → delete or fix at the source.
   - A gotcha only when the cause is verified, will recur, and none of the above can encode it: `symptom → cause → fix (ticket)`, at most 2 lines; each `gotchas/` file ≤ 4 KB.
3. **Propose.** A compact list (problem, evidence, tokens or turns spent, where to fix, recommendation) goes into G2 of phase 5. Nothing worth fixing → write `Retro: không` in *Ghi chú cho retro*.
4. **Write** the approved improvements per `mattpocock-skills:writing-for-agents`, in English: one home per idea; actionable instructions with a completion criterion; branch-only material behind that branch's pointer; cut duplicates, no-ops and anything a script or config already says. Codex-only adjustments go in `.agents/skills/ship-ticket-fashion/`.
5. **Verify and commit.** Script changes → `python3 -m unittest discover -s S/scripts`; hook or backend config changes → the matching check (*Machine checks*); always `git diff --check`. Record the improvements made in *Ghi chú cho retro*, then `commit.py <T> --task retro -m "chore: refine ship-ticket-fashion after <topic> ticket" -- <file>… <report.md>`.

Lessons go into the skill's or repo's source of truth; write memory only when the user asks.

## Done when

Every costly point has a conclusion; only approved improvements were made, verified, and sit in a `Task: retro` commit, or the report says `Retro: không`.

## PR retro (`retro #<number>`)

Runs at once, no state needed.

1. Evidence: `gh pr view <number> --json title,commits,reviews,comments,statusCheckRollup` (account in `phases/6-ship.md`), line comments per the CI section of that phase, the ticket report if any, `user_prompts.py`.
2. Do steps 2 and 4, verify per step 5. Improvements the user asked for explicitly are approved; ask about new proposals with `AskUserQuestion`.
3. Changes → branch `chore/skill-retro-pr-<number>` from `origin/dev`, commit `chore: refine ship-ticket-fashion after PR #<number>`, PR per `phases/6-ship.md` sections 1–3. No changes → report the conclusion.
