---
name: ship-ticket-fashion
description: Làm ticket `.scratch/` của Fashion Store khi người dùng nói "làm ticket NN", "làm tiếp", "làm module X", "retro PR #N", hoặc hỏi tiến độ / ticket tiếp theo: grilling tới merge, lập spec + ticket cho module mới.
argument-hint: "[<feature>/<NN> | <NN> | <module>] [grill|code|report|review|sync|ship|done|retro] | retro #<PR>"
---

# ship-ticket-fashion

Tin nhắn cho người dùng viết tiếng Việt. Mỗi lần chạy đưa **một** ticket qua vòng dưới; chỉ dừng ở gate, ở *Cần người dùng* (`reference/rules.md`), hoặc khi xong.

- `S` = `.claude/skills/ship-ticket-fashion`, tính từ gốc repo.
- `<T>` = `<feature>/<NN>`, ví dụ `backend-bootstrap/16`.
- `<K>` = `<feature>-<NN>`, tên file của ticket trong `.git/ship-ticket-fashion/`: state `<K>.json`, bản đồ code `<K>-map.md`, finding review `<K>-review.md`. Thư mục nằm trong `.git/` nên không bị commit và còn nguyên sau `/clear`.

**Codex:** đọc `.agents/skills/ship-ticket-fashion/SKILL.md` trước; file đó đổi công cụ, phase và script vẫn dùng chung ở `S`.

## Bắt đầu

Máy Windows: đọc `gotchas/windows-shell.md` và thay `python3` bằng `python` trong mọi lệnh mẫu.

1. Chạy riêng `python3 S/scripts/state.py start [<T>]`. Output (ticket, phase, `next`, slice, gate, cờ, dòng `READ`) thay cho việc đọc file state.
   - `NO STATE` kèm `FRONTIER` → `reference/pick-ticket.md`.
   - Tham số là module hoặc mốc chưa có ticket (`catalog`, `M1`) → `phases/0-plan.md`.
   - `retro #<PR>` → bỏ qua `start`, làm `phases/8-retro.md` mục *Retro một PR*.
2. Read mọi file sau `READ`, mỗi file một lần gọi.
3. Làm từ `next`. Tham số `[phase]` ghi đè phase, trừ khi gate chưa duyệt.

## Vòng

```
0 plan (khi frontier rỗng)
1 grill → ⛔G1 → 2 code → 3 report → 4 review → 5 sync → ⛔G2 → 6 ship → 7 done → closed
                    ↑                         │          │
                    └── review / sync đổi hành vi ───────┘
```

Phase 7 vào **8 retro** chỉ khi `retro_batch.py status` báo đủ 10 ticket mới đã merge.

| # | File | Skill (`mattpocock-skills:`) | Kết quả |
| --- | --- | --- | --- |
| 0 | `phases/0-plan.md` | `grilling`; người dùng gõ `/mattpocock-skills:to-spec`, `to-tickets`, `improve-codebase-architecture` | spec + ticket của mốc mới |
| 1 | `phases/1-grill.md` | `grilling`; `codebase-design` khi có interface public; `research` khi bọc việc của thư viện | nhánh, baseline xanh, `<K>-map.md`, *spec* + *plan* đã commit, ⛔G1 |
| 2 | `phases/2-code.md` | `tdd`; `diagnosing-bugs` khi đỏ sai dự kiến | mọi slice xanh, mỗi slice một commit |
| 3 | `phases/3-report.md` | — | `report.md` |
| 4 | `phases/4-review.md` | `code-review` + agent trục Bug; `diagnosing-bugs` | `<K>-review.md`, mọi finding có kết luận |
| 5 | `phases/5-sync.md` | `domain-modeling` khi có thuật ngữ / ADR mới | tài liệu khớp code, ⛔G2 |
| 6 | `phases/6-ship.md` | `pr`; `diagnosing-bugs` khi CI đỏ | PR mở, CI xanh, ticket đóng trong PR |
| 7 | `phases/7-done.md` | — | merge khi người dùng bảo |
| 8 | `phases/8-retro.md` | `writing-for-agents`; người dùng gõ `/mattpocock-skills:retro` | một PR cải tiến cho đợt |

Skill viết `/mattpocock-skills:<tên>` chỉ người dùng gọi được: agent đề xuất người dùng gõ. Skill không có `/` thì agent gọi bằng Skill tool.

