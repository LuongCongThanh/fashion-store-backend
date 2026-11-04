---
name: ship-ticket-fashion
description: Làm ticket `.scratch/` của Fashion Store khi người dùng nói "làm ticket NN", "làm tiếp", "làm module X", "retro PR #N", hoặc hỏi tiến độ / ticket tiếp theo: grilling tới merge, lập spec + ticket cho module mới.
argument-hint: "[<feature>/<NN> | <NN> | <module>] [grill|code|report|review|sync|ship|done] | retro #<PR>"
---

# ship-ticket-fashion

Tin nhắn cho người dùng viết tiếng Việt. Mỗi lần chạy đưa **một** ticket qua vòng dưới; chỉ dừng ở gate, ở *Cần người dùng* (`reference/rules.md`), hoặc khi xong.

- `S` = `.claude/skills/ship-ticket-fashion` (từ gốc repo) · `<T>` = `<feature>/<NN>` · `<K>` = `<feature>-<NN>`.
- `.git/ship-ticket-fashion/` giữ state `<K>.json`, bản đồ code `<K>-map.md`, finding review `<K>-review.md` và `logs/`: ngoài git, còn nguyên sau `/clear`.

**Codex:** đọc `.agents/skills/ship-ticket-fashion/SKILL.md` trước.

## Bắt đầu

Windows: đọc `gotchas/windows-shell.md`, dùng `python` thay `python3`.

1. `python3 S/scripts/state.py start [<T>]`. Output (ticket, phase, `next`, slice, gate, cờ, dòng `READ`) thay cho việc đọc state.
   - `NO STATE` + `FRONTIER` → `reference/pick-ticket.md`.
   - Module hoặc mốc chưa có ticket (`catalog`, `M1`) → `phases/0-plan.md`.
   - `retro #<PR>` → bỏ `start`, làm `phases/8-retro.md` mục *Retro một PR*.
2. Read mọi file sau `READ`.
3. Làm từ `next`. Tham số `[phase]` ghi đè phase, trừ khi gate chưa duyệt.

## Vòng

```
0 plan (frontier rỗng)
1 grill → ⛔G1 → 2 code → 3 report → 4 review → 5 sync + retro → ⛔G2 → 6 ship → 7 done → closed
                    ↑                         │          │
                    └── review / sync đổi hành vi ───────┘
```

Phase `n` ở `phases/<n>-<tên>.md`. Retro (`phases/8-retro.md`) chạy trong phase 5 của mỗi ticket; cải tiến skill đi cùng PR của ticket, token của ticket ghi ở `metrics.md`. Skill viết `/mattpocock-skills:<tên>` chỉ người dùng gọi được: đề xuất người dùng gõ; skill không có `/` thì gọi bằng Skill tool.

## Mode

**lite** khi đủ cả ba: ≤ 3 acceptance criteria, không thêm model hay migration, không thêm endpoint. Ngược lại **full**. Phase 1 đề xuất, G1 chốt. Lite: một slice, phiên chính tự code và sửa, grilling chỉ hỏi phần còn mở, review một agent cho cả ba trục.

## Sub-agent

Phiên chính điều phối và giữ gate, tài liệu, ship, done, retro. Sub-agent là `general-purpose`, không đặt `model`:

| Việc | Full | Lite |
| --- | --- | --- |
| Phase 1, bản đồ code | `Explore`; phiên chính lưu kết quả vào `<K>-map.md` | như full |
| Phase 2, mọi slice | **một** *implementer* làm hết slice theo DAG | phiên chính |
| Phase 4, review | `code-review` (Spec + Standards) song song một agent Bug | một agent cả ba trục |
| Phase 4 vòng sửa, phase 6 CI đỏ | *implementer* của phase 2 | phiên chính |

- **Prompt là địa chỉ**: `<T>`, việc (slice / vòng sửa / log CI), mode và đường dẫn cần đọc theo thứ tự `S/reference/sub-agent.md`, `S/reference/rules.md`, file phase, `.git/ship-ticket-fashion/<K>-map.md`, thư mục ticket. Nội dung file để agent tự đọc.
- **Báo là gọi**: tin nhắn báo giao việc chứa luôn lệnh gọi `Agent`.
- **Giữ implementer**: lưu id agent. Câu trả lời *Cần người dùng*, vòng sửa, CI đỏ gửi cho nó bằng `SendMessage` (nạp bằng `ToolSearch "select:SendMessage"`). `ListAgents` không còn agent đó → tạo mới với cùng prompt địa chỉ; agent mới đọc `handoff` trong state, commit và `<K>-map.md` rồi làm tiếp.
- Phiên chính tin kết quả trả về và state, không đọc lại file sub-agent đã đọc.

## Gate

*Gate* (G1, G2) là quyết định của người dùng; script xanh / đỏ chỉ là *check*.

1. **Tóm tắt**: bảng gọn các mục phase liệt kê, mỗi điểm mở kèm khuyến nghị.
2. **Hỏi**: `AskUserQuestion` chỉ chứa điểm cần trả lời; ≤ 4 câu mỗi lần, 2–4 lựa chọn, lựa chọn khuyên dùng đứng đầu kèm "(khuyên dùng)". Gom điểm liên quan vào một câu.

Gate xong khi mọi điểm mở có câu trả lời đã ghi vào ticket hoặc state.

## State, ticket, commit

- Schema state: `reference/state.md`; ghi field bằng `state.py set` / `push`. Đổi phase chỉ bằng `python3 S/scripts/state.py transition <T> --to <phase> --next "<một việc cụ thể>" --reason "<tiêu chí đã đạt / gate>" [--gate g1|g2]`; script từ chối chuyển sai thứ tự hoặc thiếu gate.
- Ticket là thư mục `.scratch/<feature>/issues/NN-<slug>/`: `spec.md` (phase 1 thêm `## Quyết định`), `plan.md` (sinh bằng `plan.py`), `report.md` (phase 3 viết, phase 4 và 5 ghi đè).
- Một *task* là đúng một commit, qua `python3 S/scripts/commit.py <T> --task <task> -m "<subject>" [--body "…"] -- <file>…` (gắn trailer `Refs:`, `Task:`; hook sửa file thì tự add lại). Task và subject: `templates/commit-msg.md`. `commit_map.py <T> [--md]` in commit → task → AC.

**Điểm clear** (phase chỉ ra chỗ): in `Đã lưu state (<phase>/<slice>). Có thể /clear rồi chạy lại /ship-ticket-fashion <T> để tiếp tục.`, rồi làm tiếp trừ khi người dùng ngắt. Còn ngữ cảnh chưa ghi vào state hay ticket (grilling dở) thì thêm: `Cần mang ngữ cảnh đó sang phiên mới thì gõ /mattpocock-skills:handoff <T> <phase>.`
