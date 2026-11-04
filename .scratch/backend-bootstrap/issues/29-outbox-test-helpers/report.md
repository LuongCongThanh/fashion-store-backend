# Báo cáo

### Báo cáo 04/11/2026

**Nhánh:** `refactor/outbox-test-helpers` · **PR:** #64 · **Mode:** lite

#### Đã làm

| AC | Bằng chứng |
| --- | --- |
| 1. Không còn hằng hay helper test khai báo lặp trong `shared/events/tests`; factory mặc định không cần sự kiện mẫu | `shared/events/tests/test_factories.py::test_outbox_event_factory_default_is_neutral`, `::test_factory_traits_build_sample_listed_and_failed`; `shared/tests/test_models.py::test_outbox_models_share_uuid7_primary_key`. Grep `datetime(20`, `^NOW`, `^ORDER_CODE`, `FS2610`, `^class`, `Barrier`, `_listed_event`, `_failed(`, `_register(` trong `shared/events/tests/`: chỉ còn ở `_helpers.py`; helper còn lại (`_finished`, `_reloaded`, `_handlers_of`, `_register_recorder`, `_publish_then_fail`) mỗi cái một bản |
| 2. Mỗi quy tắc vòng đời Event delivery chỉ kiểm ở một chỗ | Xoá `test_consumer.py::test_saved_outcome_resets_interrupted_runs` (4 tham số); bỏ assert lịch retry, bộ đếm, cột reset ở `test_consumer.py::test_retry_later_rolls_back_and_keeps_pending`, `::test_exception_rolls_back_handler_and_keeps_pending`, `::test_exhausted_retries_mark_failed`, `::test_validation_error_inside_handler_schedules_retry`, `test_drain.py::test_drain_does_not_wait_for_future_retry`, `test_retry_failed_events.py::test_reopens_failed_and_logs_each_delivery`. Các quy tắc này còn ở `test_models.py` (`test_retry_or_fail_*`, `test_reopen_resets_failed_delivery`, `test_complete_*`, `test_reject_*`) |
| 3. `make lint`, `make test` xanh, cổng coverage `shared` đạt | 93 test verify xanh (danh sách trong `plan.md`) |

`make lint` xanh: ruff, mypy, `lint-imports`, OpenAPI không lệch. `make test`: 397 passed trong 12,1s, ít hơn 1 so với trước (bỏ 4 tham số trùng, thêm 3 test). Branch coverage nhóm `shared` 86/88 (97,73%). `makemigrations --check` không có thay đổi.

#### Chưa làm

- Không

#### Gap

- `ORDER_CODE` có ở `_helpers.py` và trong trait `sample` của `shared/testing/factories.py` (`shared/testing` không import được gói test). `test_factories.py` buộc hai giá trị này khớp nhau.
- `test_replay_events.py::test_replay_and_purge_concurrently_keep_new_delivery` dùng một thread không có `Barrier`, nên không qua `run_concurrently`. Test vẫn gắn marker `concurrency`.
- Trait `listed` đặt `deliveries_created_at = occurred_at`. Ở `test_purge.py::test_purge_respects_retention_boundary`, mốc lập danh sách giờ trùng `occurred_at` thay vì `OLD`. Purge chỉ xét marker khác NULL, nên kết quả không đổi.

#### Thay đổi theo yêu cầu

- Gắn `@pytest.mark.concurrency` cho 4 test nhiều thread (12 mục 2.2): `test_consumer.py::test_concurrent_duplicate_dispatch_commits_once`, `test_relay.py::test_two_relays_concurrently_create_no_duplicates`, `::test_two_relays_concurrently_dispatch_each_delivery_once`, `test_replay_events.py::test_replay_and_purge_concurrently_keep_new_delivery`.

#### Review

Theo yêu cầu người dùng (đi nhanh), review gọn ở phiên chính, không chạy `code-review` và sub-agent trục Bug. Phạm vi soát: 4 file không phải test (`shared/models.py`, `shared/events/models.py`, `shared/testing/factories.py`, `shared/events/tests/_helpers.py`) đối chiếu `## Quyết định`, cùng grep AC1. Check máy: `state.py check`, `check_ac_trace.py` xanh; `make lint` xanh; `make test` 397 passed, branch coverage `shared` 86/88 (97,73%); `makemigrations --check` không có thay đổi.

| Mã | `file:line` | Kết luận | Lý do |
| --- | --- | --- | --- |
| V1 | `shared/events/tests/_helpers.py:13` | chỉ báo | `_helpers.py` và 7 file test import `SampleHappenedV1`/`HandlerEffect` từ `conftest.py`; `## Quyết định` đã chốt giữ hai class này ở `conftest.py` |
| V2 | `f1e987f` | chỉ báo | Commit report thủ công thiếu trailer `Refs:`/`Task:`; xử lý ở G2 |

Không có finding *sửa*; không có vòng sửa.

#### Commit

| Task | Phase | AC | Commit | File |
| --- | --- | --- | --- | --- |
| plan | 1 grill | — | `b05e18e` docs: plan outbox test helpers ticket | 2 |
| S1 | 2 code | 1, 2, 3 | `f2fb738` refactor(events): share outbox test helpers and factory traits | 15 |
| sync | 5 sync | — | docs: sync docs and report for outbox test helpers ticket (amend `f1e987f`) | 3 |

#### Tài liệu đã cập nhật

- `docs/architecture/03-data-model.md` mục quy ước chung: `BaseModel` kế thừa `UUIDv7Model`; outbox kế thừa thẳng `UUIDv7Model`.

#### Ghi chú cho retro

- Helper `record_effect` trùng tên với handler cục bộ `def record_effect(event)` trong `test_consumer.py`. Handler che helper và gây đệ quy, làm 3 test đỏ trước khi đổi tên handler thành `record`. Khi gom helper vào module chung, nên grep tên trùng trước.
- Người dùng commit `report.md` thủ công (`f1e987f`, thiếu trailer) và push trước sync; G2 chọn amend thành task `sync` rồi `--force-with-lease`.
- Người dùng thấy ticket refactor test kéo dài; G2 chọn review gọn ở phiên chính thay vì `code-review` + sub-agent Bug.
- `plan.py` khai `conftest.py` trong `files` dù không cần sửa. `commit.py` từ chối commit cho tới khi bỏ file đó khỏi slice.
