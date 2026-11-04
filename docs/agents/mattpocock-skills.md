# Plugin mattpocock-skills: skill nào dùng khi nào

Bảng chọn skill của plugin `mattpocock-skills` (bản 1.3.1) cho Fashion Store, kèm các lưu ý riêng của repo. Chi tiết từng skill (các bước, đầu ra) đọc trong `SKILL.md` gốc: `~/.claude/plugins/cache/claude-plugins-official/mattpocock-skills/1.3.1/` hoặc <https://github.com/mattpocock/skills>.

## 1. Cách gọi

- **Model-invoked**: agent tự gọi khi việc khớp mô tả, hoặc bạn gõ `/mattpocock-skills:<tên>`.
- **User-invoked**: chỉ chạy khi bạn gõ tay. Agent không tự gọi được.
- Claude Code có sẵn `/code-review` (tìm bug trong diff), khác `/mattpocock-skills:code-review` (đối chiếu Standards và Spec). Gõ đủ tiền tố khi muốn dùng skill của plugin.

## 2. Cấu hình repo

Repo đã cấu hình tương đương `setup-matt-pocock-skills`: [`issue-tracker.md`](./issue-tracker.md), [`triage-labels.md`](./triage-labels.md), [`domain.md`](./domain.md) và khối `## Agent skills` trong `CLAUDE.md`. Có hai chỗ repo khác mặc định của plugin:

- Ticket là **thư mục** `.scratch/<feature>/issues/<NN>-<slug>/spec.md`, không phải một file `<NN>-<slug>.md`. `issue-tracker.md` đã ghi đè quy ước này.
- Mô tả PR bắt buộc theo `.github/pull_request_template.md` ([`11-git-workflow.md`](../architecture/11-git-workflow.md) mục 4.2). Skill `pr` không đọc template này.

## 3. Engineering

| Skill | Gọi | Dùng khi | Lưu ý riêng cho repo |
| --- | --- | --- | --- |
| `tdd` | model | Làm tính năng hoặc sửa bug theo kiểu test trước | Đưa kèm `spec.md` của feature để skill khỏi làm lấn sang ticket khác |
| `diagnosing-bugs` | model | Bug khó, bug chập chờn, hồi quy hiệu năng | Skill sửa luôn mà không hỏi; muốn duyệt trước khi sửa thì nói rõ lúc gọi |
| `code-review` | model | Review nhánh hoặc PR từ một mốc (thường là `origin/dev`) | Chỉ xem `<mốc>...HEAD`, nên phải commit trước. Chạy ở phiên mới. Coi phát hiện là giả thuyết |
| `codebase-design` | model | Bàn interface, seam, deep module | Ở repo, "module" là module nghiệp vụ, mỗi module một Django app (ADR 0018). Khi bàn, gọi cụ thể là hàm, class hay package |
| `domain-modeling` | model | Mài thuật ngữ, sửa `GLOSSARY.md`, ghi ADR | Chỉ ghi ADR khi quyết định khó đảo ngược, gây bất ngờ nếu thiếu ngữ cảnh, và có trade-off thật |
| `prototype` | model | Kiểm một state model hoặc logic trước khi code thật | Repo là backend, nên dùng nhánh logic (HTML). Commit lên nhánh `prototype/<tên>`, không merge |
| `research` | model | Cần sự thật từ nguồn ngoài repo (GHN, VNPay, MoMo, thư viện) | Lưu ở `.scratch/<feature>/research/`, rồi trỏ ticket hoặc spec tới file đó |
| `pr` | model | Viết mô tả PR | Đặt Summary, Evidence, Merge Danger **bên trong** template của repo |
| `wizard` | model | Bước chỉ người làm được (secret, dashboard bên thứ ba) | Skill bảo đọc `.env`, nhưng repo cấm. Chỉ cho đọc `.env.example`, `docker-compose.yml`, `.github/workflows/` |
| `ask-matt` | user | Không biết nên dùng skill nào | |
| `grill-with-docs` | user | Bắt đầu một thay đổi: grilling + `domain-modeling` | |
| `to-spec` | user | Biến buổi grilling thành `.scratch/<feature>/spec.md` | Chạy trong cùng phiên với buổi grilling |
| `to-tickets` | user | Chia spec thành các ticket lát dọc | Ticket sinh ra đã ở `ready-for-agent`, không cần `triage` |
| `implement` | user | Làm một ticket | Với ticket trong `.scratch/`, dùng `ship-ticket-fashion` (mục 6) |
| `implement-spec` | user | Làm cả spec song song trên một integration branch | Lệch quy ước của repo (mỗi ticket một PR, khoảng 400 dòng). Không dùng |
| `triage` | user | Ticket thô ở `needs-triage` không do `to-tickets` tạo | Repo chưa có `.out-of-scope/`. Việc ngoài phạm vi ghi vào `.scratch/backlog.md` |
| `improve-codebase-architecture` | user | Quét tìm chỗ nên deepening | Báo cáo HTML nằm ngoài repo |
| `wayfinder` | user | Việc quá lớn, mù mờ, cần chia thành các ticket quyết định | Map ở `.scratch/<effort>/map.md`. Việc đã rõ phạm vi thì dùng `grill-with-docs` |
| `retro` | user | Sau phiên code, cải thiện môi trường làm việc của agent | Phiên gắn ticket thì dùng retro của `ship-ticket-fashion` |
| `setup-matt-pocock-skills` | user | Cấu hình repo cho plugin | Đã chạy rồi. Nếu chạy lại, đọc kỹ bản nháp để giữ phần tuỳ biến tiếng Việt |

