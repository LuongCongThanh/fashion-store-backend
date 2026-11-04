# Phase 4 — three-axis review + fix rounds

Goal: code **and tests** match the ticket and the repo's standards. Mandatory in every mode.

1. **Scripts first** (cheaper than reviewers; their output goes to the reviewers):

   ```bash
   python3 S/scripts/state.py check <T>
   python3 S/scripts/check_ac_trace.py <T>
   python3 S/scripts/check_ship.py <T>
   ```

   Errors → fix before review. `WARN ticket chưa commit` is expected: `report.md` is committed in task `sync`.
2. **Review.** `.git/ship-ticket-fashion/<K>-review.md` already has every axis (resuming after `/clear` or an interruption) → skip this step and read that file. The main session writes each returned report into that file right away, under headings `## Spec`, `## Standards`, `## Bug`; reviewers only return reports. Done when the file has all three headings.

   Full: in one turn, launch 2a and 2b in parallel with separate briefs. Lite: one `general-purpose` agent covers all three axes with the briefs of 2a and 2b.

   **2a. Spec + Standards**: `mattpocock-skills:code-review`, fixed point `origin/dev`; the spec is the ticket's `spec.md` (including `## Quyết định`) plus `userRequested` from state (in scope). Standards sources: `docs/architecture/13-python-django-coding-style.md`, `CONTRIBUTING.md`, `docs/architecture/02-backend-structure.md`, `docs/architecture/modules/<module>.md`, `docs/architecture/12-testing-strategy.md`, the checklist in `.github/pull_request_template.md`. Add:
   - **Spec**: "For each AC, name the test asserting its outcome. Report ACs or AC branches without a test, and tests that only assert a mock was called instead of the outcome." Attach the `check_ac_trace.py` output.
   - **Standards**: "Test files are in scope. Check the diff against each *Tài liệu chi phối* item in `## Quyết định`; report code that contradicts the docs without a recorded reason. Walk every bullet of `CONTRIBUTING.md` section *Quy ước code* over every changed test file." With an `Interface / seam` row → add: "Check new interfaces against that row and apply the _deletion test_; report public functions that only forward a call, and seams with a single adapter and no recorded reason."

   **2b. Bug**: one `general-purpose` sub-agent given `git diff origin/dev...HEAD`, the commit list, the ticket's `spec.md` and `<K>-map.md`. Brief: "Hunt for wrong runtime behaviour that Spec and Standards do not look at: data dropped on write, safety guards bypassed, logic re-implementing what a library already does. Read the code around each hunk and its callers. A plan commit changing the `Status:` line of a triaged ticket is the expected process. Code each finding `B1`, `B2`…, with `file:line` and a concrete failing scenario."

   Shared brief: report in English, under 600 words, every finding with `file:line` and the quoted standard / AC; temp files go to `.git/ship-ticket-fashion/`, and afterwards `git status --short` shows only ticket files.
3. **Verify** each finding that will change code: open the quoted line yourself first; reviewers can be wrong. Finding `B<n>` → `mattpocock-skills:diagnosing-bugs` through the end of that skill's phase 1: one test red on the exact failure scenario, run via `run_logged.py --label <K>-R<n>-red` (the log is the fix round's red evidence). Cannot reproduce → *report only*.
4. **Classify** each finding:
   - *fix*: a standards violation in the diff; code contradicting an AC or `## Quyết định`; a missing or weak test for an AC.
   - *revert*: something the agent added out of scope (no AC, no request), even if harmless.
   - *report only*: smells, pre-existing bugs, points for the user to decide. Out-of-scope items still worth doing → backlog (`reference/rules.md`, *Scope*).

   Present the findings table (code, `file:line`, class, fix) and ask with `AskUserQuestion` (multi-select) which to fix now; *fix* items are preselected as recommended. List only fix groups, no "fix nothing" option: the user can drop everything via Other. Ask before reverting anything in `userRequested`. Record the choice at the end of `<K>-review.md`.
5. **Fix rounds, at most 2.** Full: send the implementer (`SKILL.md` → *Sub-agents*) the `<K>-review.md` path and the chosen finding codes. Lite: main session.
   - Round 1 handles every chosen item as one batch; round 2 only what round 1 left red or broke.
   - Behaviour-changing items: red test before the fix.
   - One commit per round: `commit.py <T> --task R1` (round 2: `R2`), subject `fix(<scope>): address review findings on <topic>`, body lists the finding codes fixed (`B1`, `S2`…).
   - End of round: full check (*Machine checks*) and `check_ac_trace.py`.

   Still open after round 2 → raise at G2.
6. **Record** the verdict table in `report.md` (section *Review*), in Vietnamese: one row per finding (code, `file:line`, đã sửa / chỉ báo / hoàn tác / bác, a few words of reason); smells grouped in one row. Update the AC → evidence table if tests changed.
7. `state.py transition <T> --to sync --next "đồng bộ tài liệu" --reason "review xong"`, print the clear point.

## Done when

Step 1 scripts green; `<K>-review.md` has all three axes; every finding has a verdict in the report; at most 2 fix rounds ran and the last is green; `phase` is `sync`.
