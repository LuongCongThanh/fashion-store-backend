# Kế hoạch

Sinh bằng `plan.py` từ state của skill. Mỗi task là đúng một commit có trailer `Task: <task>`.

| Task | AC | Seam | Test dự kiến | File | Sau |
| --- | --- | --- | --- | --- | --- |
| S1 | 1, 2 | backend/Makefile: export PYTHONUTF8 := 1 cho mọi recipe | — | `backend/Makefile`<br>`docs/architecture/08-local-development.md` | — |

AC 1 không test tự động: Kiểm tay: cài make bằng winget ezwinports.make, chạy make lint > out.txt trong backend/ (Git Bash), cần exit 0

AC 2 không test tự động: Kiểm bằng job backend của CI ở phase 6

Commit dự kiến: `plan` → `S1` → `R1 (khi review cần sửa)` → `sync` → `close`.
