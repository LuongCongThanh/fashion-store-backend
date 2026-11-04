# Phase 2 — code with TDD

Full: the *implementer* (`SKILL.md` → *Sub-agents*). Lite: the main session.

## Before the first slice

Read `.git/ship-ticket-fashion/<K>-map.md`, the *governing docs* sections (the `Tài liệu chi phối` row in `## Quyết định`), `docs/architecture/13-python-django-coding-style.md` (sections matching the file type: view, service, model, test…) and `CONTRIBUTING.md` section *Quy ước code*. Follow the names, structure and conventions there. A new view under `/api/v1/` needs a `summary` and English examples (`04-api-contract.md` section 5.6); `make lint` blocks it via `gen_openapi.py --check`.

## Each slice

1. `state.py set <T> slices.<id>.status=code currentSlice=<id>`.
2. `mattpocock-skills:tdd`, testing only at the slice's seam.
   - Each `tddTests`: write the test → `tdd.py <T> <slice> red <test-id>` shows the expected `expectedRed` → minimal code → `tdd.py <T> <slice> green <test-id>`. Function not yet defined → declare its signature raising `NotImplementedError` first, so red is not an `AttributeError`.
   - Each `verificationTests`: `tdd.py <T> <slice> verify <test-id>` after the change.
   - Red differs from `expectedRed`, or still red after two fixes → `mattpocock-skills:diagnosing-bugs`, using the `tdd.py` command as the feedback loop.

   `tdd.py` keeps the evidence; `state.py set` / `push` cannot write the `tdd` field.
3. A red test outside the slice → *Machine checks*, *Red outside the ticket*.
4. Migration needed → `uv run python manage.py makemigrations <app>`, reread the generated file; migrations must be reversible (`docs/architecture/12-testing-strategy.md` section 6).
5. **Lint** (*Machine checks*). Done when lint and the slice's tests are green.
6. Commit the slice: `python3 S/scripts/commit.py <T> --task <id> -m "<subject>" --body "<why>" -- <file>…` (`templates/commit-msg.md`). The script refuses files outside `slice.files`: a legitimate extra file → update state and regenerate the plan first. More changes in the slice before returning → `git commit --amend --no-edit` (not pushed yet, so safe).
7. `state.py set <T> slices.<id>.status=done 'slices.<id>.tests=[…]' 'slices.<id>.handoff=[…]' 'next=…'`; record actual test names if they changed from the plan.

## End of phase

The implementer (lite: main session) runs the full check (*Machine checks*; lint is already green from the last slice) and `check_ac_trace.py <T>` before returning. Red → fix within the ticket's scope and rerun; red outside scope → *Needs user*. The main session takes the result, runs `state.py transition <T> --to report --next "viết báo cáo" --reason "mọi slice xanh"` and prints the clear point.

## Done when

Every slice `done`; `tddTests` have red/green, `verificationTests` have a verified green; `make lint`, `make test`, `check_ac_trace.py` green; `commit_map.py <T>` prints exactly one commit per slice and no `FAIL`; `phase` is `report`.
