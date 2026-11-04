# Plugin mattpocock-skills: skill nào dùng khi nào

Tài liệu này giải thích từng skill của plugin `mattpocock-skills` (bản 1.3.1): mục đích, khi nào dùng, skill làm gì, đầu ra, và ví dụ áp dụng cho Fashion Store. Nội dung lấy từ `SKILL.md`, `README.md`, `SCOPE.md` và `docs/` của plugin; chỗ nào nguồn không nói rõ thì ghi **chưa rõ**.

Nguồn đã cài trên máy: `~/.claude/plugins/cache/claude-plugins-official/mattpocock-skills/1.3.1/`. Bản gốc: <https://github.com/mattpocock/skills>.

## Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Cấu hình của repo cho plugin](#2-cấu-hình-của-repo-cho-plugin)
3. [Nhóm Engineering](#3-nhóm-engineering)
4. [Nhóm Productivity](#4-nhóm-productivity)
5. [Nhóm in-progress (beta, chưa ổn định)](#5-nhóm-in-progress-beta-chưa-ổn-định)
6. [Nhóm misc (đóng băng)](#6-nhóm-misc-đóng-băng)
7. [Nhóm deprecated](#7-nhóm-deprecated)
8. [Luồng làm việc nối các skill](#8-luồng-làm-việc-nối-các-skill)
9. [Bảng tra nhanh: tình huống → skill](#9-bảng-tra-nhanh-tình-huống--skill)
10. [Chồng chéo với `ship-ticket-fashion`](#10-chồng-chéo-với-ship-ticket-fashion)

## 1. Tổng quan

### Hai cách gọi skill

Plugin chia skill theo **ai được gọi**:

- **Model-invoked**: agent tự gọi khi việc đang làm khớp mô tả của skill, hoặc bạn gõ `/mattpocock-skills:<tên>`. Đây là nơi chứa "kỷ luật" dùng lại được (TDD, review, thuật ngữ...).
- **User-invoked**: chỉ chạy khi bạn gõ `/mattpocock-skills:<tên>` (frontmatter có `disable-model-invocation: true`). Việc của chúng là điều phối; một skill user-invoked có thể gọi skill model-invoked nhưng không gọi skill user-invoked khác.

Cài qua plugin marketplace thì mọi skill có tiền tố `mattpocock-skills:`. Lưu ý: Claude Code có sẵn một skill `/code-review` (tìm bug trong diff), khác với `/mattpocock-skills:code-review` (đối chiếu Standards và Spec). Gõ đúng tên có tiền tố khi muốn dùng skill của plugin.

### Skill đang bật trong Claude Code

11 skill model-invoked dưới đây đang bật, agent có thể tự gọi. Trong tài liệu, các skill này được đánh dấu **[đang bật]**.

| Skill | Nhóm | Một dòng |
| --- | --- | --- |
| `codebase-design` | Engineering | Bộ từ vựng thiết kế deep module: interface nhỏ, seam sạch |
| `code-review` | Engineering | Review diff theo hai trục Standards và Spec, chạy song song |
| `diagnosing-bugs` | Engineering | Vòng chẩn đoán bug khó: dựng feedback loop đỏ trước khi đoán |
| `domain-modeling` | Engineering | Mài thuật ngữ, cập nhật `GLOSSARY.md` và ADR ngay khi chốt |
| `pr` | Engineering | Khuôn mô tả PR: Summary trực quan, Evidence, Merge Danger |
| `prototype` | Engineering | Code thử để trả lời một câu hỏi thiết kế |
| `research` | Engineering | Agent nền đọc nguồn gốc, ghi kết quả có trích dẫn ra file |
| `tdd` | Engineering | Vòng red → green theo từng lát dọc, tại seam đã thống nhất |
| `wizard` | Engineering | Sinh script bash dẫn người làm các bước chỉ người làm được |
| `grilling` | Productivity | Phỏng vấn tới khi mọi nhánh của cây quyết định được giải quyết |
| `writing-for-agents` | Productivity | Hướng dẫn viết tài liệu cho agent: skill, `CLAUDE.md` |

Các skill user-invoked của plugin (ví dụ `to-spec`, `to-tickets`, `triage`, `handoff`) nằm trong `plugin.json` nhưng agent không tự gọi được; bạn gõ tay khi cần. Skill dự án `ship-ticket-fashion` cũng làm vậy: nó nhắc bạn gõ `/mattpocock-skills:to-spec` thay vì tự gọi.

### Các nhóm trong plugin

| Nhóm | Có trong plugin? | Trạng thái |
| --- | --- | --- |
| `engineering/` | Có | Dùng hằng ngày cho việc code |
| `productivity/` | Có | Công cụ làm việc chung, không riêng code |
| `in-progress/` | Không | Beta, có thể đổi hoặc biến mất không báo trước |
| `misc/` | Không | Đóng băng, không còn bảo trì |
| `deprecated/` | Không | Đang rỗng |

## 2. Cấu hình của repo cho plugin

Repo đã chạy bước tương đương `/mattpocock-skills:setup-matt-pocock-skills`. Các skill engineering đọc cấu hình từ:

- [`issue-tracker.md`](./issue-tracker.md): tracker là Markdown trong `.scratch/<feature-slug>/`; mỗi ticket là thư mục `issues/<NN>-<slug>/` có `spec.md`, `plan.md`, `report.md`. Có thêm mục *Wayfinding* cho `/wayfinder`.
- [`triage-labels.md`](./triage-labels.md): 5 trạng thái ghi ở dòng `Status:`.
- [`domain.md`](./domain.md): single-context, `GLOSSARY.md` và `docs/adr/` ở gốc repo.
- Khối `## Agent skills` trong `CLAUDE.md` trỏ tới ba file trên.

Hai chỗ repo khác mặc định của plugin, cần nhớ khi skill chạy:

- `to-tickets` mặc định ghi mỗi ticket thành một file `.scratch/<feature>/issues/<NN>-<slug>.md`. Repo dùng **thư mục** `issues/<NN>-<slug>/spec.md`; `issue-tracker.md` (mục "Khi skill nói publish to the issue tracker") đã ghi đè quy ước này.
- `pr` có khuôn riêng và không đọc `.github/pull_request_template.md`. Repo bắt buộc dùng template của repo ([`11-git-workflow.md`](../architecture/11-git-workflow.md) mục 4.2). Xem [`pr`](#pr-đang-bật).

## 3. Nhóm Engineering

### 3.1. Model-invoked

#### `tdd` [đang bật]

- **Mục đích:** viết code theo vòng red → green sao cho test sinh ra đáng giữ: test hành vi qua interface công khai, không bám chi tiết cài đặt.
- **Khi nào dùng:** muốn làm một tính năng hoặc sửa bug theo kiểu test trước, nhắc tới "red-green-refactor", hoặc cần integration test.
- **Skill làm gì:**
  1. Đọc `GLOSSARY.md` để tên test và tên interface khớp thuật ngữ domain; tôn trọng ADR ở khu vực sắp sửa.
  2. Đề xuất các **seam** sẽ test, mỗi seam một dòng ghi nó bắt được gì, bỏ sót gì, và **chờ bạn xác nhận**. Không viết test ở seam chưa được duyệt.
  3. Mỗi vòng: một seam, một test đỏ, đúng đủ code để xanh. Làm theo **lát dọc** (tracer bullet), không viết hết test rồi mới viết code.
  4. Tránh các anti-pattern: test bám cài đặt (mock collaborator nội bộ, kiểm qua DB thay vì qua interface), test tautological (giá trị mong đợi tính lại y như code), cắt ngang theo lớp.
  5. Refactor **không** nằm trong vòng; đó là việc của bước review (`code-review`).
- **Đầu ra:** test và code đi kèm, mỗi lát một cặp red/green.
- **Ví dụ:**

  ```text
  /mattpocock-skills:tdd Làm AC "Hai refresh đồng thời chỉ tạo một successor" của ticket
  .scratch/module-plans/m1-catalog-inventory/issues/02-refresh-logout/. Seam đề xuất:
  service refresh trong modules/identity/services/auth.py và endpoint refresh back-office.
  ```

- **Lưu ý:** skill không biết các ticket khác trong cùng feature, nên có thể đề xuất việc thuộc ticket anh em; đưa kèm `spec.md` của feature để giảm rủi ro này.

#### `diagnosing-bugs` [đang bật]

- **Mục đích:** kỷ luật chẩn đoán bug khó và hồi quy hiệu năng. Cốt lõi: có một feedback loop **đỏ** trên đúng bug này rồi mới được đoán nguyên nhân.
- **Khi nào dùng:** bạn nói "diagnose"/"debug this", hoặc báo có thứ hỏng, ném lỗi, test fail, chạy chậm; đặc biệt bug không rõ ngay, bug chập chờn, hồi quy giữa hai trạng thái từng tốt.
- **Skill làm gì (6 phase, mỗi phase có cổng):**
  1. **Dựng feedback loop**: một lệnh duy nhất (test, `curl`, script...) đã chạy ít nhất một lần, đỏ đúng triệu chứng bạn báo, ổn định, chạy trong vài giây, agent tự chạy được. Chưa có lệnh này thì không sang phase 2.
  2. **Tái hiện và thu nhỏ**: cắt bớt input, dữ liệu, bước, tới khi mọi phần còn lại đều cần thiết để loop còn đỏ.
  3. **Giả thuyết**: 3–5 giả thuyết có thể bác bỏ, xếp hạng, đưa bạn xem trước khi kiểm (bạn vắng thì agent tự theo thứ hạng).
  4. **Đo đạc**: mỗi probe ứng với một dự đoán; log debug gắn tiền tố như `[DEBUG-a4f2]` để dọn bằng một lệnh `grep`. Với hiệu năng: đo baseline trước, sửa sau.
  5. **Sửa và regression test**: viết test hồi quy trước khi sửa, nhưng chỉ khi có seam đúng. Không có seam đúng thì ghi lại, đó chính là phát hiện về kiến trúc.
  6. **Dọn dẹp**: loop gốc hết đỏ, xoá log `[DEBUG-...]`, ghi giả thuyết đúng vào commit hoặc PR.
- **Đầu ra:** bản sửa kèm regression test, hoặc báo cáo rõ vì sao chưa dựng được loop.
- **Ví dụ:**

  ```text
  /mattpocock-skills:diagnosing-bugs Event delivery không chuyển failed khi worker bị kill
  giữa lúc chạy handler. Dựng loop bằng test trong backend/shared/events.
  ```

- **Lưu ý:** skill che (`<REDACTED>`) secret trong mọi output; hợp với quy tắc không in `.env*` của repo. Không có cổng hỏi bạn trước khi viết bản sửa; muốn có thì nói rõ lúc gọi.

#### `code-review` [đang bật]

- **Mục đích:** review diff từ một **mốc cố định** (commit, nhánh, tag, merge-base) tới `HEAD` theo hai trục tách biệt:
  - **Standards**: code có theo chuẩn viết code mà repo ghi lại không, cộng một bộ "smell" nền của Fowler (Mysterious Name, Duplicated Code, Feature Envy, Speculative Generality...).
  - **Spec**: code có làm đúng ticket/spec gốc không (thiếu, thừa ngoài phạm vi, làm sai).
- **Khi nào dùng:** review một nhánh, một PR, việc đang làm dở, hoặc "review từ X".
- **Skill làm gì:**
  1. Chốt mốc, kiểm `git rev-parse` và diff không rỗng; diff dạng ba chấm `git diff <mốc>...HEAD`.
  2. Tìm spec: số issue trong commit, đường dẫn bạn đưa, hoặc file trong `.scratch/` khớp tên nhánh; không có thì hỏi.
  3. Tìm mọi file chuẩn code (bắt buộc có `CONTRIBUTING.md` nếu tồn tại). Chuẩn của repo luôn thắng smell nền; smell luôn chỉ là nhận định, không phải vi phạm cứng.
  4. Chạy hai sub-agent song song, mỗi cái dưới 400 từ.
  5. Trình bày hai báo cáo dưới `## Standards` và `## Spec`, không gộp, không xếp hạng chéo.
- **Đầu ra:** báo cáo hai mục, kết bằng một dòng: số phát hiện mỗi trục và lỗi nặng nhất của từng trục.
- **Ví dụ:**

  ```text
  /mattpocock-skills:code-review origin/dev. Spec là
  .scratch/module-plans/m1-catalog-inventory/issues/03-category-navigation/spec.md;
  chuẩn code: docs/architecture/13-python-django-coding-style.md và CONTRIBUTING.md.
  ```

- **Lưu ý (theo tài liệu của plugin):**
  - Không thấy thay đổi chưa commit, vì diff là `<mốc>...HEAD`. Commit trước rồi review.
  - Nên chạy ở phiên mới, không phải phiên vừa viết code, để tránh tự xác nhận.
  - Phát hiện là giả thuyết; mở dòng được trích để kiểm trước khi sửa. Chạy lại lần nào cũng ra phát hiện mới, đừng lặp tới khi "sạch".
  - Lỗi đã biết: sub-agent có thể gọi lại `code-review` và đẻ thêm agent; để ý số agent khi chạy.

#### `codebase-design` [đang bật]

- **Mục đích:** bộ từ vựng và nguyên tắc chung để thiết kế **deep module**: nhiều hành vi sau một interface nhỏ, đặt ở seam sạch, test được qua chính interface đó.
- **Khi nào dùng:** thiết kế hoặc cải thiện interface, tìm cơ hội "deepening", quyết định đặt seam ở đâu, làm code dễ test hơn; hoặc khi skill khác (`tdd`, `improve-codebase-architecture`) cần bộ từ vựng này.
- **Nội dung chính:**
  - Thuật ngữ: **module** (bất kỳ thứ gì có interface và implementation, ở mọi cỡ), **interface** (mọi điều caller phải biết: chữ ký, bất biến, lỗi, hiệu năng), **depth**, **seam**, **adapter**, **leverage**, **locality**. Tránh "component", "service", "API", "boundary".
  - Nguyên tắc: depth là thuộc tính của interface; **deletion test** (xoá module đi, độ phức tạp biến mất thì nó chỉ là pass-through); interface chính là bề mặt test; "một adapter là seam giả định, hai adapter mới là seam thật".
  - File phụ: `DEEPENING.md` (deepening một cụm theo loại phụ thuộc), `DESIGN-IT-TWICE.md` (nhiều sub-agent song song thiết kế interface theo các cách khác hẳn nhau rồi so sánh).
- **Đầu ra:** không sinh file; là tài liệu tham chiếu khi thảo luận và thiết kế.
- **Ví dụ:**

  ```text
  /mattpocock-skills:codebase-design Áp deletion test cho các hàm public trong
  modules/identity/services/auth.py: hàm nào chỉ chuyển tiếp lời gọi?
  ```

- **Lưu ý:** trong repo, "module" thường nghĩa là module nghiệp vụ dưới `backend/modules/` (ADR 0006). Khi dùng từ vựng của skill này, gọi cụ thể là hàm, class hay package để khỏi lẫn.

#### `domain-modeling` [đang bật]

- **Mục đích:** chủ động xây và mài mô hình domain: chất vấn thuật ngữ, dựng tình huống biên, ghi `GLOSSARY.md` và ADR ngay khi chốt. Chỉ *đọc* glossary thì không cần skill này.
- **Khi nào dùng:** đang bàn thuật ngữ trong code, viết hoặc sửa `GLOSSARY.md`, ghi hoặc sửa ADR.
- **Skill làm gì:**
  - Thuật ngữ bạn dùng mâu thuẫn glossary → chỉ ra ngay.
  - Từ mơ hồ hoặc quá tải nghĩa → đề xuất từ chuẩn.
  - Dựng tình huống cụ thể để thử ranh giới giữa các khái niệm.
  - Đối chiếu với code; code nói khác lời bạn thì hỏi lại.
  - Cập nhật `GLOSSARY.md` ngay khi chốt từng thuật ngữ (theo `GLOSSARY-FORMAT.md`); glossary không chứa chi tiết cài đặt.
  - Chỉ đề xuất ADR khi đủ cả ba điều kiện: khó đảo ngược, gây bất ngờ nếu thiếu ngữ cảnh, là kết quả của một trade-off thật (theo `ADR-FORMAT.md`).
- **Đầu ra:** sửa đổi trong `GLOSSARY.md` và/hoặc ADR mới trong `docs/adr/`.
- **Ví dụ:**

  ```text
  /mattpocock-skills:domain-modeling Khi Staff Kiểm kê, phần chênh lệch có tính cả
  Hàng chờ xuất không? Chốt định nghĩa rồi cập nhật GLOSSARY.md nếu cần.
  ```

#### `prototype` [đang bật]

- **Mục đích:** viết code thử, dùng xong bỏ, để trả lời **một** câu hỏi thiết kế.
- **Khi nào dùng:** muốn kiểm xem một state model hoặc logic có "đúng cảm giác" không, hoặc thử xem UI nên trông thế nào.
- **Skill làm gì:** chọn một trong hai nhánh:
  - **Logic/state** (`LOGIC.md`): một file HTML duy nhất, mở bằng double-click, có nút chơi tự do và các tab hướng dẫn đẩy state machine qua những ca khó nghĩ trên giấy; người không phải dev cũng chạy được.
  - **UI** (`UI.md`): nhiều biến thể UI khác hẳn nhau trên một route, chuyển bằng search param và thanh nổi ở đáy.
  - Quy tắc chung: đánh dấu rõ là prototype, đặt gần nơi sẽ dùng, chạy bằng một lệnh, không lưu trữ bền (trừ khi chính câu hỏi là về DB), bỏ qua test và trau chuốt, hiển thị toàn bộ state sau mỗi thao tác.
- **Đầu ra:** prototype chạy được; khi xong, đưa quyết định đã kiểm vào code thật, commit prototype lên nhánh tạm `prototype/<tên>` (không merge) và để con trỏ tới nhánh đó trong ticket.
- **Ví dụ:**

  ```text
  /mattpocock-skills:prototype Dựng HTML mô phỏng Giữ hàng 15 phút: đặt đơn online,
  hết hạn, thanh toán trễ. Hiện Tồn kho và Số lượng bán được sau mỗi bước.
  ```

- **Lưu ý:** repo này là backend nên chủ yếu dùng nhánh logic. Câu hỏi mơ hồ mà bạn không có mặt, skill chọn nhánh theo code xung quanh (module backend → logic) và ghi giả định ở đầu prototype.

#### `research` [đang bật]

- **Mục đích:** giao việc đọc tài liệu cho một **agent nền**, chỉ dùng nguồn gốc (tài liệu chính thức, source code, spec, API của bên cung cấp), ghi kết quả có trích dẫn ra một file Markdown.
- **Khi nào dùng:** cần một sự thật ở ngoài thư mục làm việc để ra quyết định (API bên thứ ba hoạt động thế nào, phiên bản nào có tính năng gì), và không muốn dừng luồng của mình để đọc.
- **Skill làm gì:** chạy agent nền; agent lần mỗi khẳng định về nguồn sở hữu nó, viết một file, lưu theo quy ước ghi chú sẵn có của repo (không có thì chọn chỗ hợp lý và báo đường dẫn).
- **Đầu ra:** một file Markdown, mỗi khẳng định có link nguồn. Repo đang để file loại này trong thư mục `research/` của feature, ví dụ `.scratch/module-plans/m1-catalog-inventory/research/backoffice-auth-libraries.md`.
- **Ví dụ:**

  ```text
  /mattpocock-skills:research GHN API tạo Vận đơn: các trạng thái webhook và cách
  xác thực chữ ký. Lưu vào .scratch/<feature>/research/ghn-webhook.md.
  ```

- **Lưu ý (theo tài liệu của plugin):** câu hỏi càng hẹp kết quả càng tốt, vì skill không có tiêu chí dừng. Lỗi đã biết: agent nền có thể tự gọi thêm agent nền khác; để ý danh sách task nền. File research không tự được nạp lại ở phiên sau; bạn phải trỏ ticket hoặc spec tới nó. Kiểm vài link trích dẫn xem có dẫn tới nguồn gốc thật không.

#### `pr` [đang bật]

- **Mục đích:** khuôn cho phần mô tả PR, gồm ba mục:
  - **Summary**: hình nhỏ nhất làm rõ thay đổi (pseudocode, call tree, cây file, Mermaid, `diff`).
  - **Evidence**: trước/sau; ảnh chụp tốt nhất nếu thay đổi có giao diện, kế đến là kết quả test hoặc output.
  - **Merge Danger**: one-way hay two-way door, và **blast radius**.
- **Khi nào dùng:** khi viết mô tả PR; agent tự dùng mỗi khi được nhờ mở PR.
- **Đầu ra:** nội dung mô tả PR. Skill không tự mở PR.
- **Ví dụ:**

  ```text
  /mattpocock-skills:pr Viết mô tả PR cho nhánh feat/catalog-categories theo
  .github/pull_request_template.md; thêm Summary dạng call tree và Merge Danger.
  ```

- **Lưu ý:** skill không đọc `.github/pull_request_template.md`. Ở repo này template của repo là bắt buộc, kể cả mục **Gap và lưu ý**; nếu dùng `pr`, đặt Summary/Evidence/Merge Danger vào bên trong template của repo, không thay thế nó.

#### `wizard` [đang bật]

- **Mục đích:** sinh một script bash tương tác dẫn **người** qua các bước chỉ người làm được: dựng hạ tầng, tạo credential hoặc secret CI, thao tác dashboard bên thứ ba, chạy migration hoặc cutover một lần.
- **Khi nào dùng:** agent gặp bước nó không tự làm được. Nếu agent tự làm được thì không dùng skill này.
- **Skill làm gì:**
  1. Xác định phạm vi: liệt kê mọi bước và mọi giá trị cần thu, giá trị đó lấy ở đâu, ghi vào đâu (`.env`, GitHub secret), có phải secret không. Xác nhận thứ tự với bạn.
  2. Viết đường đi chính xác cho từng bước (mở URL nào, bấm gì, copy gì). Không biết UI hiện tại thì hỏi hoặc tra tài liệu, không bịa bước.
  3. Copy `template.sh`, chỉ viết phần `stage` (thư viện phía trên marker giữ nguyên).
  4. Kiểm bằng `bash -n`, `shellcheck` nếu có, `chmod +x`; không tự chạy script vì nó mở trình duyệt và chờ người nhập.
- **Đầu ra:** một script bash; mặc định dùng một lần rồi xoá, chỉ commit khi bạn muốn giữ làm đường setup lặp lại được.
- **Ví dụ:**

  ```text
  /mattpocock-skills:wizard Dẫn tôi lấy key sandbox VNPay, MoMo và GHN cho đợt nghiệm
  thu M7, ghi vào .env và GitHub secret mà workflow CI cần.
  ```

- **Lưu ý:** bước 1 của skill bảo đọc `.env` và `.env.*`. Repo cấm đọc các file này (trừ `.env.example`) và đã chặn bằng `permissions.deny`; hãy nói rõ chỉ đọc `.env.example`, `docker-compose.yml` và `.github/workflows/`.

### 3.2. User-invoked

#### `ask-matt`

- **Mục đích:** hỏi xem skill hay luồng nào hợp với tình huống của bạn; là bộ định tuyến qua các skill user-invoked.
- **Nội dung:** mô tả luồng chính *ý tưởng → ship*, các "on-ramp" (`triage`, `diagnosing-bugs`, `wayfinder`), việc giữ sức khoẻ codebase, và cách chọn ở **ranh giới phase** giữa *Continue*, `/clear`, `/handoff`, sub-agent, `/compact`. Skill dặn đọc `SKILL.md` của skill định khuyên trước khi khuyên.
- **Đầu ra:** lời khuyên trong hội thoại.
- **Ví dụ:** `/mattpocock-skills:ask-matt Tôi có spec M2 checkout COD và 10 ticket, nên chạy gì tiếp?`

#### `setup-matt-pocock-skills`

- **Mục đích:** cấu hình repo cho các skill engineering: issue tracker, nhãn triage, bố cục tài liệu domain. Chạy một lần mỗi repo.
- **Skill làm gì:** khảo sát repo (git remote, `CLAUDE.md`, `GLOSSARY.md`, `docs/adr/`, `docs/agents/`, `.scratch/`), hỏi từng mục (tracker, nhãn triage nếu có cài `triage`, single hay multi-context), cho xem bản nháp, rồi ghi `docs/agents/*.md` và khối `## Agent skills`.
- **Đầu ra:** `docs/agents/issue-tracker.md`, `triage-labels.md`, `domain.md`, khối `## Agent skills` trong `CLAUDE.md`.
- **Ở repo này:** đã cấu hình xong (xem [mục 2](#2-cấu-hình-của-repo-cho-plugin)). Chỉ chạy lại khi đổi tracker hoặc làm lại từ đầu; nếu chạy, đọc kỹ bản nháp để không mất phần tuỳ biến tiếng Việt.

#### `grill-with-docs`

- **Mục đích:** buổi grilling có để lại dấu vết: vừa phỏng vấn để mài kế hoạch, vừa cập nhật `GLOSSARY.md` và ADR khi quyết định chốt.
- **Skill làm gì:** gọi hai skill `grilling` và `domain-modeling`.
- **Khi nào dùng:** bắt đầu mọi thay đổi khi đang làm trong một repo. Không có repo thì dùng `grill-me`.
- **Đầu ra:** hiểu biết chung đã chốt, cộng thay đổi trong `GLOSSARY.md`/`docs/adr/`.
- **Ví dụ:** `/mattpocock-skills:grill-with-docs Tôi muốn thêm Voucher vào Tính thử ở M2.`

#### `to-spec`

- **Mục đích:** biến hội thoại hiện tại thành spec và đăng lên tracker. **Không phỏng vấn**, chỉ tổng hợp điều đã bàn.
- **Skill làm gì:**
  1. Khám phá repo nếu chưa làm; dùng thuật ngữ glossary, tôn trọng ADR.
  2. Phác các seam sẽ test (ưu tiên seam có sẵn, seam cao nhất, càng ít càng tốt) và hỏi bạn xác nhận.
  3. Viết spec theo khuôn: Problem Statement, Solution, User Stories (danh sách dài, đánh số), Implementation Decisions (không ghi đường dẫn file hay code), Testing Decisions, Out of Scope, Further Notes. Gắn trạng thái `ready-for-agent`.
- **Đầu ra:** `.scratch/<feature-slug>/spec.md`. Ví dụ đã có: `.scratch/module-plans/m1-catalog-inventory/spec.md`.
- **Ví dụ:** sau một buổi grilling về M2, gõ `/mattpocock-skills:to-spec` trong **cùng phiên**.

#### `to-tickets`

- **Mục đích:** chia spec, kế hoạch hoặc hội thoại thành các ticket **tracer bullet** (lát dọc), mỗi ticket khai báo ticket nào chặn nó.
- **Skill làm gì:**
  1. Lấy ngữ cảnh (đọc spec nếu được đưa đường dẫn), khám phá code, tìm chỗ nên "prefactor" trước.
  2. Mỗi lát cắt xuyên mọi lớp (schema, API, test), tự demo hoặc kiểm được, vừa một context window mới.
  3. Ngoại lệ **wide refactor** (đổi tên cột, đổi kiểu dùng khắp nơi): làm theo expand → migrate theo lô → contract.
  4. Trình bày danh sách (Title, Blocked by, What it delivers), hỏi độ mịn và cạnh chặn, lặp tới khi bạn duyệt.
  5. Đăng theo thứ tự phụ thuộc, trạng thái `ready-for-agent`.
- **Đầu ra:** các ticket dưới `.scratch/<feature-slug>/issues/`; repo dùng thư mục `<NN>-<slug>/spec.md` (xem [mục 2](#2-cấu-hình-của-repo-cho-plugin)).
- **Ví dụ:** `/mattpocock-skills:to-tickets .scratch/module-plans/m1-catalog-inventory/spec.md`
- **Lưu ý:** ticket do `to-tickets` sinh ra đã sẵn sàng cho agent; không cần chạy `triage` cho chúng.

#### `implement`

- **Mục đích:** làm phần việc mô tả trong spec hoặc ticket.
- **Skill làm gì:** đọc ticket và nêu tiêu đề; gọi `tdd` tại các seam đã thống nhất; chạy typecheck và từng file test thường xuyên, full suite một lần cuối; gọi `code-review`; commit vào nhánh hiện tại.
- **Đầu ra:** commit trên nhánh hiện tại. Không mở PR.
- **Ví dụ:** `/mattpocock-skills:implement .scratch/module-plans/m1-catalog-inventory/issues/04-size-color-registry/`
- **Lưu ý:** bước review chạy ngay trong phiên vừa viết code. Với ticket trong `.scratch/` của repo, ưu tiên `ship-ticket-fashion` (xem [mục 10](#10-chồng-chéo-với-ship-ticket-fashion)).

#### `implement-spec`

- **Mục đích:** làm **toàn bộ** một spec trên một **integration branch**, coi các ticket là đồ thị phụ thuộc và chạy song song nhiều sub-agent trên **frontier** (các ticket đã hết bị chặn).
- **Skill làm gì:** đọc spec và ticket; (tuỳ chọn) một sub-agent khám phá ghi chú ra ngoài repo; tạo integration branch; mỗi ticket một implementer sub-agent trong worktree riêng, chạy `tdd`; merger sub-agent gộp vào integration branch; mở thêm sub-agent khi frontier đổi; cuối cùng `code-review` trên integration branch và sửa trong một sub-agent; dọn worktree.
- **Đầu ra:** một integration branch chứa cả spec; mở draft PR nếu tracker đóng việc qua PR hoặc bạn yêu cầu.
- **Lưu ý:** repo quy ước mỗi ticket một PR vào `dev`, PR dưới khoảng 400 dòng ([`11-git-workflow.md`](../architecture/11-git-workflow.md)). Một integration branch cho cả spec lệch quy ước này; cân nhắc trước khi dùng.

#### `triage`

- **Mục đích:** đưa issue (và PR bên ngoài nếu tracker bật) qua máy trạng thái triage: hai vai trò loại (`bug`, `enhancement`) và năm vai trò trạng thái (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`).
- **Skill làm gì:** liệt kê việc cần chú ý; với từng issue: đọc đủ, kiểm đã có cài đặt chưa và đã từng bị từ chối chưa (`.out-of-scope/`), đề xuất, **tái hiện/kiểm khẳng định** trước khi grill, grill nếu cần (gọi `grilling` + `domain-modeling`), rồi áp kết quả: agent brief (`AGENT-BRIEF.md`), ghi chú `needs-info`, hoặc đóng `wontfix`. Mọi bình luận bắt đầu bằng dòng ghi là do AI sinh ra.
- **Đầu ra:** dòng `Status:` được cập nhật, kèm brief hoặc ghi chú trong ticket.
- **Ví dụ:** `/mattpocock-skills:triage .scratch/sandbox-acceptance/issues/01-load-test-k6-staging/` (ticket đang `needs-triage`).
- **Lưu ý:** chỉ dùng cho việc **không** do bạn tạo qua `to-tickets`. Repo chưa có thư mục `.out-of-scope/`; việc ngoài phạm vi đang ghi vào `.scratch/backlog.md`.

#### `improve-codebase-architecture`

- **Mục đích:** quét codebase tìm **cơ hội deepening** (biến module nông thành sâu) để dễ test và dễ cho agent điều hướng.
- **Skill làm gì:**
  1. Chọn phạm vi trước: theo hướng bạn nêu, nếu không thì theo các "điểm nóng" trong `git log`.
  2. Đọc glossary và ADR, cho một sub-agent đi khắp code ghi lại chỗ ma sát; áp deletion test.
  3. Viết báo cáo HTML (Tailwind + Mermaid qua CDN) vào thư mục tạm của hệ điều hành, mỗi ứng viên một thẻ: Files, Problem, Solution, Benefits, sơ đồ trước/sau, mức khuyến nghị (`Strong`, `Worth exploring`, `Speculative`), cuối có *Top recommendation*. Chưa đề xuất interface.
  4. Bạn chọn một ứng viên → grilling cùng `domain-modeling`; bạn bác ứng viên với lý do quan trọng → đề xuất ADR để lần sau khỏi gợi ý lại.
- **Đầu ra:** file HTML ngoài repo, và các thay đổi `GLOSSARY.md`/ADR phát sinh khi grill.
- **Ví dụ:** `/mattpocock-skills:improve-codebase-architecture backend/shared/events (outbox, relay, consumer)`

#### `wayfinder`

- **Mục đích:** lên kế hoạch cho việc quá lớn, mù mờ, không vừa một phiên agent: dựng một **map** gồm các **ticket quyết định**, giải từng cái tới khi đường tới đích rõ. Sinh ra **quyết định**, không sinh sản phẩm.
- **Skill làm gì:**
  - *Chart*: grill để gọi tên **đích** (destination); grill theo chiều rộng để tìm frontier; tạo map (Destination, Notes, Decisions so far, Not yet specified, Out of scope); tạo ticket rồi nối cạnh chặn; bắn sub-agent `research` cho các ticket loại research.
  - *Work*: nạp map, nhận (claim) một ticket frontier, giải theo loại (`research`, `prototype`, `grilling`, `task`), ghi câu trả lời, đóng ticket, thêm dòng vào Decisions so far. Mỗi phiên tối đa một ticket (trừ research).
- **Đầu ra:** theo `issue-tracker.md`: map ở `.scratch/<effort>/map.md`, ticket con ở `.scratch/<effort>/issues/NN-<slug>/spec.md` với dòng `Type:` và `Status: claimed|resolved`.
- **Khi map xong:** quay về luồng chính tại `to-spec`, rồi `to-tickets`.
- **Ví dụ:** `/mattpocock-skills:wayfinder Lên đường cho M7 nghiệm thu sandbox VNPay, MoMo, GHN.`
- **Lưu ý:** chỉ dùng cho việc thật sự lớn và mù mờ; việc đã rõ phạm vi thì dùng `grill-with-docs`.

#### `retro`

- **Mục đích:** sau một phiên code, đề xuất cải thiện **môi trường** của agent (không phải code), nặng nhất trước.
- **Skill làm gì:** gọi `writing-for-agents`, đọc log phiên (mặc định phiên hiện tại), tìm ứng viên theo các nhóm: điều hướng, check tự động (lỗi cơ học → lint/hook/CI, không viết thành quy tắc), chuẩn code cho reviewer, `AGENTS.md`/`CLAUDE.md` quá dài, tool tốn token, câu chỉ dẫn không đổi hành vi, quyền truy cập thông tin.
- **Đầu ra:** danh sách đề xuất trong hội thoại.
- **Ví dụ:** chạy `/mattpocock-skills:retro` trong chính phiên vừa sửa bug outbox, trước khi `/clear`.

## 4. Nhóm Productivity

### 4.1. Model-invoked

#### `grilling` [đang bật]

- **Mục đích:** phỏng vấn không ngừng về một kế hoạch, quyết định hoặc ý tưởng tới khi hai bên hiểu như nhau. Đây là "primitive" mà `grill-me`, `grill-with-docs`, `triage`, `wayfinder`, `improve-codebase-architecture` dùng bên trong.
- **Skill làm gì:**
  - Coi vấn đề là **cây quyết định**; hỏi theo **vòng**. Mỗi vòng hỏi toàn bộ **frontier** (các câu đã đủ tiền đề), đánh số, kèm câu trả lời khuyên dùng, viết sao cho trả lời "yes" là chấp nhận khuyến nghị.
  - Tìm **sự thật** là việc của agent (dùng sub-agent tra code, file); **quyết định** là việc của bạn.
  - Xong khi frontier rỗng. Chưa hành động cho tới khi bạn xác nhận đã hiểu chung.
- **Đầu ra:** các quyết định đã chốt trong hội thoại (không ghi file; muốn ghi glossary/ADR thì dùng `grill-with-docs`).
- **Ví dụ:**

  ```text
  /mattpocock-skills:grilling Grill tôi về thiết kế Kiểm kê ticket 10: phạm vi, xử lý
  khi đang có Giữ hàng, ai được điều chỉnh, seam để test.
  ```

#### `writing-for-agents` [đang bật]

- **Mục đích:** hướng dẫn viết mọi tài liệu agent đọc: skill, `AGENTS.md`/`CLAUDE.md`, tài liệu được trỏ tới.
- **Nội dung chính:** **context pointer** (mô tả skill, một dòng trong `CLAUDE.md`) quyết định khi nào agent đọc tài liệu; hai loại tải (context load và cognitive load); thang thông tin (bước trong file → tham chiếu trong file → tham chiếu tách ra file khác); mỗi bước có **tiêu chí hoàn thành** rõ; **leading word**; viết theo hướng khẳng định thay vì cấm đoán; cắt tỉa (một nguồn sự thật, không chép lại thứ môi trường đã có, săn câu "no-op"). Với skill, đọc thêm `SKILL-MECHANICS.md`.
- **Đầu ra:** không sinh file; là tài liệu tham chiếu khi viết.
- **Ví dụ:** `/mattpocock-skills:writing-for-agents Rà .claude/skills/ship-ticket-fashion/phases/2-code.md, tìm câu no-op và chỗ trùng lặp.`

### 4.2. User-invoked

#### `grill-me`

- **Mục đích:** như `grill-with-docs` nhưng **không lưu gì** (không glossary, không ADR). Gọi `grilling`.
- **Khi nào dùng:** không làm trong một repo: mài một kế hoạch, một bài viết. Trong repo này thì `grill-with-docs` tốt hơn.

#### `handoff`

- **Mục đích:** nén hội thoại thành tài liệu bàn giao để agent khác làm tiếp.
- **Skill làm gì:** ghi file vào thư mục tạm của hệ điều hành (không phải workspace); có mục "suggested skills"; tham chiếu spec, ADR, commit bằng đường dẫn thay vì chép lại; che thông tin nhạy cảm. Tham số (nếu có) mô tả phiên kế tiếp sẽ làm gì.
- **Đầu ra:** một file Markdown trong `$TMPDIR` hoặc `/tmp`.
- **Ví dụ:** `/mattpocock-skills:handoff .scratch/module-plans/m1-catalog-inventory/issues/05-product-variant-management grill` (`ship-ticket-fashion` gợi ý dạng `handoff <ticket> <phase>` khi ngữ cảnh grilling chưa lưu vào state).
- **Lưu ý:** hỏi lại đường dẫn file ngay; thư mục tạm có thể bị xoá khi khởi động lại máy. Mở phiên mới và bảo agent đọc file đó, không dán nội dung vào lệnh shell.

#### `teach`

- **Mục đích:** dạy bạn một kỹ năng hoặc khái niệm qua nhiều phiên, dùng thư mục hiện tại làm workspace có trạng thái.
- **Skill làm gì:** duy trì `MISSION.md`, `RESOURCES.md`, `NOTES.md`, `learning-records/`, `lessons/*.html`, `reference/*.html`, `assets/`; mỗi bài học ngắn, gắn với mission, có quiz và nguồn tin cậy.
- **Lưu ý:** skill tạo file ngay trong thư mục đang chạy; đừng chạy ở gốc repo này, hãy chạy trong một thư mục riêng.

#### `to-questionnaire`

- **Mục đích:** biến một quyết định bạn không tự trả lời được thành bảng câu hỏi Markdown cho **một** người nắm thông tin điền (bất đồng bộ hoặc trong buổi họp).
- **Skill làm gì:** chỉ hỏi bạn về **việc gửi** (gửi ai, cần nhận lại gì), không hỏi về chủ đề; viết bảng câu hỏi xếp theo mức quan trọng, mỗi câu một ý, có chỗ trả lời.
- **Đầu ra:** `to-questionnaire-<slug>.md` ở thư mục hiện tại.
- **Ví dụ:** `/mattpocock-skills:to-questionnaire` để soạn câu hỏi cho pháp chế hoặc kế toán về các mục **[Cần xác minh trước go-live]** trong `docs/business/06-compliance.md`.

#### `wait-what`

- **Mục đích:** dùng ngay khi tin nhắn của agent khó hiểu: agent trình bày lại, thêm ngữ cảnh, theo ASD-STE100 Simplified Technical English, dùng thuật ngữ trong `GLOSSARY.md`.
- **Ví dụ:** gõ `/mattpocock-skills:wait-what` giữa bất kỳ skill nào.

## 5. Nhóm in-progress (beta, chưa ổn định)

**Không nên dùng cho việc thật.** Các skill này là beta: không nằm trong plugin, không có trang tài liệu, có thể đổi hoặc biến mất không báo trước. Muốn thử thì cài riêng bằng `npx skills@latest add mattpocock/skills --skill=<name>`.

| Skill | Làm gì | Gọi |
| --- | --- | --- |
| `loop-me` | Grilling có trạng thái để viết spec cho các **workflow** lặp lại trong đời sống/công việc (trigger, checkpoint, brief); lưu ở `workflows/*.md` và `NOTES.md` | User |
| `writing-fragments` | Grilling để "đào" mảnh viết rời, nối vào một file Markdown làm nguyên liệu bài viết | User |
| `writing-shape` | Lấy file nguyên liệu, nặn thành bài viết từng đoạn, tranh luận chọn định dạng mỗi khối | User |
| `writing-beats` | Viết bài theo các "beat", chọn đường kiểu choose-your-own-adventure, đảm bảo khái niệm được giới thiệu trước khi dùng | User |
| `claude-handoff` | Như `handoff` nhưng khởi động luôn một agent nền bằng `claude --bg --name ...` | User |
| `setup-ts-deep-modules` | Cài dependency-cruiser cho repo TypeScript để mỗi package chỉ truy cập được qua file entry point | User |
| `chief-of-staff` | Theo đuổi một mục tiêu dài trong một phiên bằng cách điều phối sub-agent và lịch chạy | User |

`chief-of-staff` có thư mục trong bản cài nhưng không được liệt kê trong `skills/in-progress/README.md`; tình trạng của nó **chưa rõ**. `setup-ts-deep-modules` chỉ dành cho TypeScript, không áp dụng cho backend Django này.

## 6. Nhóm misc (đóng băng)

**Không nên dùng ở repo này.** Tác giả giữ lại nhưng hiếm khi dùng; không có trong plugin, mọi issue bị đóng. Nguồn không nói rõ cách cài riêng.

| Skill | Làm gì | Ghi chú cho Fashion Store |
| --- | --- | --- |
| `git-guardrails-claude-code` | Thêm hook `PreToolUse` chặn `git push`, `reset --hard`, `clean -f`, `branch -D`, `checkout .` | Repo đã có hook riêng `guard_merge_target.py` và `permissions.deny` trong `.claude/settings.json`; thêm hook này cần cân nhắc vì nó chặn mọi `git push` |
| `migrate-to-shoehorn` | Đổi `as` trong test TypeScript sang `@total-typescript/shoehorn` | Chỉ cho TypeScript |
| `scaffold-exercises` | Tạo cấu trúc thư mục bài tập cho khoá học (`pnpm ai-hero-cli`) | Không liên quan |
| `setup-pre-commit` | Cài Husky + lint-staged + Prettier | Repo dùng framework `pre-commit` (`.pre-commit-config.yaml`), không dùng Husky |

## 7. Nhóm deprecated

Đang rỗng. Theo `skills/deprecated/README.md`, skill bị bỏ sẽ bị xoá, và changeset xoá nó ghi skill nào thay thế.

Thư mục `docs/` của plugin có trang `resolving-merge-conflicts.md` nhưng bản 1.3.1 không có `SKILL.md` tương ứng; skill này **chưa có** trong bản cài.

## 8. Luồng làm việc nối các skill

### 8.1. Luồng chính: ý tưởng → ship

```text
grill-with-docs (grilling + domain-modeling)
   │   cần câu trả lời chạy được? → handoff → prototype → handoff quay lại
   │   cần sự thật bên ngoài?     → research (agent nền, ghi file)
   ▼
nhiều phiên? ── có ──▶ to-spec ──▶ to-tickets ──▶ implement (mỗi ticket, /clear giữa các ticket)
   │                                         └──▶ hoặc implement-spec (cả spec, chạy song song)
   └── không ──▶ implement ngay trong phiên
                       │
                       ▼
            tdd (từng lát red → green) ──▶ code-review (Standards + Spec)
                       │
                       ▼
                 pr (mô tả PR) ──▶ retro (cải thiện môi trường)
```

- Giữ grilling, `to-spec`, `to-tickets` trong **một** context window liên tục; mỗi lần `implement` bắt đầu phiên mới, làm việc từ ticket.
- `codebase-design` và `domain-modeling` chạy "bên dưới": các skill khác tự kéo vào khi bàn interface/seam hoặc thuật ngữ.

### 8.2. Các nhánh vào luồng chính

| Điểm xuất phát | Skill | Nhập vào luồng chính ở |
| --- | --- | --- |
| Có thứ hỏng, test đỏ, chạy chậm | `diagnosing-bugs` | Sửa xong → `retro`; không có seam tốt → `improve-codebase-architecture` |
| Issue/ticket thô không do mình tạo | `triage` | `ready-for-agent` → `implement` |
| Việc khổng lồ, mù mờ (cả một mốc mới) | `wayfinder` | Map xong → `to-spec` → `to-tickets` |
| Rảnh tay, muốn giữ codebase khoẻ | `improve-codebase-architecture` | Ứng viên đã chọn → `grill-with-docs` |
| Thuật ngữ lộn xộn, cần ADR | `domain-modeling` | Bất kỳ lúc nào |
| Câu hỏi thiết kế khó nghĩ trên giấy | `prototype` | Quyết định đưa vào spec/ticket |
| Cần sự thật từ tài liệu bên ngoài | `research` | File kết quả đưa vào grilling hoặc spec |
| Thiếu thông tin nằm ở người khác | `to-questionnaire` | Câu trả lời đưa vào `grill-with-docs` hoặc `to-spec` |
| Bước chỉ người làm được (secret, dashboard) | `wizard` | Chạy script rồi quay lại việc đang dở |

## 9. Bảng tra nhanh: tình huống → skill

| Tình huống | Skill nên dùng |
| --- | --- |
| Làm một ticket trong `.scratch/` từ đầu tới merge | `/ship-ticket-fashion` (skill dự án) |
| Không biết nên dùng skill nào | `/mattpocock-skills:ask-matt` |
| Muốn bị chất vấn về một ý tưởng trước khi làm | `/mattpocock-skills:grill-with-docs` (trong repo) hoặc `grilling` |
| Đã bàn xong, cần viết spec cho một mốc mới | `/mattpocock-skills:to-spec` |
| Có spec, cần chia ticket | `/mattpocock-skills:to-tickets` |
| Viết một hành vi nhỏ ngoài ticket, test trước | `tdd` |
| Bug khó, chập chờn, hồi quy hiệu năng | `diagnosing-bugs` |
| Review nhánh hoặc PR theo spec và chuẩn code | `/mattpocock-skills:code-review` |
| Tìm bug runtime trong diff | `/code-review` có sẵn của Claude Code |
| Bàn nên đặt seam ở đâu, interface có "nông" không | `codebase-design` |
| Quét code tìm chỗ nên refactor | `/mattpocock-skills:improve-codebase-architecture` |
| Một thuật ngữ đang bị dùng hai nghĩa; cần ghi ADR | `domain-modeling` |
| Kiểm state machine (Đơn hàng, Giữ hàng) trước khi code | `prototype` |
| Tra API GHN, VNPay, MoMo hoặc thư viện | `research` |
| Viết mô tả PR | template repo, có thể thêm phần của `pr` |
| Cần người tạo secret, bấm dashboard bên thứ ba | `wizard` |
| Ticket mới ở `needs-triage` | `/mattpocock-skills:triage` |
| Kế hoạch quá lớn cho một phiên | `/mattpocock-skills:wayfinder` |
| Chuyển việc sang phiên/agent khác | `/mattpocock-skills:handoff` |
| Agent vừa nói điều khó hiểu | `/mattpocock-skills:wait-what` |
| Cần hỏi người khác để ra quyết định | `/mattpocock-skills:to-questionnaire` |
| Sau phiên làm việc, muốn agent làm tốt hơn lần sau | `/mattpocock-skills:retro` |
| Sửa skill, `CLAUDE.md`, tài liệu cho agent | `writing-for-agents` |

## 10. Chồng chéo với `ship-ticket-fashion`

Skill dự án [`.claude/skills/ship-ticket-fashion/`](../../.claude/skills/ship-ticket-fashion/SKILL.md) đưa một ticket `.scratch/` qua các phase: plan (khi frontier rỗng) → grill → G1 → code → report → review → sync + retro → G2 → ship → done. Nó **dùng lại** nhiều skill của plugin và thêm phần riêng của repo: preflight môi trường, state ngoài git (`.git/ship-ticket-fashion/`), bằng chứng red/green qua `tdd.py`, mỗi task một commit qua `commit.py`, hai cổng duyệt G1/G2, mở PR theo template repo, đóng ticket và cập nhật `ticket-history.md`.

| Skill plugin | Chỗ `ship-ticket-fashion` dùng hoặc trùng | Nên dùng cái nào |
| --- | --- | --- |
| `grilling` | Phase 0 (chốt phạm vi mốc) và phase 1 (chốt lựa chọn và seam) | Trong ticket: để `ship-ticket-fashion` gọi. Ngoài ticket: gọi thẳng |
| `codebase-design` | Phase 1 khi ticket thêm hoặc đổi interface công khai | Như trên |
| `to-spec`, `to-tickets` | Phase 0 nhắc bạn gõ hai lệnh này, rồi kiểm theo khuôn của repo | Gõ khi `ship-ticket-fashion` nhắc, để spec/ticket đi qua bước kiểm của nó |
| `implement` | Trùng với phase 2 (code) | Ticket `.scratch/`: dùng `ship-ticket-fashion`, vì `implement` không ghi state, không có bằng chứng `tdd.py`, không theo một-task-một-commit và review ngay trong phiên vừa code |
| `implement-spec` | Trùng mục đích (làm nhiều ticket), khác cách: một integration branch cho cả spec | Repo đi theo mỗi ticket một PR; dùng `ship-ticket-fashion` từng ticket |
| `tdd` | Phase 2 dùng `tdd` cho từng slice, kèm `tdd.py` ghi bằng chứng | Trong ticket: qua `ship-ticket-fashion`. Thử nhanh ngoài ticket: gọi thẳng |
| `diagnosing-bugs` | Phase 2 (red sai kỳ vọng), phase 4 (phát hiện `B<n>`), phase 6 (CI đỏ không rõ lý do) | Trong ticket: để skill dự án gọi. Bug ngoài ticket: gọi thẳng |
| `code-review` | Phase 4: Spec + Standards với mốc `origin/dev`, chạy song song với một agent Bug | Trong ticket: phase 4 đã đủ ba trục. Review nhánh bất kỳ: gọi thẳng |
| `pr` | Phase 6 viết mô tả PR tiếng Việt theo `.github/pull_request_template.md` | Theo template repo; `pr` chỉ để tham khảo cách trình bày Summary/Evidence |
| `domain-modeling` | Phase 5: thuật ngữ mới vào `GLOSSARY.md`, quyết định kiến trúc lâu dài thành ADR | Như trên |
| `retro` | Phase 8 chạy retro cho mỗi ticket và `retro #<PR>`; ghi cải tiến theo `writing-for-agents` | Sau ticket: retro của skill dự án. Sau phiên không gắn ticket: `/mattpocock-skills:retro` |
| `handoff` | Gợi ý ở *clear point* khi ngữ cảnh grilling chưa vào state | Theo gợi ý |
| `triage` | Khi chọn ticket, gợi ý gõ `triage` cho ticket `needs-triage` | Theo gợi ý |
| `improve-codebase-architecture` | Phase 0 gợi ý khi một khu vực thành "điểm nóng" | Theo gợi ý |

Tóm lại:

- **Làm ticket trong `.scratch/`**: luôn bắt đầu bằng `/ship-ticket-fashion <feature>/<NN>`. Không chạy `implement` hay `implement-spec` song song cho cùng ticket, vì sẽ lệch state, commit và cách đóng ticket của repo.
- **Việc không gắn ticket** (thử ý tưởng, debug nhanh, review nhánh của người khác, tra tài liệu): gọi thẳng skill của plugin.
- **Lên mốc mới khi chưa có ticket**: `/ship-ticket-fashion <module>` sẽ vào phase 0 và nhắc bạn gõ `to-spec`/`to-tickets` đúng lúc.
