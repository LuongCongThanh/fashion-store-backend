# Sub-agent contract

Every sub-agent this skill spawns reads this file first. The main session only reads returned results and state: anything not on disk or in the result is lost.

- **Map first, explore second.** `.git/ship-ticket-fashion/<K>-map.md` already lists the ticket's files, signatures, callers, tests and fixtures: start from it, read only files you are changing and files the map lacks. A newly found file a later slice needs → add one line to the map.
- **The implementer keeps the work to the end.** Phase 2: every slice in DAG order (start a slice only after its `dependsOn` are done), one commit per slice, then return once. Review fix rounds and CI failures arrive later via `SendMessage`, reusing the code context you already have.
- **Write before returning.** Everything a later step needs goes to disk: state (`slices.<id>.status`, `handoff`, `tests`, `next`, `untestable`) and commits. Reviewers only return a report; the main session writes `<K>-review.md`.
- **Decisions belong to the user.** On *Needs user* (`reference/rules.md`): record it in state `notes`, return it on the *Needs user* line and stop. The answer comes back via `SendMessage`.
- **User-owned fields**: `gates`, `userRequested` are written by the main session.
- **Unplanned change to `shared/`**: *Needs user* with the blast radius (`git grep -l "<module>" -- "*.py" | wc -l` and which modules), plus the option *keep `shared` unchanged* and what the AC loses with it.
- **Return ≤ 15 lines**, exactly:

  ```
  <Slice / round>: <done / blocked>
  Files changed: <names> (<n> files)
  Tests: <x/y green> · lint: <ok / errors>
  check_ac_trace: <ok / missing AC>
  Plan drift: <none / what + "state updated">
  Needs user: <none / one question per line, with options and a recommendation>
  ```
