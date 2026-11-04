# Phase 7 — done

1. Tell the user: PR URL, title, CI status, each AC → result, what is unchecked (`untestable` ACs), new tickets created. Say plainly what has not been verified.
2. Ask with `AskUserQuestion`: merge now (recommended when CI is green and nothing is open), or wait (the user reviews or merges later).
3. Merge now:

   ```bash
   python3 S/scripts/commit_map.py <T> --md > .git/SQUASH_BODY.md
   GH_TOKEN="$(gh auth token --user LuongCongThanh)" gh pr merge <number> --squash --delete-branch -F .git/SQUASH_BODY.md
   git switch dev && git pull
   python3 S/scripts/progress.py
   ```

   The squash commit body on `dev` keeps the commit → task table, so after the branch is deleted you can still see which commit belonged to which task. Wait: keep phase `done`, set `next=chờ merge PR #<number>` and stop. Next run, `reference/resume.md` checks the PR state.
4. **After merge**: `state.py transition <T> --to closed --next "chọn ticket tiếp theo" --reason "merged"`.

## Done when

Waiting for merge: `phase` is `done`. Merged: ticket `resolved` on `origin/dev`, `phase` is `closed`.