## Mode

**lite** khi đủ cả ba: ≤ 3 acceptance criteria, không thêm model hay migration, không thêm endpoint. Ngược lại **full**. Phase 1 đề xuất, G1 chốt. Lite: một slice, phiên chính tự code và sửa, grilling chỉ hỏi phần còn mở, review một agent cho cả ba trục.

## Sub-agent

Phiên chính điều phối và giữ gate, tài liệu, ship, done, retro. Việc đọc nhiều file hoặc chạy nhiều lượt giao cho sub-agent (`general-purpose`, không đặt `model`):

| Việc | Full | Lite |
| --- | --- | --- |
| Phase 1, bản đồ code | `Explore`; phiên chính lưu kết quả vào `<K>-map.md` | như full |
| Phase 2, mọi slice | **một** *implementer* làm hết slice theo DAG | phiên chính |
| Phase 4, review | `code-review` (Spec + Standards) song song một agent Bug | một agent cả ba trục |
| Phase 4 vòng sửa, phase 6 CI đỏ | *implementer* của phase 2, gửi bằng `SendMessage` | phiên chính |

- **Prompt là địa chỉ**: `<T>`, việc (slice / vòng sửa), mode và đường dẫn cần đọc theo thứ tự `S/reference/sub-agent.md`, `S/reference/rules.md`, file phase, `.git/ship-ticket-fashion/<K>-map.md`, thư mục ticket. Không chép nội dung file vào prompt.
- **Báo là gọi**: tin nhắn báo giao việc chứa luôn lệnh gọi `Agent`.
- **Làm tiếp, không tạo lại**: câu trả lời *Cần người dùng*, vòng sửa, chạy lại đều gửi cho agent cũ bằng `SendMessage` (nạp bằng `ToolSearch "select:SendMessage"`). `ListAgents` không còn agent đó thì tạo mới với cùng prompt địa chỉ.
- Phiên chính tin kết quả trả về và state, không đọc lại file sub-agent đã đọc.

## Gate

*Gate* (G1, G2) là quyết định của người dùng; script xanh / đỏ chỉ là *check*.

1. **Tóm tắt**: bảng gọn các mục phase liệt kê, mỗi điểm mở kèm khuyến nghị.
2. **Hỏi**: `AskUserQuestion` chỉ chứa điểm cần trả lời; ≤ 4 câu mỗi lần, 2–4 lựa chọn, lựa chọn khuyên dùng đứng đầu kèm "(khuyên dùng)". Gom điểm liên quan vào một câu.

Gate xong khi mọi điểm mở có câu trả lời đã ghi vào ticket hoặc state.

## State, ticket, commit

- Schema state: `reference/state.md`. Ghi field bằng `state.py set` / `push`. Đổi phase chỉ qua lệnh dưới; script từ chối nhảy cóc, vào `code` khi chưa có G1 hoặc *spec*/*plan* chưa commit, vào `ship` khi chưa có G2, vào `report` khi còn slice chưa xong:

  ```bash
  python3 S/scripts/state.py transition <T> --to <phase> --next "<một việc cụ thể>" --reason "<tiêu chí đã đạt / gate>" [--gate g1|g2]
  ```

- Ticket là thư mục `.scratch/<feature>/issues/NN-<slug>/`: `spec.md` (phase 1 thêm `## Quyết định`), `plan.md` (sinh bằng `plan.py`), `report.md` (phase 3 viết, phase 4 và 5 ghi đè).
- Một *task* là đúng một commit, qua `python3 S/scripts/commit.py <T> --task <task> -m "<subject>" [--body "…"] -- <file>…` (gắn trailer `Refs:`, `Task:`; hook sửa file thì tự add lại). Danh sách task và subject: `templates/commit-msg.md`. `commit_map.py <T> [--md]` in commit → task → AC.

**Điểm clear** (phase chỉ ra chỗ): in `Đã lưu state (<phase>/<slice>). Có thể /clear rồi chạy lại /ship-ticket-fashion <T> để tiếp tục.`, rồi làm tiếp trừ khi người dùng ngắt. Còn ngữ cảnh chưa ghi vào state hay ticket (grilling dở) thì thêm: `Cần mang ngữ cảnh đó sang phiên mới thì gõ /mattpocock-skills:handoff <T> <phase>.`
