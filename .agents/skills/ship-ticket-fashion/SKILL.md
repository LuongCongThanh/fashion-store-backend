---
name: ship-ticket-fashion
description: Làm ticket Fashion Store trong .scratch/ từ chốt spec tới merge, retro mỗi đợt 10 ticket; lập spec và ticket cho module mới; retro PR theo yêu cầu. Dùng khi người dùng yêu cầu làm ticket, làm tiếp module, xem tiến độ ticket hoặc retro PR trong repo này.
---

# ship-ticket-fashion cho Codex

Đọc [workflow dùng chung](../../../.claude/skills/ship-ticket-fashion/SKILL.md) và áp dụng các điều chỉnh Codex dưới đây khi workflow nhắc tới công cụ hoặc skill của Claude Code. Các điều chỉnh này chỉ thay cách thực hiện trong Codex; giữ nguyên phase, acceptance criteria, commit theo task và gate của workflow.

`S` luôn là `.claude/skills/ship-ticket-fashion`, tính từ gốc repo. Script, phase, template, gotcha và schema state dùng chung ở đó; không copy sang `.agents/`. Vì vậy `state.py` tiếp tục in đường dẫn `READ` đúng mà không cần đổi hằng `SKILL`. Trong các lệnh mẫu, thay `S` bằng đường dẫn thật; `S` không phải biến shell đã được khai báo.

Trước khi làm ticket, đọc `CLAUDE.md` (quy ước dự án) và `GLOSSARY.md`. Tài liệu viết tiếng Việt; code, tên nhánh, commit và tiêu đề PR dùng tiếng Anh. Không đọc nội dung `.env*` (trừ `.env.example`), `.secrets/`, `*.pem`, hoặc in token. Rule trong `.claude/settings.json` chỉ dành cho Claude Code, không tự trở thành quyền truy cập của Codex.

## Bắt đầu và làm tiếp

- Ticket, module hoặc tiến độ: chạy riêng `python3 .claude/skills/ship-ticket-fashion/scripts/state.py start [<T>]`, rồi đọc các file `READ` và làm theo `next`. State dùng chung với Claude; chỉ một phiên sở hữu ticket tại một thời điểm. Có dấu hiệu phiên khác đang làm cùng ticket thì xác minh với người dùng trước khi sửa state hoặc file của ticket.
- `retro #<PR>`: bỏ qua `start`, đọc `S/phases/8-retro.md` và dùng nguồn bằng chứng Codex ở phần Retro bên dưới.
- Sau khi lưu state và quyết định, thay thông báo `/clear` bằng: `Đã lưu state (<phase>/<slice>). Có thể mở phiên mới rồi gọi $ship-ticket-fashion <T> để tiếp tục.` Phiên mới đọc lại state, không giả định agent cũ còn tồn tại.

## Công cụ và gate

| Trong workflow Claude | Thực hiện trong Codex |
| --- | --- |
| `Read`, `Bash`, `grep` | Đọc file bằng công cụ filesystem hoặc `Get-Content -LiteralPath`; chạy lệnh bằng công cụ shell; tìm bằng `rg`. |
| `AskUserQuestion` | Dùng công cụ hỏi người dùng có sẵn trong phiên. Nếu không có, hỏi trong tin nhắn rồi dừng phần phụ thuộc câu trả lời. |
| `Agent`, `Explore`, `general-purpose` | Dùng công cụ tạo sub-agent có sẵn; ghi vai trò Explore trong prompt, không giả định có loại agent cùng tên. Không đặt model. |
| `SendMessage`, `ListAgents`, `ToolSearch` | Dùng công cụ gửi việc, xem agent và khám phá công cụ tương ứng đang có. Không gọi tên công cụ Claude theo nghĩa đen. |

