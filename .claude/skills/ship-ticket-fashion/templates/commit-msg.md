# Commit message

```
<type>(<scope>): <English description, present tense, lowercase start, no trailing period>

<Body: WHY, plus what this commit leaves undone or any gap.>

Refs: .scratch/<feature>/issues/NN-<slug>
Task: <task>
```

`commit.py` writes the two trailer lines; the agent provides only subject and body. `Refs:` per `docs/architecture/11-git-workflow.md` section 3; `Task:` says which part of the ticket the commit belongs to:

| Task | Phase | Subject |
| --- | --- | --- |
| `plan` | 1 | `docs: plan <topic> ticket` (`spec.md` + `plan.md`) |
| `S<n>` | 2 | `feat` / `fix` / `refactor` / `test` per what the slice does |
| `R1`, `R2` | 4 | `fix(<scope>): address review findings on <topic>`, body lists finding codes |
| `sync` | 5 | `docs: sync docs and report for <topic> ticket` |
| `retro` | 5 | `chore: refine ship-ticket-fashion after <topic> ticket` |
| `close` | 6 | `docs: close <topic> ticket` |
| `ci` | 6 | `fix(<scope>): …` per the CI failure; repeatable |

`type`, `scope`, `BREAKING CHANGE`: `docs/architecture/11-git-workflow.md` section 3. The `commitizen` hook blocks malformed messages. No AI attribution lines (`Co-Authored-By` naming an assistant) and no assistant names in commit text.

Example: `feat(common): return ErrorDTO for unhandled API errors` + `Task: S2`
