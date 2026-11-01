---
name: ship-ticket-fashion
description: Làm một ticket `.scratch/<feature>/issues/NN-*/` của Fashion Store từ grilling tới merge, kèm retro skill; tạo spec và ticket cho module chưa có ticket; retro một PR. Dùng khi người dùng nói "làm ticket NN", "làm tiếp", "làm module X", "retro PR #N", hoặc hỏi tiến độ / ticket tiếp theo.
argument-hint: "[<feature>/<NN> | <NN> | <module>] [grill|code|report|review|sync|ship|done|retro] | retro #<PR>"
---

# ship-ticket-fashion

Mọi tin nhắn cho người dùng viết tiếng Việt. Mỗi lần chạy đưa **một** ticket qua một vòng khép kín; dừng chỉ ở gate, ở *Cần người dùng*, hoặc khi xong.

`S` = `.claude/skills/ship-ticket-fashion` (đường dẫn tính từ gốc repo). `<T>` = ticket ở dạng `<feature>/<NN>`, ví dụ `backend-bootstrap/16`.

## Đầu mỗi lần chạy

1. `python S/scripts/state.py start [<T>]`, chạy riêng. Tham số là tên module hoặc mốc (`catalog`, `M1`) chưa có ticket trong `.scratch/` → `phases/0-plan.md`. Script in ticket, phase, `next`, slice, gate, các cờ (`BRANCH RED`, `DIRTY`, `BEHIND`, `SLICE OPEN`, `NO HOOKS`) và các dòng `READ <file>`. Output này thay cho việc đọc file state.
   - `NO STATE` kèm frontier → chưa có ticket đang làm: báo tiến độ (`python S/scripts/progress.py`), hỏi người dùng chọn ticket (khuyên dùng theo thứ tự ưu tiên mới nhất trong *Decisions-so-far* của `.scratch/mvp-roadmap/map.md`; chưa có thì đề xuất thứ tự, lỗi thật trước rồi tới cổng chặn CI, và ghi vào đó khi người dùng duyệt), rồi vào phase 1. Có ticket `needs-triage` → cùng lần hỏi, hỏi từng ticket: `ready-for-agent`, `ready-for-human`, `wontfix` hay để sau (`docs/agents/triage-labels.md`); ghi dòng `Status:` theo câu trả lời và commit cùng ticket ở phase 1 bước 9. Một package đã có từ 3 ticket trở lên sửa (`git log --oneline origin/dev -- <package>`) và frontier còn ticket ở đó → cùng lần hỏi, đề xuất theo `phases/0-plan.md` mục *Điểm nóng*. Frontier rỗng, hoặc mốc chỉ còn ticket bị chặn hay cần người → `phases/0-plan.md`.
   - `retro #<PR>` → bỏ qua state, làm `phases/8-retro.md` mục *Retro một PR*.
2. Đọc mọi file sau `READ` bằng Read tool, mỗi file một lần gọi.
3. Bắt đầu từ `next`. Tham số `[phase]` ghi đè phase, trừ khi gate chưa được duyệt.

## Vòng

```
0 plan (khi frontier rỗng)
1 grill → ⛔G1 → 2 code (S1 → S2 → …) → 3 report → 4 review → 5 sync → ⛔G2 → 6 ship → 7 done → 8 retro
                    ↑                                  │          │
                    └──── review / sync đổi hành vi ───┴──────────┘
```

| # | Phase | File | Skill (`mattpocock-skills:`) | Kết quả |
| --- | --- | --- | --- | --- |
| 0 | plan | `phases/0-plan.md` | `grilling`; người dùng gõ `to-spec`, `to-tickets`, `improve-codebase-architecture` (điểm nóng) | spec + ticket của mốc mới |
| 1 | grill | `phases/1-grill.md` | `grilling`; `codebase-design` khi ticket có interface public | nhánh, *spec* + *plan* đã commit, ⛔G1 |
| 2 | code | `phases/2-code.md` | `tdd` | mọi slice xanh, mỗi slice một commit |
| 3 | report | `phases/3-report.md` | — | `report.md` (commit ở sync) |
| 4 | review | `phases/4-review.md` | `code-review`; `code-review` dựng sẵn (trục Bug) | mọi finding có kết luận |
| 5 | sync | `phases/5-sync.md` | `domain-modeling` khi có thuật ngữ / ADR mới | tài liệu khớp code, ⛔G2 |
| 6 | ship | `phases/6-ship.md` | — | PR mở, ticket đóng trong PR, CI xanh |
| 7 | done | `phases/7-done.md` | — | merge khi người dùng bảo |
| 8 | retro | `phases/8-retro.md` | `writing-for-agents` | skill tốt hơn, PR của skill |

Quy tắc chung cho mọi phase: `reference/rules.md`.

## Spec, plan, report

Ticket là thư mục `.scratch/<feature>/issues/NN-<slug>/` (`docs/agents/issue-tracker.md`); mỗi phần một file:

