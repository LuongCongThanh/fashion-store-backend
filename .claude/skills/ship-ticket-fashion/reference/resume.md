# Resume

Read when `state.py start` prints `READ …/reference/resume.md`: flags are set, a slice is open, or the phase needs more than continuing from `next`.

## Flags first, before anything else

- `BRANCH RED` (current branch differs from state `branch`) → ask the user: switch to the state's branch (recommended), or make the current branch the new `branch`.
- `DIRTY` → check `git status --short`: ticket files → continue; files from other work → ask the user whether to keep or stash.
- `BEHIND origin/dev` → `git fetch origin && git rebase origin/dev` before phase 6; in earlier phases rebase when convenient and rerun tests afterwards.
- `SLICE OPEN` → the implementer per `SKILL.md` → *Sub-agents*; if the agent is still running, wait for it to return.
- `NO PR` in phase `done` → the PR was never opened: go back to phase 6, open-PR step.

## By phase

| Phase | Resume |
| --- | --- |
| `grill` | G1 asked but unanswered → present G1 again from `## Quyết định` in `spec.md` and the slices in state |
| `review` | `<K>-review.md` has all three axes → skip the review step, continue from verification; a missing axis → rerun only that axis |
| `sync` | G2 asked but unanswered → present G2 again; G2 approved but no `Task: retro` commit → `phases/8-retro.md` steps 4–5 |
| `done` | `gh pr view <pr> --json state` (account in `phases/6-ship.md`): `MERGED` → phase 7 step 4; `OPEN` → ask merge or wait |
| `closed` | Ticket finished: run `progress.py`, propose the next ticket |