G1, G2, chọn finding để sửa, chọn cải tiến retro và quyết định merge vẫn cần câu trả lời thực của người dùng. Giữ nguyên phạm vi đã được duyệt; câu trả lời trong phiên trước vẫn có giá trị khi state và ticket đã lưu. Check xanh hoặc một lựa chọn được đánh dấu khuyên dùng không phải duyệt gate. Chỉ chạy `transition --gate g1|g2` sau khi người dùng duyệt. G2 cho phép push và mở PR như phase 5 quy định; merge cần chỉ thị riêng của người dùng.

Điều chỉnh số câu và lựa chọn theo giới hạn công cụ trong phiên. Với multi-select không được hỗ trợ, đánh số các finding hoặc đề xuất và hỏi người dùng chọn mã; không tự chọn thay họ.

## Sub-agent

Khi phiên có công cụ và cho phép delegation, áp dụng bảng phân việc của workflow dùng chung. Mỗi agent đọc file này trước `S/reference/sub-agent.md`, `S/reference/rules.md`, phase, gotcha và ticket; truyền `<T>`, slice, mode và phạm vi file rõ ràng. Slice phụ thuộc nhau chạy tuần tự. Một agent giữ việc qua các vòng sửa khi nó còn tồn tại; trả lời cần kích hoạt agent đang chờ thì dùng công cụ giao việc tiếp.

Nếu phiên không hỗ trợ hoặc không cho phép sub-agent, phiên chính thực hiện các vai trò lần lượt, vẫn ghi state và báo cáo như hợp đồng sub-agent. Nêu rõ review do cùng một agent thực hiện. Khi resume có `SLICE OPEN`, kiểm tra agent còn sống nếu có công cụ; agent đã mất thì đọc handoff, diff, commit và trạng thái test trước khi nhận lại slice.

## Skill phụ thuộc

Chỉ gọi skill thực sự có trong danh sách của phiên; tên `mattpocock-skills:*` là tham chiếu Claude, không phải dependency tự được cài vào Codex. Nếu có skill tương ứng thì đọc hướng dẫn của nó. Khi thiếu, thực hiện trực tiếp kết quả yêu cầu bên dưới, không bỏ phase hoặc yêu cầu người dùng gõ slash command Claude.

| Skill được nhắc tới | Kết quả cần thực hiện khi thiếu |
| --- | --- |
| `grilling` | Đọc code và tài liệu, tìm quyết định còn mở trong phạm vi ticket, trình phương án và khuyến nghị, chốt câu trả lời vào `## Quyết định`. |
| `to-spec`, `to-tickets` (người dùng gọi) | Tự viết spec theo `S/phases/0-plan.md` và mẫu `.scratch/backend-bootstrap/spec.md`; tạo ticket theo khung của phase 0, có AC kiểm chứng được và quan hệ chặn. Chốt phạm vi còn mở với người dùng trước khi viết. |
| `codebase-design` | Chốt interface và seam trong spec; đánh giá phần phức tạp được che giấu và điều gì mất nếu xoá abstraction (deletion test). Một seam chỉ có một adapter phải có lý do. Interface `contracts.py` đầu tiên so sánh tối đa ba phương án ở G1. |
| `tdd` | Làm từng vòng test red đúng lỗi hành vi → code tối thiểu để green → refactor; test tại seam và theo AC như phase 2. |
| `mattpocock-skills:code-review` + sub-agent trục Bug | Thực hiện đủ ba trục Spec, Standards, Bug theo `S/phases/4-review.md`, cùng mốc `origin/dev`. Spec kiểm từng AC và chất lượng assertion; Standards đối chiếu tài liệu chi phối; Bug soi diff và code liên quan để tìm lỗi hành vi. Mỗi finding có mã, `file:line`, bằng chứng và kết luận. |
| `domain-modeling` | Đọc `docs/agents/domain.md`, cập nhật `GLOSSARY.md` cho thuật ngữ mới và ADR cho quyết định kiến trúc lâu dài, đối chiếu tên trong code. |
| `improve-codebase-architecture` (người dùng gọi) | Khảo sát khu vực nóng và các caller, chỉ ra vấn đề bằng code cụ thể, đề xuất phạm vi cải thiện và đánh đổi. Người dùng chọn trước khi tạo ticket `needs-triage` theo phase 0. |
| `research` | Tra tài liệu gốc (docs chính thức, source của thư viện đúng phiên bản trong `backend/uv.lock`), ghi kết quả có trích nguồn vào `.scratch/<feature>/research/<chủ-đề>.md`. |
| `diagnosing-bugs` | Dựng một lệnh đỏ đúng lỗi (test, script) và chạy được trước, rồi mới đặt giả thuyết và sửa; không dựng được thì báo rõ đã thử gì. |
| `pr` | Giữ khung `.github/pull_request_template.md`; *Giải pháp* dùng pseudocode / call tree nhỏ nhất, *Cách kiểm* ghi Before/After, *Reviewer cần chú ý* ghi Door và Blast Radius. |
| `triage`, `retro`, `handoff` (người dùng gọi) | Bỏ đề xuất gõ lệnh: triage hỏi trực tiếp như phase 1; retro dùng nguồn bằng chứng ở mục Retro; handoff thay bằng state + thông báo mở phiên mới. |
| `writing-for-agents` | Ghi đúng cải tiến retro đã chọn: mỗi ý một chỗ, chỉ dẫn hành động cụ thể; bỏ dòng trùng hoặc lỗi thời. Giữ quy tắc và ví dụ theo cùng một nguồn. |