## 4. Productivity

| Skill | Gọi | Dùng khi | Lưu ý riêng cho repo |
| --- | --- | --- | --- |
| `grilling` | model | Chất vấn một kế hoạch tới khi hai bên hiểu như nhau | Không ghi file; muốn ghi thì dùng `grill-with-docs` |
| `writing-for-agents` | model | Sửa skill, `CLAUDE.md`, tài liệu cho agent | |
| `grill-me` | user | Grilling ngoài repo | Trong repo, dùng `grill-with-docs` |
| `handoff` | user | Chuyển việc sang phiên khác | Cú pháp: `handoff <ticket> <phase>`. File nằm trong thư mục tạm của hệ thống, có thể mất khi khởi động lại máy |
| `teach` | user | Học một khái niệm qua nhiều phiên | Skill tạo file ngay tại chỗ, đừng chạy ở gốc repo |
| `to-questionnaire` | user | Cần người khác trả lời để ra quyết định (pháp chế, kế toán) | |
| `wait-what` | user | Agent vừa nói điều khó hiểu | |

Các nhóm `in-progress/` (beta), `misc/` (đóng băng) và `deprecated/` (đang rỗng) không có trong plugin, không dùng ở repo này. Hai skill trong `misc/` thừa với repo: repo dùng framework `pre-commit` chứ không dùng Husky, và đã có hook git riêng (`guard_merge_target.py`, `permissions.deny`).

## 5. Luồng làm việc

```text
grill-with-docs ──(cần chạy thử? prototype · cần sự thật ngoài? research)
   ▼
nhiều phiên? ── có ──▶ to-spec ──▶ to-tickets ──▶ ship-ticket-fashion (mỗi ticket)
   └── không ──▶ tdd ──▶ code-review ──▶ pr ──▶ retro
```

Giữ grilling, `to-spec` và `to-tickets` trong **một** phiên liên tục. Mỗi ticket bắt đầu một phiên mới.

| Tình huống | Skill |
| --- | --- |
| Làm ticket `.scratch/` từ đầu tới merge | `/ship-ticket-fashion` |
| Lên mốc mới khi chưa có ticket | `/ship-ticket-fashion <module>` (nó nhắc gõ `to-spec`/`to-tickets` đúng lúc) |
| Chất vấn ý tưởng trước khi làm | `grill-with-docs` |
| Bug, test đỏ, chạy chậm | `diagnosing-bugs` |
| Review theo spec và chuẩn code | `/mattpocock-skills:code-review` |
| Tìm bug runtime trong diff | `/code-review` có sẵn |
| Seam, interface "nông" | `codebase-design` |
| Thuật ngữ bị dùng hai nghĩa, cần ADR | `domain-modeling` |
| Kiểm state machine (Đơn hàng, Giữ hàng) | `prototype` |
| Tra API hoặc thư viện bên ngoài | `research` |
| Ticket `needs-triage` | `triage` |
| Việc khổng lồ, mù mờ | `wayfinder` |
| Cần người làm bước thủ công | `wizard` |

## 6. Với `ship-ticket-fashion`

[`ship-ticket-fashion`](../../.claude/skills/ship-ticket-fashion/SKILL.md) tự gọi `grilling`, `codebase-design`, `tdd`, `diagnosing-bugs`, `code-review`, `domain-modeling` và `retro` ở đúng phase, rồi bổ sung phần riêng của repo: ghi state, lưu bằng chứng `tdd.py`, mỗi task một commit, hai cổng G1/G2, PR theo template.

- **Ticket trong `.scratch/`**: luôn dùng `/ship-ticket-fashion <feature>/<NN>`. Không chạy `implement`/`implement-spec` cho cùng ticket, vì hai skill này bỏ qua state, bằng chứng red/green và cách đóng ticket của repo.
- **Việc không gắn ticket** (thử ý tưởng, debug nhanh, review nhánh khác, tra tài liệu): gọi thẳng skill của plugin.
