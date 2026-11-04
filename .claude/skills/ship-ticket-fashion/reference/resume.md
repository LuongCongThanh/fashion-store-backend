# Làm tiếp

Đọc khi `state.py start` in `READ …/reference/resume.md`: có cờ, có slice đang mở, hoặc phase không chỉ đơn giản tiếp tục từ `next`.

## Cờ trước, trước mọi việc

- `BRANCH RED` (nhánh hiện tại khác `branch` của state) → hỏi người dùng: chuyển sang nhánh của state (khuyên dùng), hay lấy nhánh hiện tại làm `branch` mới.
- `DIRTY` → xem `git status --short`: file của ticket thì làm tiếp; file của việc khác thì hỏi người dùng giữ hay stash.
- `BEHIND origin/dev` → `git fetch origin && git rebase origin/dev` trước phase 6; ở phase sớm hơn thì rebase khi tiện, chạy lại test sau rebase.
- `SLICE OPEN` → implementer theo `SKILL.md` → *Sub-agent*; agent đang chạy thì chờ nó trả về.
- `NO PR` ở phase `done` → PR chưa mở được: quay lại phase 6 bước mở PR.

## Theo phase

| Phase | Làm tiếp |
| --- | --- |
| `grill` | G1 đã hỏi nhưng chưa trả lời → trình lại G1 từ `## Quyết định` trong `spec.md` và slice trong state |
| `review` | `<K>-review.md` có đủ ba trục → bỏ qua bước review, đi tiếp từ bước xác minh; thiếu trục nào chỉ chạy lại trục đó |
| `sync` | G2 đã hỏi nhưng chưa trả lời → trình lại G2; G2 đã duyệt nhưng chưa có commit `Task: retro` → `phases/8-retro.md` bước 4–5 |
| `done` | `gh pr view <pr> --json state` (tài khoản ở `phases/6-ship.md`): `MERGED` → phase 7 bước 4; `OPEN` → hỏi merge hay chờ |
| `closed` | Ticket đã xong: chạy `progress.py`, đề xuất ticket tiếp theo |
