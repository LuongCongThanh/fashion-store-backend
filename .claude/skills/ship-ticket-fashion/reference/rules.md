# Quy tắc (mọi phase)

- **Phạm vi = acceptance criteria + điều người dùng yêu cầu.** Chỉ sửa code mà một AC, mục `## Việc cần làm` hoặc `## Quyết định` của ticket đòi hỏi. Người dùng yêu cầu thêm thì làm, ghi vào `userRequested` của state và mục *Thay đổi theo yêu cầu* của báo cáo, test như một AC. Việc tốt nhưng ngoài phạm vi → một dòng trong `.scratch/backlog.md`; chỉ thành ticket `needs-triage` (cùng feature, số tiếp theo) khi nó chặn mốc đang làm hoặc mốc kế tiếp, và ticket ghi mốc bị chặn.
- **`docs/` là nguồn chuẩn**: code làm theo tài liệu. *Tài liệu chi phối* của một file là các mục quy định cách viết nó: `docs/architecture/` (bản đồ ở `docs/architecture/README.md`), quy tắc trong `docs/business/`, ADR trong `docs/adr/`. Phase 1 ghi chúng vào `## Quyết định`; code và review đối chiếu với chúng. Ticket cố ý làm khác tài liệu → ghi lý do trong `## Quyết định`, sửa tài liệu ở phase 5 cùng PR.
- **Mỗi loại kiến thức một chỗ.**
  - Quyết định của ticket → `## Quyết định` trong `spec.md` (bảng Chủ đề | Quyết định).
  - Quyết định ảnh hưởng ngoài ticket (API của `shared`, tách ticket, đổi phạm vi) → **Decisions-so-far** của `.scratch/mvp-roadmap/map.md`.
  - Quyết định kiến trúc lâu dài → ADR qua `mattpocock-skills:domain-modeling`. Thuật ngữ → `GLOSSARY.md`, tránh từ ở mục _Avoid_.
  - Slice, `next`, AC → test → state; bản in cho người đọc là `plan.md`.
  - Code ticket chạm tới → `.git/ship-ticket-fashion/<K>-map.md`; finding review → `<K>-review.md`.
  - Kết quả (đã làm, chưa làm, gap) → `report.md`. Điều máy kiểm được → test, script trong `S/scripts/`, lint hoặc hook.
- **Cần người dùng** là quyết định ngoài gate: thay đổi ngoài phạm vi; sửa `backend/shared/` mà ticket không nhắc; test đỏ ngoài ticket không nằm trong baseline; hook chặn không sửa được trong phạm vi; tài liệu thiếu, mâu thuẫn, hoặc code buộc phải trái ADR (`docs/agents/domain.md`); lỗi môi trường (DB, Redis, `.env`). Phiên chính hỏi ngay bằng `AskUserQuestion`; sub-agent làm theo `reference/sub-agent.md`.
- **Từ vựng thiết kế**: *module* là module nghiệp vụ trong `modules/` (ADR 0006). Bàn thiết kế code dùng *seam*, *interface*, *depth*, *adapter*, *deletion test* của `mattpocock-skills:codebase-design`; thứ skill đó gọi là module thì gọi bằng tên cụ thể (hàm, class, package).
- **Nói với người dùng**: mã người dùng không tự viết thì kèm nghĩa: `AC2 (fail-open khi Redis tắt)`, `ticket 15 (Docker Compose local)`.

## Check máy

Gọi skill này là đồng ý chạy test. Lệnh chạy trong `backend/`, luôn qua `run_logged.py`: log ở `.git/ship-ticket-fashion/logs/<label>.log`, xanh in một dòng, đỏ in đoạn cuối; cần thêm thì `grep -n` trên log. Máy không có `make` thì script tự chạy recipe của `Makefile`.

```bash
python3 S/scripts/run_logged.py --label fmt  --cwd backend -- make fmt
python3 S/scripts/run_logged.py --label lint --cwd backend --keep-going -- make lint
python3 S/scripts/run_logged.py --label test --cwd backend -- make test
```

- **Lint**: `fmt` rồi `lint`; `--keep-going` in lỗi của mọi công cụ trong một lần, sửa hết rồi mới chạy lại. mypy chỉ tin kết quả của `make lint`.
- **Full check** (`fmt`, `lint`, `test`) chạy ở: cuối phase 2, cuối mỗi vòng sửa, phase 5 khi code đổi sau lần xanh gần nhất, phase 6 khi rebase kéo về commit mới. Cuối mỗi slice: `fmt`, `lint` và test của slice. Mốc không có commit đổi code kể từ lần xanh gần nhất thì dùng lại kết quả đó.
- **Test đọc log** (`caplog`, fixture `json_logging`): chạy thêm file test đó với `uv run pytest -p no:xdist <file>`.
- **Đỏ ngoài ticket**: có trong `notes.baselineRed` (đỏ sẵn trên `origin/dev`, ghi ở phase 1) → một dòng trong báo cáo, làm tiếp. Không có → do nhánh này: sửa; không sửa được trong phạm vi → *Cần người dùng*. Bước đỏ không có test id (cổng coverage) thì ghi tên bước, ví dụ `check_module_coverage`.
- Ghi nhiều field state trong một lần `state.py set` / `push`. Giữ nội dung `.env`, secret, token ngoài output.
