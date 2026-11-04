# Rules (every phase)

- **Scope = acceptance criteria + what the user asked.** Change only code that an AC, the ticket's `## Việc cần làm` or `## Quyết định` requires. Extra user requests: do them, record in state `userRequested` and the report's *Thay đổi theo yêu cầu* section, test them like an AC. Good but out-of-scope work → one line in `.scratch/backlog.md`; it becomes a `needs-triage` ticket (same feature, next number) only when it blocks the current or next milestone, and the ticket names the blocked milestone.
- **`docs/` is the source of truth**: code follows the docs. A file's *governing docs* (*tài liệu chi phối*) are the sections that rule how it is written: `docs/architecture/` (map in `docs/architecture/README.md`), rules in `docs/business/`, ADRs in `docs/adr/`. Phase 1 records them in `## Quyết định`; code and review check against them. A ticket that deliberately deviates → reason in `## Quyết định`, fix the docs in phase 5 of the same PR.
- **One home per kind of knowledge.**
  - Ticket decisions → `## Quyết định` in `spec.md` (table Chủ đề | Quyết định).
  - Decisions reaching beyond the ticket (`common` API, ticket splits, scope changes) → **Decisions-so-far** in `.scratch/mvp-roadmap/map.md`.
  - Lasting architecture decisions → ADR via `mattpocock-skills:domain-modeling`. Terms → `GLOSSARY.md`, avoiding words under _Avoid_.
  - Slices, `next`, AC → test → state; the human-readable print is `plan.md`.
  - Code the ticket touches → `.git/ship-ticket-fashion/<K>-map.md`; review findings → `<K>-review.md`.
  - Outcome (done, not done, gaps) → `report.md`. Anything a machine can check → a test, a script in `S/scripts/`, lint or a hook.
- **Needs user** is a decision outside the gates: out-of-scope change; touching `common/` when the ticket does not mention it; a red test outside the ticket and not in the baseline; a hook block not fixable within scope; missing or contradictory docs, or code forced to break an ADR (`docs/agents/domain.md`); environment errors (DB, Redis, `.env`). The main session asks at once with `AskUserQuestion`; sub-agents follow `reference/sub-agent.md`.
- **Design vocabulary**: *module* means a business module, one Django app under `apps/` (ADR 0018). In code design talk use *seam*, *interface*, *depth*, *adapter*, *deletion test* from `mattpocock-skills:codebase-design`; what that skill calls a module, name concretely (function, class, package).
- **Talking to the user**: codes the user did not write come with their meaning: `AC2 (fail-open khi Redis tắt)`, `ticket 15 (Docker Compose local)`.

## Machine checks

Invoking this skill is consent to run tests. Commands run at the repo root, always through `run_logged.py`: log at `.git/ship-ticket-fashion/logs/<label>.log`, green prints one line, red prints the tail; need more → `grep -n` the log. Without `make`, the script runs the `Makefile` recipe itself.

```bash
python3 S/scripts/run_logged.py --label fmt  -- make fmt
python3 S/scripts/run_logged.py --label lint --keep-going -- make lint
python3 S/scripts/run_logged.py --label test -- make test
```

- **Lint**: `fmt` then `lint`; `--keep-going` prints every tool's errors in one run; fix them all before rerunning. Trust mypy only through `make lint`.
- **Full check** (`fmt`, `lint`, `test`) runs at: end of phase 2, end of each fix round, phase 5 when code changed since the last green, phase 6 when the rebase pulled new commits. End of each slice: `fmt`, `lint` and the slice's tests. A milestone with no code-changing commit since the last green reuses that result.
- **Log-reading tests** (`caplog`, fixture `json_logging`): also run that test file with `uv run pytest -p no:xdist <file>`.
- **Red outside the ticket**: listed in `notes.baselineRed` (already red on `origin/dev`, recorded in phase 1) → one line in the report, carry on. Not listed → this branch caused it: fix; not fixable within scope → *Needs user*. A red step without a test id (coverage gate) is recorded by step name, e.g. `check_module_coverage`.
- Write several state fields in one `state.py set` / `push`. Keep `.env` contents, secrets and tokens out of output.
