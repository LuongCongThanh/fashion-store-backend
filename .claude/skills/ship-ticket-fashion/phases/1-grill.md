# Phase 1 — grill + ⛔G1

Goal: every acceptance criterion has a seam and test names, every open choice has a decision, the environment can run tests.

1. **Branch.** Stop at the first *Needs user*.
   - `git status --short` shows changes from other work → *Needs user*.
   - `gh pr list --head <current branch> --state open` (account in `phases/6-ship.md`). An open PR → ask: merge that PR first (recommended when the new ticket needs its code), or branch from `origin/dev` now.
   - `git fetch origin`, create `<type>/<short-description>` from `origin/dev` (`docs/architecture/11-git-workflow.md` section 2).

   Done when `git branch --show-current` is the new branch and the working tree holds only ticket files.
2. **Baseline.** Flag `NO HOOKS` → ask, then run `uv run pre-commit install` in `backend/`. Preflight is already green (`SKILL.md` → *Start*). Run `make test` with `--label baseline` (*Machine checks*). A red test is pre-existing on `origin/dev`: record the test id (or step name) in `notes.baselineRed` at step 3. Done when the baseline is green or every red is in `notes.baselineRed`.
3. **State.** `python3 S/scripts/state.py init <T> --branch <branch> --mode full` (provisional mode, G1 decides). Read `reference/state.md`.
4. **Sources.** Read the ticket, the feature `spec.md`, the docs and ADRs the ticket points to, `GLOSSARY.md`. Ticket touches business rules → also `docs/business/04-business-rules.md`, `05-order-lifecycle.md`. Tests: look up `docs/architecture/12-testing-strategy.md` by both test type and the topics the ticket touches (logs, DB, cache, fixtures).
5. **Code map** (`Explore` sub-agent). Brief: code the ticket changes or calls (file, signature, line), callers, reusable tests and fixtures, tickets blocked by this one (`Blocked by` pointing here) so the API fits their later use. Ticket wraps something a library already does (calendar sync, migration, auth…) → `mattpocock-skills:research` on the primary docs for the exact version in `backend/uv.lock`, written to `.scratch/<feature>/research/<topic>.md`.
   The main session writes the result to `.git/ship-ticket-fashion/<K>-map.md` (≤ 150 lines: file → signature / line → role; reusable tests, fixtures, library functions), then looks up `docs/architecture/README.md` for the *governing docs* of each file to change and reads exactly those sections. Done when the map has every file to change.
6. **Grilling.** `mattpocock-skills:grilling` within the ticket's scope: settle open choices and the _seams_ to test. Lite: ask only what the ticket and docs leave open.
   - Code moving out of a broad `except` (a handler's, a transaction's): list every exception it used to catch there and decide where each lands after the move.
   - **Public interface** (adding or changing a public function in a module's `contracts.py`, `services`, `selectors`, or in `shared/`) → add `mattpocock-skills:codebase-design`: _deletion test_ and "one adapter = hypothetical seam" for each interface. A module's first `contracts.py` → add *design-it-twice*, at most 3 options, compared at G1.
7. **`## Quyết định`** in the ticket's `spec.md`, placed before `## Acceptance criteria`: the line `Chốt khi grilling ngày DD/MM/YYYY.`, then a Chủ đề | Quyết định table with a `Tài liệu chi phối` row (machine-readable references: `docs/architecture/13-python-django-coding-style.md::3.1`, `docs/adr/0007-events-outbox-celery-no-kafka.md`), an `Interface / seam` row if any, and every deviation from *Việc cần làm* with its reason. Models and tests reference the naming / test-path sections; tests add the factory section and the doc owning the scenario. Write it in Vietnamese.
8. **Slices** (schema in `reference/state.md`). Split the ACs into vertical slices (lite: one slice), one commit per slice:
   - `acs`, `seam`, `dependsOn`.
   - `files`: only files actually changed; `commit.py` refuses a commit with missing or extra files. Changed behaviour → `rg -n "<affected state / field>" docs`, include related code, tests, diagrams, scenarios.
   - `tddTests` + `expectedRed`: `AssertionError` or a domain exception; setup / infrastructure errors are invalid. Destructive I/O is tested at the seam with a fake connection.
   - `verificationTests`: existing tests that only need to stay green.
   - `governingDocs`: file → `path/to/doc.md::section` (an ADR applying to the whole file may drop `::`); the same references must appear in the `Tài liệu chi phối` row.
   - An AC not automatically testable → `untestable` with a manual check.

   Done when every AC belongs to exactly one slice or is in `untestable`.
9. **Plan.** Push the slices in one go, then run `state.py check <T>`, `check_ac_trace.py <T> --planned`, `plan.py <T>`. Slices changed after G1 → update state and regenerate the plan before coding. Done when all three are green.
10. **⛔G1** (format in `SKILL.md` → *Gate*). Summary: `plan.md`; governing docs; new decisions; files to change (flag `backend/shared/`); mode; `untestable` ACs; tests in `notes.baselineRed`. Ask to approve slices and mode together with remaining open decisions.
11. **Approved.** Commit *spec* + *plan* (and any triaged `Status:` lines), change phase, print the clear point:

    ```bash
    python3 S/scripts/commit.py <T> --task plan -m "docs: plan <topic> ticket" -- <ticket folder> [<triaged ticket spec.md>…]
    python3 S/scripts/state.py transition <T> --to code --gate g1 --next "S1: viết test red đầu tiên" --reason "G1 approved"
    ```

## Done when

Baseline ran; `<K>-map.md` has every file to change; every AC is in a slice or `untestable`; every file to change has governing docs and every open choice has a row in `## Quyết định`; `state.py check` and `check_ac_trace.py --planned` are green; the `Task: plan` commit exists; `gates.g1` has a date and `phase` is `code`.