## Shell và GitHub

Shell mặc định của phiên này có thể là PowerShell. Lệnh `GH_TOKEN="$(gh auth token --user LuongCongThanh)" gh …` trong phase 6–8 là cú pháp Bash: chỉ dùng nguyên mẫu khi công cụ shell chạy Bash. Với PowerShell, lấy token vào biến môi trường cho tiến trình `gh`, giữ token ngoài output và khôi phục biến môi trường cũ bằng `try/finally`. Không đổi tài khoản GitHub mặc định toàn máy.

Giữ token trong môi trường tiến trình, không nội suy vào chuỗi lệnh hoặc ghi vào file. Thân PR và squash commit ghi bằng UTF-8 rồi truyền `--body-file`/`-F` theo hướng dẫn phase. Dùng các công cụ shell hiện có, không yêu cầu `Bash tool` riêng. Giữ `run_logged.py` cho các lệnh kiểm tra dài và đọc `S/gotchas/windows-shell.md` khi gặp lỗi shell.

## Retro

Thời điểm retro và cách đếm theo `S/phases/7-done.md`; chỉ đọc `S/phases/8-retro.md` khi đủ đợt hoặc người dùng yêu cầu `retro #<PR>`. Ghi chú mỗi ticket theo template báo cáo, checkpoint dùng chung giữa Claude và Codex.

`S/scripts/user_prompts.py` chỉ đọc transcript Claude. Trong Codex, bỏ lệnh này ở cả retro ticket và retro PR; không lấy lịch sử Claude làm bằng chứng cho phiên Codex và không quét thư mục phiên người dùng khác.

Dùng `report.md` và mục *Ghi chú cho retro* của từng ticket trong đợt, spec, plan, commit → task và review/CI của PR. Hội thoại, state/handoff và log kiểm tra còn giữ được là bằng chứng bổ sung. Sau khi đổi phiên, nếu không có nguyên văn lời nhắc thì chỉ kết luận từ bằng chứng còn lưu và nêu phần không xác minh được. Không suy diễn câu người dùng đã nói.

Cải tiến quy trình chung ghi ở `S`; điều chỉnh chỉ dành cho Codex ghi ở file này. Thay đổi trong `.agents/skills/` cũng là thay đổi skill khi áp dụng phase 8; chỉ thay hook hoặc cấu hình backend mới kéo theo check backend tương ứng. Sửa script thì chạy suite unittest dùng chung. Luôn `git diff --check`; giữ bước người dùng chọn đề xuất trước khi sửa và quy trình PR retro của phase 8.

Chỉ ghi memory khi người dùng yêu cầu trực tiếp, theo quyền và cơ chế memory của phiên Codex.
