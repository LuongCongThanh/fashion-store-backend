# Phase 0 — plan the next milestone

Use when the current milestone's frontier is empty or nearly so, the user wants a module that has no tickets yet (take the milestone containing it), or wants tickets re-split. Per `.scratch/mvp-roadmap/map.md`, a milestone's spec is created when the previous one is nearly done, so it builds on existing code. No state of its own: the output is files in `.scratch/`.

## Spec for a new milestone

1. Take the milestone's row from the **Notes** table of `map.md`: folder, content, user stories, "Xong khi" condition. `progress.py` prints milestones without a folder.
2. An `Explore` sub-agent reads and summarises: those user stories in `docs/business/03-user-stories.md`, related rules in `04-business-rules.md` and `05-order-lifecycle.md`, architecture docs and ADRs of the modules touched, and existing `shared` code.
3. `mattpocock-skills:grilling` to settle scope and decisions.
4. Ask the user to type `/mattpocock-skills:to-spec` → `.scratch/<slug>/spec.md`. Check it against the shape of `.scratch/backend-bootstrap/spec.md`: Bối cảnh, Phạm vi, Quyết định, Ticket (ordered list; `progress.py` uses this order for the frontier), Ngoài phạm vi.
5. Ask the user to type `/mattpocock-skills:to-tickets` → `.scratch/<slug>/issues/NN-<slug>/spec.md`. Check each ticket against the shape below; `plan.md` and `report.md` are created while working the ticket.

## Hotspot

When the hotspot condition in `reference/pick-ticket.md` step 4 holds, or the user asks about the architecture of an area → suggest the user type `/mattpocock-skills:improve-codebase-architecture <area>` before creating or working more tickets there. Candidates the user picks go through step 5 and become `needs-triage` tickets; overlapping old tickets are merged in or closed `wontfix`.

## Ticket `spec.md` shape

```markdown
# <Tiêu đề tiếng Việt>

Status: ready-for-agent

Blocked by: NN, NN

Spec: [spec.md](../../spec.md)

## Việc cần làm

## Acceptance criteria

- [ ] <hành vi kiểm chứng được bằng test>
```

- Each ticket is a _tracer bullet_ that fits one PR (under ~400 lines excluding migrations) and runs end to end.
- Acceptance criteria are behaviours that can become test names; cite related `US-xxx`, `BR-xxx`.
- Splitting a large ticket: the first part keeps the old number, split-off parts take the feature's next numbers, with `Tách từ ticket [NN](../NN-…/spec.md).` Existing tickets are never renumbered.

## Done when

- Every user story in the milestone's row is referenced by at least one ticket.
- `progress.py` prints a non-empty frontier for the new milestone, with no warnings.
- `map.md`: the Tiến độ table has the milestone's row, Decisions-so-far has the spec-creation date line.

Ship the planning as a docs PR (branch `docs/<slug>-spec`) per `phases/6-ship.md` sections 1, 2, 3, then rerun the skill to pick a ticket.
