# Báo cáo

### Báo cáo 03/11/2026

**Nhánh:** `feat/trusted-bff-request-id` · **PR:** chưa mở · **Mode:** lite

#### Đã làm

| AC | Bằng chứng |
| --- | --- |
| 1. Secret BFF đúng và `X-Request-ID` hợp lệ thì `error.request_id` và log dùng giá trị đó | `shared/tests/test_api_request_id.py::test_trusted_request_id_is_used_in_error_and_logs` (ULID và biên 64 ký tự). Sai định dạng / quá dài giữ id tự sinh, log `request_id_invalid` kèm `reason`: `shared/tests/test_api_request_id.py::test_malformed_request_id_is_replaced_and_logged_with_reason`; không lộ giá trị header hay secret trên mọi dòng log: `shared/tests/test_api_request_id.py::test_malformed_request_id_value_and_secret_are_not_logged`; thiếu hoặc rỗng header thì không cảnh báo: `shared/tests/test_api_request_id.py::test_missing_or_empty_request_id_keeps_generated_id_without_warning` |
| 2. Thiếu hoặc sai secret thì `request_id` tự sinh, bỏ qua header | `shared/tests/test_api_request_id.py::test_request_id_header_ignored_when_bff_secret_missing`, `shared/tests/test_api_request_id.py::test_request_id_header_ignored_when_bff_secret_wrong` (kể cả header sai định dạng: không cảnh báo). Đổi tên hàm so secret không đổi `client_ip`: `shared/tests/test_api_client_ip.py::test_wrong_secret_uses_remote_addr`, `shared/tests/test_api_client_ip.py::test_valid_secret_uses_x_client_ip` |

`make lint` xanh · `make test`: 383 passed trong 11.74s, branch coverage `shared` 81/84 (96.43%) · chạy tuần tự không xdist (`pytest -p no:xdist`): 383 passed

#### Chưa làm

- Không trả header `X-Request-ID` trong response: tài liệu không yêu cầu (G1), đã ghi `.scratch/backlog.md`.

#### Gap

- Django chỉ chứng minh request đi qua BFF; việc BFF bỏ `X-Request-ID` của browser và tự sinh mới là hợp đồng phía Next.js (05 §1.1, đã ghi), cần kiểm khi bootstrap frontend cùng test toàn đường browser → BFF → Django (05 §5).

#### Thay đổi theo yêu cầu

- Không

#### Review

| Mã | Chỗ | Kết luận | Lý do |
| --- | --- | --- | --- |
| B1, B2, S1, P3 | `shared/tests/test_api_request_id.py` | đã sửa | Test phụ thuộc thứ tự (`json_logging` gọi `reset_defaults()`), trái 12 §4; chuyển sang `json_logging` + `capsys` |
| B5, S2, P3 | `shared/tests/test_api_request_id.py` | đã sửa | Thêm biên 64, header thiếu/rỗng, sai secret + header sai định dạng, kiểm lộ dữ liệu trên mọi log |
| B3 | `shared/api/request_id.py:27` | đã sửa | Header rỗng coi như không gửi |
| B8 | `shared/api/request_id.py:30-37` | đã sửa | `reason` `too_long` / `invalid_chars` |
| S6, S7 | `shared/api/request_id.py:20`, `shared/apps.py:14` | đã sửa | Hằng private; `dispatch_uid` |
| B4, S4 | `shared/api/request_id.py:1`, `shared/api/client_ip.py:1` | đã sửa | Docstring nêu đúng giới hạn của secret; 05 §1.1 thêm hợp đồng BFF |
| P2 | `.scratch/backlog.md` | đã sửa | Dòng backlog header response |
| B6 | `shared/api/request_id.py:27` | bác | G1 chốt dùng hàm, không gán cờ; so tối đa 2 secret |
| B7, S3, S5 | | chỉ báo | Tách `bff.py`, gộp parametrize, helper header BFF chung: chờ chỗ dùng thứ ba |

#### Commit

| Task | Phase | AC | Commit | File |
| --- | --- | --- | --- | --- |
| plan | 1 grill | — | `2afe35e` docs: plan trusted BFF request id ticket | 2 |
| S1 | 2 code | 1, 2 | `1ce6a50` feat(shared): trust X-Request-ID only with a valid BFF secret | 4 |
| R1 | 4 review | — | `630c742` fix(shared): address review findings on trusted request id | 4 |
| sync | 5 sync | — | commit này: tài liệu, spec, report, backlog | 8 |

#### Tài liệu đã cập nhật

- `docs/architecture/10-nfr.md` §4: điều kiện tin `X-Request-ID` (secret + định dạng), log `request_id_invalid`, response không trả header.
- `docs/architecture/05-auth-security.md` §1.1: `X-Request-ID` vào danh sách header BFF không chuyển tiếp từ browser, BFF tự sinh.
- `docs/architecture/02-backend-structure.md` §5: dòng `request_id.py`, ghi chú `bff_secret_matches` ở `client_ip.py`.
- `docs/architecture/12-testing-strategy.md` §4: gọi `dictConfig(json_logging)` trong thân test để `capsys` bắt được.
- `spec.md` của ticket: `## Quyết định` khớp code sau review.

#### Ghi chú cho retro

- Bỏ sót 12 §4 (fixture `json_logging`) ở phase 1 nên dùng `capture_logs` rồi `caplog`, chẩn đoán sai nguyên nhân (`cache_logger_on_first_use`) và chỉ trục Bug bắt được (`pytest shared/tests/test_logging.py shared/tests/test_api_request_id.py` đỏ 6 test trước R1, commit `R1`) → gợi ý: phase 1 bước 3 tra 12 theo chủ đề (log, fixture), không chỉ mục loại test; chạy thêm `pytest -p no:xdist` khi test đọc log.
- `check_ac_trace.py` không nhận test id ở mức file; test thêm ở vòng review không ghi được vào `tdd` (tdd.py chỉ chạy ở phase code) → bằng chứng nằm ở commit `R1`; gợi ý: `state.py check` phase 1 từ chối id không có `::`, và tdd.py nhận task `R<n>`.
