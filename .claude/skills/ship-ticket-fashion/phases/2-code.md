# Phase 2 — code bằng TDD

Full: một sub-agent cho mỗi slice, theo thứ tự DAG (`dependsOn` xong hết mới bắt đầu). Lite: phiên chính làm một slice.

## Trong một slice

1. `state.py set <T> slices.<id>.status=code currentSlice=<id>`. Đọc các mục *tài liệu chi phối* (dòng đầu `## Quyết định`) của file slice sẽ đổi và `CONTRIBUTING.md` mục *Quy ước code*: code theo đúng tên, cấu trúc, quy ước ở đó.
2. `mattpocock-skills:tdd`, chỉ test ở seam của slice. Với mỗi `tddTests`: viết test, chạy `tdd.py <T> <slice> red <test-id>` và thấy đúng `expectedRed`, viết code tối thiểu, chạy lại với `green`. Red khác `expectedRed`, hoặc vẫn đỏ sau hai lần sửa code → `mattpocock-skills:diagnosing-bugs`, dùng chính lệnh `tdd.py` làm vòng phản hồi. Với `verificationTests`: chạy `tdd.py <T> <slice> verify <test-id>` sau thay đổi. Runner giữ bằng chứng; `state.py set/push` không được ghi field này.
3. Test đỏ không thuộc slice → chứng minh nó đỏ trên `origin/dev` (`reference/rules.md` → *Test*), ghi `notes`, làm tiếp.
4. Cần migration → `uv run python manage.py makemigrations <app>` và đọc lại file sinh ra; migration phải đảo ngược được (`docs/architecture/12-testing-strategy.md` mục 6).
5. Cuối slice: `uv run ruff format` và `uv run ruff check --fix` cho file đã đổi, chạy lại các test của slice. Kết quả mypy và `lint-imports` lấy từ `run_logged.py … make lint` (cấu hình đầy đủ như CI); gọi `mypy` theo cách khác có thể báo lỗi không có thật.
6. Commit một lần cho cả slice: `python S/scripts/commit.py <T> --task <id> -m "<subject>" --body "<vì sao>" -- <file>…` (`templates/commit-msg.md`). Script từ chối file không nằm trong `slice.files`; file phát sinh hợp lệ thì cập nhật state và sinh lại plan trước. Còn sửa trong slice trước khi trả về thì `git commit --amend --no-edit` commit đó, chưa push nên an toàn.
7. `state.py set <T> slices.<id>.status=done 'slices.<id>.tests=[…]' 'slices.<id>.handoff=[…]' 'next=…'`. Tên test đổi so với kế hoạch thì ghi tên thật.
8. Sub-agent trả về theo `reference/sub-agent.md`. Phiên chính in điểm clear rồi giao slice tiếp theo.

## Cuối phase

```bash
python S/scripts/run_logged.py --label lint --cwd backend -- make lint
python S/scripts/run_logged.py --label test --cwd backend -- make test
python S/scripts/check_ac_trace.py <T>
python S/scripts/state.py transition <T> --to report --next "viết báo cáo" --reason "mọi slice xanh"
```

Đỏ → sửa trong phạm vi ticket rồi chạy lại (nguyên nhân chưa rõ → `mattpocock-skills:diagnosing-bugs`); đỏ ngoài phạm vi → *Cần người dùng*.

## Xong khi

Mọi slice `done`; `tddTests` có red/green và `verificationTests` có verified green; `make lint`, `make test`, `check_ac_trace.py` xanh; `commit_map.py <T>` in đúng một commit cho mỗi slice, không `FAIL`; `phase` là `report`.
