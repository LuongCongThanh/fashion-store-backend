# Báo cáo

### Báo cáo 03/11/2026

**Nhánh:** `refactor/outbox-delivery-lifecycle` · **PR:** #62 · **Mode:** lite

#### Đã làm

| AC | Bằng chứng |
| --- | --- |
| 1. Chỉ `shared/events/models.py` ghi cột vòng đời của `EventDelivery` hoặc truyền `update_fields` | `shared/events/tests/test_models.py`: `test_new_delivery_is_due_immediately`, `test_start_run_counts_interrupted_run`, `test_start_run_fails_at_interrupted_threshold`, `test_complete_resets_interrupted_runs`, `test_reject_records_error_and_resets_interrupted_runs`, `test_retry_or_fail_schedules_next_retry`, `test_retry_or_fail_fails_after_last_retry`, `test_fail_keeps_attempts_and_interrupted_runs`, `test_reopen_resets_failed_delivery`, `test_mark_dispatched_sets_dispatch_deadline`. Kiểm thêm bằng `rg` trên `shared/`, `modules/`: chỉ còn marker `deliveries_created_at` của `OutboxEvent` trong `relay.create_deliveries` (để sau, xem *Gap*) |
| 2. Vị từ tới hạn / đã lập danh sách / chưa kết thúc chỉ ở `models.py`, có test trực tiếp | `shared/events/tests/test_models.py`: `test_is_due_requires_pending_and_attempt_time`, `test_attempt_due_ignores_dispatch_deadline`, `test_dispatch_due_requires_dispatch_deadline`, `test_unfinished_excludes_completed_and_rejected`, `test_listed_and_unlisted_split_on_marker` |
| 3. `make lint`, `make test` xanh; test cũ chỉ đổi import | 27 test hành vi cũ đã verify xanh, gồm: `test_consumer.py`: retry, reject, failed, lỗi parse, chạy dở, giao trùng; `test_relay.py`: lập danh sách, giao lại; `test_retry_failed_events.py`; `test_purge.py`; `test_replay_events.py`; `test_selectors.py`; `test_drain.py`. Diff 4 file test cũ chỉ đổi dòng `import` |

`make lint` xanh: ruff, mypy 149 file, `lint-imports` 9 contract, OpenAPI không lệch. `make test`: 398 passed trong 14,1s. Branch coverage nhóm `shared` 86/88 (97,73%), đạt cổng. `makemigrations --check` không có thay đổi.

#### Chưa làm

- Không

#### Gap

- Marker `deliveries_created_at` vẫn ghi bằng `.update()` trong `relay.create_deliveries`. Việc này đã ghi vào `.scratch/backlog.md` (`OutboxEvent.mark_listed`) để làm cùng ticket 28 (B5).
- Test cũ ở `test_consumer.py`, `test_relay.py` và `test_selectors.py` còn kiểm lại lịch retry, ngưỡng chạy dở và vị từ tới hạn, trùng với test mới ở `test_models.py`. Ticket 29 sẽ rút gọn.
- Log `event_delivery_failed` giờ chạy sau `save` thay vì trước, vẫn trong cùng transaction. Tên log và trường log không đổi (đã chốt khi grilling, Q3).

#### Thay đổi theo yêu cầu

- Mang các thay đổi chưa commit của đợt review kiến trúc `shared/events` sang nhánh này, commit cùng `plan`: spec 25, 26, 28, ticket 29 mới, `map.md`, `GLOSSARY.md`.

#### Review

Ba trục chạy ngày 03/11/2026. Trục Bug không có finding: đã so từng hunk với `origin/dev`, gồm `update_fields`, guard khoá, ngưỡng chạy dở và ngữ nghĩa vị từ. Trục Spec xác nhận AC1–3 đạt.

| Mã | `file:line` | Kết luận | Lý do |
| --- | --- | --- | --- |
| P3 | `shared/events/tests/test_models.py:262` | đã sửa (R1) | Test `dispatch_due` thêm delivery `failed` tới hạn, khẳng định điều kiện `pending` |
| S7 | `shared/events/models.py:203` | đã sửa (R1) | Bỏ trích dẫn "07 mục 1.3" sai |
| S6 | `shared/events/consumer.py:119` | đã sửa (R1) | Đổi `_retry_or_fail` thành `_record_handler_error` vì helper có log |
| S5 | `shared/events/models.py:268` | đã sửa (R1) | Tách `_mark_failed` dùng chung cho `retry_or_fail` và `_fail` |
| S1 | `docs/architecture/02-backend-structure.md:189,195` | đã sửa (sync) | Mô tả `consumer.py` / `models.py` cũ |
| P2 | `spec.md` dòng *Thứ tự log* | đã sửa (sync) | Thêm `event_retry_scheduled` (cũng chạy sau `save`) |
| S2 | `shared/events/models.py:211-233` | đã sửa (sync) | Ghi vào 13 mục 7.1: thao tác hàng loạt có side effect là classmethod của model |
| S3, S4 | `shared/events/relay.py:25`, `models.py:227` | chỉ báo | Middle Man nhẹ, spec giữ có chủ đích |
| P4 | commit `2f115b1` | bác | Đã ghi ở *Thay đổi theo yêu cầu* |

Sau R1: `make fmt`, `make lint` xanh; `make test` 398 passed, branch coverage `shared` 86/88 (97,73%); `check_ac_trace.py` OK.

#### Commit

| Task | Phase | AC | Commit | File |
| --- | --- | --- | --- | --- |
| plan | 1 grill | — | `2f115b1` docs: plan outbox delivery lifecycle ticket | 8 |
| S1 | 2 code | 1, 2, 3 | `0acc13b` refactor(events): move delivery lifecycle and outbox predicates into models | 10 |
| R1 | 4 review | — | `412284f` fix(events): address review findings on delivery lifecycle | 3 |

#### Tài liệu đã cập nhật

- `docs/architecture/02-backend-structure.md`: mô tả `models.py` (method vòng đời, QuerySet primitive), `consumer.py` (gọi method model, log theo kết quả), `relay.build_deliveries` (qua `EventDelivery.new`). Review S1.
- `docs/architecture/13-python-django-coding-style.md` mục 7.1: chuyển trạng thái hàng loạt là `@classmethod` của model, không phải method `QuerySet`. Review S2.
- `spec.md` `## Quyết định`: dòng *Thứ tự log* thêm `event_retry_scheduled` (review P2); dòng *lưu kết quả* ghi tên helper `_record_handler_error` (review S6).
- `GLOSSARY.md` ("Event delivery", "Lập danh sách delivery") đã cập nhật trong commit `plan`; không có thuật ngữ hay ADR mới.

#### Ghi chú cho retro

- `check_ac_trace.py --planned` chấp nhận `verificationTests` ghi theo file (`shared/events/tests/test_x.py`), nhưng bản kiểm cuối chỉ nhận id cấp hàm. Phải mở lại slice đã `done` để thay 8 id file bằng 27 id hàm. Bằng chứng: `slices.S1.verificationTests` trong state.
- `expectedRed` cấm `AttributeError`, nên với method mới phải khai chữ ký raise `NotImplementedError` trước, rồi mới red được. Cách này nên ghi vào `phases/2-code.md`.
