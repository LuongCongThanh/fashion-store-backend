# State

`.git/ship-ticket-fashion/<feature>-<NN>.json`, tạo ở phase 1 bằng `state.py init`. Đọc file này ở phase 1 và khi ghi một field lần đầu.

```json
{
  "ticket": ".scratch/backend-bootstrap/issues/16-shared-api-layer",
  "feature": "backend-bootstrap", "num": 16,
  "branch": "feat/shared-api-layer", "mode": "full",
  "phase": "code", "next": "S2: viết test 404 trả ErrorDTO rồi exception_handler",
  "gates": { "g1": "2026-10-29", "g2": null },
  "slices": [
    { "id": "S1", "acs": [4], "dependsOn": [], "status": "done",
      "seam": "GET list endpoint qua APIClient",
      "tests": ["tests/shared/api/test_pagination.py::test_page_size_capped_at_100"],
      "tddTests": ["tests/shared/api/test_pagination.py::test_page_size_capped_at_100"],
      "verificationTests": [],
      "expectedRed": {"tests/shared/api/test_pagination.py::test_page_size_capped_at_100": "AssertionError"},
      "files": ["backend/shared/api/pagination.py"],
      "governingDocs": {"backend/shared/api/pagination.py": ["docs/architecture/13-python-django-coding-style.md::3.1"]},
      "tdd": {"tests/shared/api/test_pagination.py::test_page_size_capped_at_100":
        {"redAt": "2026-10-29T10:10:00+07:00", "redReason": "FAILED …", "greenAt": "2026-10-29T10:20:00+07:00"}},
      "handoff": ["StandardPagination trong shared/api/pagination.py"] },
    { "id": "S2", "acs": [1], "dependsOn": ["S1"], "status": "code", "seam": "service result",
      "tests": ["modules/x/tests/test_services_x.py::test_x"], "tddTests": [],
      "verificationTests": ["modules/x/tests/test_services_x.py::test_x"], "expectedRed": {},
      "files": ["backend/modules/x/services/x.py"],
      "governingDocs": {"backend/modules/x/services/x.py": ["docs/architecture/13-python-django-coding-style.md::4"]},
      "tdd": {} }
  ],
  "currentSlice": "S2",
  "untestable": { "3": "cần Redis thật; kiểm tay bằng make up rồi tắt redis" },
  "userRequested": [{ "date": "2026-10-29", "request": "…" }],
  "notes": {},
  "pr": null,
  "transitions": [{ "from": "grill", "to": "code", "at": "2026-10-29T10:00:00", "reason": "G1 approved" }]
}
```

- `acs`: số thứ tự của AC trong mục `## Acceptance criteria` của `spec.md`, đếm từ 1.
- `tests`: hợp không trùng của `tddTests` và `verificationTests`; id pytest tính từ `backend/`.
- `tddTests`: test mới cho hành vi, cần `expectedRed`, red rồi green. `verificationTests`: test sẵn có chỉ cần verify green.
- `files`: file slice sẽ đổi, ghi ở phase 1 cho `plan.md`; một slice là một commit gồm đúng các file này.
- `governingDocs`: mỗi key là file trong `files`, value là reference `path.md::số-mục`; script kiểm file và heading tồn tại, đồng thời reference phải xuất hiện trong `## Quyết định`.
- `tdd`: chỉ `tdd.py` ghi. `tddTests` cần `redAt` + `greenAt`; `verificationTests` cần `verifiedAt` trước khi slice `done`.
- `notes`: ghi chú tự do theo khoá. `notes.baselineRed`: list id test đỏ sẵn trên `origin/dev`, ghi ở phase 1 từ log baseline.
- `untestable`: AC không test tự động được ở đây, kèm lý do và cách kiểm tay; báo cáo liệt kê chúng ở mục *Chưa làm*.
- `status` của slice: `todo` → `code` → `done`. Slice phụ thuộc nhau tạo thành DAG; `state.py check` từ chối id trùng, `dependsOn` không tồn tại và vòng lặp.
- `handoff`: tối đa 5 dòng mỗi slice, chỉ những gì slice sau dùng lại (tên export, quyết định). Không ghi nhật ký làm việc.
- `next`: đúng một việc cụ thể tiếp theo, viết lại sau mỗi bước.
- `phase`: `grill | code | report | review | sync | ship | done | retro | closed`.
- `pr`: số PR, ghi ở phase 6.
- `phase`, `transitions`, `gates`: chỉ `state.py transition` ghi; `set` / `push` từ chối các field này. `--gate g1` chỉ dùng ở `grill → code`, `--gate g2` chỉ ở `sync → ship`.
- Sau merge, `done → closed` khi chưa đủ đợt retro; đủ đợt thì `done → retro → closed`. Chờ merge giữ `done`. Bộ đếm dùng lịch sử `origin/dev` và `reference/retro-batch.json`, độc lập state từng ticket.

Lệnh:

```bash
python3 S/scripts/state.py init <T> --branch <nhánh> --mode lite|full
python3 S/scripts/state.py set <T> mode=lite slices.S1.status=code 'next=S1: chạy test red' currentSlice=S1
# Push một object đầy đủ theo schema S1/S2 ở trên; state.py từ chối field thiếu.
python3 S/scripts/state.py check <T>
```

Giá trị parse được thành JSON thì lưu dạng JSON (`[4]`, `null`, `true`), ngược lại lưu chuỗi. Đường dẫn `slices.S1.x` chọn slice theo `id`. `push` thêm từng phần tử của list vào cuối field list.
