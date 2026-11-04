# Pick a ticket

Read when `state.py start` prints `NO STATE` with `FRONTIER`: no ticket in progress. Every question below goes into **one** ask (format in `SKILL.md` → *Gate*).

1. **Progress.** Run `python3 S/scripts/progress.py` and summarise it for the user.
2. **Recommended ticket.** Follow the latest priority order in *Decisions-so-far* of `.scratch/mvp-roadmap/map.md`. No order yet → propose: real bugs first, then CI gates; once the user approves, record that order in *Decisions-so-far*.
3. **`needs-triage` tickets** (if any): suggest the user type `/mattpocock-skills:triage <ticket folder>`. If the user wants to answer now, ask per ticket: `ready-for-agent`, `ready-for-human`, `wontfix` or later (`docs/agents/triage-labels.md`). Write the `Status:` line accordingly; that file is committed with the `plan` commit in phase 1 (step *Approved*).
4. **Hotspot.** A package already changed by 3+ tickets (`git log --oneline origin/dev -- <package>`) with frontier tickets still there → propose per `phases/0-plan.md` section *Hotspot*.

Empty frontier, or the milestone only has blocked or human tickets left → `phases/0-plan.md` instead of the steps above.

## Done when

The user picked a ticket and every `needs-triage` ticket is answered or deferred; continue with `phases/1-grill.md` for that ticket.
