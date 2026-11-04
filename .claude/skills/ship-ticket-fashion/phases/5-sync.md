# Phase 5 — sync docs, retro + ⛔G2

Goal: after this PR, `docs/` and `.scratch/` describe the code on the branch.

1. **Change list.** From `git diff origin/dev...HEAD --stat` and the code diff: new or renamed public names (functions, classes, settings), `make` commands, env vars, new files / folders, endpoints, models, behaviour changed during review.
2. **Find stale spots.** For each item, `grep -rn "<name>" docs GLOSSARY.md .scratch CONTRIBUTING.md README.md` and fix places describing old behaviour. Docs that often drift:
   - `docs/architecture/02-backend-structure.md`: folder tree, module template, layers.
   - `docs/architecture/modules/<module>.md`: the touched module's tree, public API, events, jobs.
   - `03-data-model.md`: fields, constraints, migrations.
   - `04-api-contract.md`: endpoints, error format, pagination.
   - `08-local-development.md`: `make` commands (table in section 3), env vars (section 2.3), `.env.example`.
   - `12-testing-strategy.md`: markers, fixtures, CI gates.
3. **Domain.** New terms → `GLOSSARY.md`; lasting architecture decisions → ADR; both via `mattpocock-skills:domain-modeling`.
4. **Ticket.** `## Quyết định` in `spec.md` matches the final code (function signatures, behaviour changed in review). Out-of-scope work found → backlog per `reference/rules.md` (*Scope*).
5. **Small code fixes of the same kind** this phase exposes within the ticket's scope (names drifting from the settled docs, wrong comments): fix the code, rerun the related tests.
6. Fill the report's *Tài liệu đã cập nhật* section and refresh its *Commit* section (`commit_map.py <T> --md`), then commit docs, step 5 code and the ticket folder at once: `commit.py <T> --task sync -m "docs: sync docs and report for <topic> ticket" -- <file>…`.
7. **Final check**: full check per the milestones in *Machine checks*; always run `check_ac_trace.py` and `check_ship.py <T>`. Every `WARN` / `FAIL` line is a G2 point.
8. **Retro**: `phases/8-retro.md` steps 1–3.
9. **⛔G2** (format in `SKILL.md` → *Gate*). Summary: AC → evidence table; review verdicts (open items); docs updated; new tickets created; test count; `WARN` / `FAIL` lines of `check_ship.py`; tokens by phase; proposed retro improvements; proposed PR title. State plainly: approving G2 lets phase 6 push, open the PR and close the ticket without asking again; merge is still asked separately. Ask: approve ship (recommended when there is no `FAIL`), more fixes, or stop; and which retro improvements to make (multi-select).
10. User asks for more fixes → record `userRequested`, fix (behaviour change → `--to code` and walk the phases again), present G2 again. Once approved: `phases/8-retro.md` steps 4–5 with the chosen improvements, then:

    ```bash
    python3 S/scripts/state.py transition <T> --to ship --gate g2 --next "push và mở PR" --reason "G2 approved"
    ```

## Done when

Every change-list item was grepped and no doc still describes old behaviour; the final check is green or each `WARN` was answered at G2; retro is done per *Done when* of `phases/8-retro.md`; `gates.g2` has a date and `phase` is `ship`.
