# Báo cáo 03/11/2026

**Nhánh:** `test/pytest-markers-and-br-report` · **PR:** chưa mở · **Mode:** lite

#### Đã làm

| AC | Bằng chứng |
| --- | --- |
| 1. Test dùng marker chưa khai báo thì pytest báo lỗi | `tests/test_pytest_markers.py::test_strict_markers_rejects_undeclared` |
| 2. `pytest -m concurrency` và `pytest -m flow` chỉ chạy đúng nhóm test đó | `tests/test_pytest_markers.py::test_marker_filtering_concurrency_and_flow` |
| 3. `make br-report` in đúng danh sách mã `BR-xxx` chưa có test và luôn thoát với mã 0 | `tests/test_pytest_markers.py::test_br_report_outputs_untested_codes_and_exits_zero` |

`make lint` xanh · `make test`: 367 passed trong 15.43s (shared: 81/84 branches, 96.43%; identity: 6/6 branches, 100.00%)

#### Chưa làm

- Không

#### Gap

- Không

#### Thay đổi theo yêu cầu

- Không

#### Review

- Không có finding nào sau khi review đủ 3 trục Spec, Standards và Bug.

#### Commit

| Task | Phase | AC | Commit | File |
| --- | --- | --- | --- | --- |
| plan | 1 grill | — | `e0398f2` docs: plan pytest markers and br-report ticket | 2 |
| S1 | 2 code | 1, 2, 3 | `3415747` feat(backend): declare pytest markers and add br-report command | 4 |

#### Tài liệu đã cập nhật

- `docs/architecture/08-local-development.md`: thêm lệnh `make br-report` vào bảng lệnh Makefile mục 3

#### Ghi chú cho retro

- Không