| Phần | File | Viết ở | Trả lời |
| --- | --- | --- | --- |
| *spec* | `spec.md`: `## Quyết định` + `## Acceptance criteria` (cùng `Status:`, `**PR:**`) | phase 1 | làm gì, theo tài liệu nào |
| *plan* | `plan.md`, sinh bằng `plan.py` từ slice trong state | phase 1 | làm theo thứ tự nào, test nào chứng minh, commit nào |
| *report* | `report.md` | phase 3, ghi đè ở 4 và 5 | đã làm, chưa làm, gap, commit → task |

Code chỉ bắt đầu khi *spec* và *plan* đã commit: `state.py transition --to code` kiểm cả hai.

## Commit

Một *task* là đúng một commit: `plan`, mỗi slice `S<n>`, mỗi vòng sửa review `R1` / `R2`, `sync` (tài liệu + report), `close`; thêm `ci` cho mỗi lần CI đỏ. PR squash vào `dev`, nên commit trên nhánh là dấu vết để đọc, không phải lịch sử lâu dài; mỗi commit thêm còn chạy lại hook `mypy` + `lint-imports`.

- Commit qua `python S/scripts/commit.py <T> --task <task> -m "<subject>" [--body "…"] -- <file>…`: gắn trailer `Refs:` (ticket) và `Task:`, hook chạy trong log, hook sửa file thì tự add lại.
- `python S/scripts/commit_map.py <T> [--md]` in commit → task → phase → AC; báo commit thiếu trailer và task có hai commit. Bảng `--md` đi vào report, thân PR và thân commit squash.

## Mode

**lite** khi đủ cả ba: ticket có ≤ 3 acceptance criteria, không thêm model hay migration, không thêm endpoint. Ngược lại là **full**. Phase 1 đề xuất mode, G1 chốt. Lite: một slice, làm ngay trong phiên chính, grilling chỉ hỏi phần còn mở.

## State

State nằm ở `.git/ship-ticket-fashion/<feature>-<NN>.json`: trong `.git/` nên không bao giờ bị commit, và vẫn còn sau `/clear`. Schema: `reference/state.md`. File là bộ nhớ; context của phiên chỉ là tạm.

Ghi field bằng `state.py set` / `push`. Đổi phase chỉ qua:

```bash
python S/scripts/state.py transition <T> --to <phase> --next "<một việc cụ thể>" --reason "<tiêu chí đã đạt / gate>" [--gate g1|g2]
```

Script từ chối nhảy cóc phase, vào `code` khi chưa có G1, vào `ship` khi chưa có G2, vào `report` khi còn slice chưa xong.

**Điểm clear** (các file phase chỉ ra chỗ): sau khi state và ticket đã giữ mọi quyết định, in `Đã lưu state (<phase>/<slice>). Có thể /clear rồi chạy lại /ship-ticket-fashion <T> để tiếp tục.`, rồi làm tiếp trừ khi người dùng ngắt.

## Gate

*Gate* là quyết định của người dùng (G1, G2); script xanh / đỏ là *check*. Mỗi gate gồm:

1. **Tin tóm tắt**: mọi mục phase liệt kê cho gate, viết thành bảng gọn, mỗi điểm mở kèm khuyến nghị.
2. **Quyết định**: `AskUserQuestion` chỉ chứa điểm cần trả lời (≤ 4 câu mỗi lần gọi, 2–4 lựa chọn, lựa chọn khuyên dùng đứng đầu, ghi "(khuyên dùng)"). Gom các điểm liên quan vào một câu; nhiều hơn 4 thì gọi lần hai.

Gate xong khi mọi điểm mở có câu trả lời và đã ghi vào ticket hoặc state.

*Cần người dùng* (quyết định ngoài gate) định nghĩa ở `reference/rules.md`.

## Sub-agent

Phiên chính điều phối. Việc đọc nhiều file hoặc chạy nhiều lượt giao cho sub-agent (`general-purpose`, không đặt `model`):

| Ở đâu | Sub-agent | Lite |
| --- | --- | --- |
| Phase 1, bản đồ code (`Explore`) | một | như full |
| Phase 2, mỗi slice | một cho mỗi slice | phiên chính |
| Phase 4, ba trục review | do skill review tạo | như full |
| Phase 4, vòng sửa khi finding đổi code | một cho mọi vòng | như full |

Gate, tài liệu, ship, done, retro chạy ở phiên chính: retro cần thấy những gì phiên này đã vấp.

- **Báo là gọi**: tin nhắn báo giao việc cho sub-agent chứa luôn lệnh gọi `Agent`.
- **Prompt = địa chỉ**: `<T>`, slice id, mode và các đường dẫn cần đọc: `S/reference/sub-agent.md` trước, rồi `S/reference/rules.md`, file phase, file `gotchas/` phase đó nêu, ticket.
- **Làm tiếp, không tạo lại**: câu trả lời cho *Cần người dùng*, vòng sửa tiếp theo, chạy lại đều gửi cho cùng agent bằng `SendMessage` (nạp bằng `ToolSearch "select:SendMessage"`).
- Phiên chính đọc kết quả trả về và state, tin phần sub-agent đã đọc.
