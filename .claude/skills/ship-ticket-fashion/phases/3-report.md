# Phase 3 — report

1. Write the report per `templates/report.md` into the ticket's `report.md` (create it with first line `# Báo cáo` if missing), dated, in Vietnamese. Later runs (after review, sync) **overwrite** this report instead of adding a new one: the ticket keeps only the latest result.
   - One row per AC: the proving test (`file::test`, from state), or the `untestable` reason and manual check.
   - Numbers from the logs `.git/ship-ticket-fashion/logs/lint.log` and `test.log` (test count, duration, coverage if any).
   - *Commit* section: output of `python3 S/scripts/commit_map.py <T> --md`.
   - *Ghi chú cho retro*: at most 3 lines on what cost effort, with an evidence pointer, or `Không`. Keep and update it when the report is overwritten in review/sync; point to durable evidence rather than logs a later ticket will overwrite. This step only records; phase 5 retro analyses.
2. Show the user the report (the exact text written to `report.md`).
3. Leave `report.md` uncommitted: phases 4 and 5 still overwrite it, and it is committed once in task `sync`.
4. `state.py transition <T> --to review --next "chạy check máy rồi code-review" --reason "báo cáo đã ghi"`, print the clear point.

## Done when

Every AC has a row in the AC → evidence table; sections Đã làm, Chưa làm, Gap have content or "Không"; the *Commit* section lists every commit on the branch; `phase` is `review`.
