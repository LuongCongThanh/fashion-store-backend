# Phase 2 — code bằng TDD

Full: **một** *implementer* sub-agent làm mọi slice theo DAG (`dependsOn` xong mới bắt đầu) rồi trả về một lần (`reference/sub-agent.md`). Lite: phiên chính.

## Trước slice đầu

Read `.git/ship-ticket-fashion/<K>-map.md`, các mục *tài liệu chi phối* (dòng `Tài liệu chi phối` trong `## Quyết định`), `docs/architecture/13-python-django-coding-style.md` (mục khớp loại file: view, service, model, test…) và `CONTRIBUTING.md` mục *Quy ước code*. Code theo đúng tên, cấu trúc, quy ước ở đó. View mới dưới `/api/v1/` phải có `summary` và ví dụ tiếng Anh (`04-api-contract.md` mục 5.6); `make lint` chặn qua `gen_openapi.py --check`.

## Mỗi slice

1. `state.py set <T> slices.<id>.status=code currentSlice=<id>`.
2. `mattpocock-skills:tdd`, chỉ test ở seam của slice.
   - Mỗi `tddTests`: viết test → `tdd.py <T> <slice> red <test-id>` thấy đúng `expectedRed` → code tối thiểu → `tdd.py <T> <slice> green <test-id>`.
   - Mỗi `verificationTests`: `tdd.py <T> <slice> verify <test-id>` sau thay đổi.
   - Red khác `expectedRed`, hoặc vẫn đỏ sau hai lần sửa → `mattpocock-skills:diagnosing-bugs`, dùng chính lệnh `tdd.py` làm vòng phản hồi.

   `tdd.py` giữ bằng chứng; `state.py set` / `push` không ghi được field `tdd`.
3. Test đỏ ngoài slice → `reference/rules.md` → *Check máy*, mục *Test đỏ ngoài ticket*.
4. Cần migration → `uv run python manage.py makemigrations <app>`, đọc lại file sinh ra; migration phải đảo ngược được (`docs/architecture/12-testing-strategy.md` mục 6).
5. **Lint một lượt**: `make fmt`, rồi `make lint` với `--keep-going` (`reference/rules.md` → *Check máy*); sửa mọi lỗi đã in rồi mới chạy lại. Xong khi lint xanh và test của slice xanh.
6. Commit cả slice: `python3 S/scripts/commit.py <T> --task <id> -m "<subject>" --body "<vì sao>" -- <file>…` (`templates/commit-msg.md`). Script từ chối file ngoài `slice.files`: file phát sinh hợp lệ thì cập nhật state và sinh lại plan trước. Sửa thêm trong slice trước khi trả về → `git commit --amend --no-edit` (chưa push nên an toàn).
7. `state.py set <T> slices.<id>.status=done 'slices.<id>.tests=[…]' 'slices.<id>.handoff=[…]' 'next=…'`; tên test đổi so với kế hoạch thì ghi tên thật.

## Cuối phase

Implementer (lite: phiên chính) chạy trước khi trả về; lint đã xanh ở slice cuối:

```bash
python3 S/scripts/run_logged.py --label test --cwd backend -- make test
python3 S/scripts/check_ac_trace.py <T>
```

Đỏ → sửa trong phạm vi ticket rồi chạy lại; đỏ ngoài phạm vi → *Cần người dùng*. Phiên chính nhận kết quả, giữ id của implementer cho vòng sửa ở phase 4, rồi chạy `state.py transition <T> --to report --next "viết báo cáo" --reason "mọi slice xanh"` và in điểm clear.

## Xong khi

Mọi slice `done`; `tddTests` có red/green, `verificationTests` có verified green; `make lint`, `make test`, `check_ac_trace.py` xanh; `commit_map.py <T>` in đúng một commit cho mỗi slice, không `FAIL`; `phase` là `report`.
