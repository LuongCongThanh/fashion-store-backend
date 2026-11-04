# Commit message

```
<type>(<scope>): <mô tả tiếng Anh, thì hiện tại, chữ đầu viết thường, không dấu chấm cuối>

<Thân: VÌ SAO, và phần chưa làm hoặc còn gap của commit này nếu có.>

Refs: .scratch/<feature>/issues/NN-<slug>
Task: <task>
```

`commit.py` viết hai dòng trailer cuối; agent chỉ đưa subject và thân. `Refs:` theo `docs/architecture/11-git-workflow.md` mục 3; `Task:` cho biết commit thuộc phần nào của ticket:

| Task | Phase | Subject |
| --- | --- | --- |
| `plan` | 1 | `docs: plan <chủ đề> ticket` (`spec.md` + `plan.md`) |
| `S<n>` | 2 | `feat` / `fix` / `refactor` / `test` theo việc slice làm |
| `R1`, `R2` | 4 | `fix(<scope>): address review findings on <chủ đề>`, thân liệt kê mã finding |
| `sync` | 5 | `docs: sync docs and report for <chủ đề> ticket` |
| `retro` | 5 | `chore: refine ship-ticket-fashion after <chủ đề> ticket` |
| `close` | 6 | `docs: close <chủ đề> ticket` |
| `ci` | 6 | `fix(<scope>): …` theo lỗi CI; lặp lại được |

`type`, `scope`, `BREAKING CHANGE`: `docs/architecture/11-git-workflow.md` mục 3. Hook `commitizen` chặn sai định dạng.

Ví dụ: `feat(shared): return ErrorDTO for unhandled API errors` + `Task: S2`
