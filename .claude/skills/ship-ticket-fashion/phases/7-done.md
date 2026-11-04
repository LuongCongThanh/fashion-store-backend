# Phase 7 — done

1. Tell the user: PR URL, title, CI status, each AC → result, what is unchecked (`untestable` ACs), new tickets created. Say plainly what has not been verified.
2. Ask with `AskUserQuestion`: merge now (recommended when CI is green and nothing is open), or wait (the user reviews or merges later).
3. Merge now: `python3 S/scripts/merge.py <T>`. It refuses unless phase is `done` and the PR is open into `dev`, not a draft, conflict-free, with every check green; then it squash-merges with the commit → task table as the body (so `dev` still shows which commit belonged to which task after the branch is deleted), switches to `dev` and pulls, prints progress and moves the ticket to `closed`. Wait: keep phase `done`, set `next=chờ merge PR #<number>` and stop. Next run, `reference/resume.md` checks the PR state.
4. **Merged outside `merge.py`** (the user merged on GitHub): `git switch dev && git pull`, then `state.py transition <T> --to closed --next "chọn ticket tiếp theo" --reason "merged"`.

## Done when

Waiting for merge: `phase` is `done`. Merged: ticket `resolved` on `origin/dev`, `phase` is `closed`.
