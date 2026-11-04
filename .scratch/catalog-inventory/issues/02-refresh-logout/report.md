# Báo cáo

### Báo cáo 04/11/2026

**Nhánh:** `feat/backoffice-refresh-logout` · **PR:** chưa mở · **Mode:** full

#### Đã làm

| AC | Bằng chứng |
| --- | --- |
| 1. Refresh lần đầu cấp cặp mới cùng family, đánh dấu predecessor cùng transaction | `apps/identity/tests/test_services_refresh.py::test_first_refresh_issues_successor_and_marks_parent` |
| 2. Hai refresh đồng thời một successor; retry 10 giây trả đúng cặp, không gia hạn | `apps/identity/tests/test_concurrency_refresh.py::test_concurrent_refresh_creates_one_successor`, `apps/identity/tests/test_services_refresh.py::test_retry_inside_window_returns_same_pair_without_extending` |
| 3. 409 `REFRESH_SUPERSEDED`, reuse ngoài cửa sổ thu hồi family, từ chối family thu hồi/Tài khoản vô hiệu/lệch `tv`, 503 `REFRESH_REPLAY_UNAVAILABLE` | `apps/identity/tests/test_services_refresh.py::test_retry_after_successor_used_raises_superseded`, `::test_reuse_outside_window_revokes_family`, `::test_revoked_family_is_rejected`, `::test_inactive_account_or_stale_token_version_is_rejected`, `::test_missing_replay_inside_window_raises_unavailable`, `::test_missing_key_on_first_refresh_issues_nothing`, `apps/identity/tests/test_models_auth.py::test_revoke_family_revokes_only_that_family` |
| 4. Logout thu hồi family, xoá replay, 204 idempotent, không cần access token | `apps/identity/tests/test_services_refresh.py::test_logout_revokes_family_and_deletes_replay`, `::test_logout_is_idempotent_and_accepts_expired_token`, `apps/identity/tests/test_api_backoffice_logout.py::test_logout_returns_204_without_access_token`, `::test_logout_rejects_wrong_audience` |
| 5. AESGCM khoá riêng: khoá khác/AAD sai/ciphertext sửa không giải mã được; cấu hình sai bị từ chối; deploy check | `apps/identity/tests/test_auth_replay_crypto.py` (5 test), `tests/test_env.py::test_refresh_replay_key_reads_32_byte_file`, `::test_refresh_replay_key_rejects_wrong_length_without_leaking`, `shared/tests/test_checks.py::test_deploy_check_requires_refresh_replay_key` |
| 6. API/OpenAPI refresh/logout đúng hợp đồng, log và lỗi không lộ token | `apps/identity/tests/test_api_backoffice_refresh.py` (5 test, gồm `::test_refresh_logs_and_errors_hide_tokens`), `apps/identity/tests/test_api_backoffice_me.py::test_refresh_and_logout_document_declared_errors` |
| 7. Job `identity.purge_refresh_replays` mỗi phút | `apps/identity/tests/test_tasks_purge_refresh_replays.py::test_purge_deletes_only_expired_replays`, `shared/tests/test_sync_beat_schedule.py::test_beat_schedule_includes_identity_purge_refresh_replays` |
| 8. `TokenPairDTO` chỉ còn field output; `decode_access_token` bắt buộc `now` | `apps/identity/tests/test_services_tokens.py::test_token_pair_dto_has_only_output_fields`, `::test_issue_token_pair_keeps_given_family`, `::test_decode_refresh_token_*` (3 test) |

`make lint` xanh (gồm `gen_openapi.py --check`) · `make test`: 576 passed trong 14,45s, branch coverage `identity` 22/22 (100%), `shared` 85/88 (96,59%)

#### Chưa làm

- Không

#### Gap

- `IssuedTokenPair` giữ field phẳng và thêm property `.pair` trả `TokenPairDTO`, để helper test (`conftest._backoffice_client`) không phải đổi.
- Lỗi refresh/logout là `DomainError` (`RefreshRejected` 401 `NOT_AUTHENTICATED`, `RefreshExpired` 401 `TOKEN_EXPIRED`, `RefreshSuperseded` 409, `RefreshReplayUnavailable` 503, `SessionStateUnavailable` 503 `AUTH_STATE_UNAVAILABLE`), không phải `AuthenticationFailed`. Lý do: với `authentication_classes = ()`, DRF đổi `AuthenticationFailed` thành 403.
- Khoá replay: `.env.example` dùng giá trị của 08; thiếu một trong hai biến, file không tồn tại hay file khác 32 byte đều bị từ chối lúc khởi động; bỏ trống cả hai nghĩa là không có khoá. 08 §2.3 chưa ghi rõ là dev/test được phép bỏ trống cả hai (sync ở phase 5).
- Job purge mới kiểm qua gọi task trực tiếp và test beat schedule, chưa chạy trên beat thật.

#### Thay đổi theo yêu cầu

- 04/11/2026: thêm job `identity.purge_refresh_replays` (AC7).
- 04/11/2026: tách `TokenPairDTO` và bắt buộc `now` khi decode (AC8, việc trong backlog của ticket 01).

#### Review

Chưa review.

#### Commit

| Task | Phase | AC | Commit | File |
| --- | --- | --- | --- | --- |
| plan | 1 grill | — | `c26b1df` docs: plan backoffice refresh and logout ticket | 2 |
| S1 | 2 code | 8 | `61e688d` refactor(identity): split issued token pair from output dto and add refresh decode | 4 |
| S2 | 2 code | 5 | `0b31c5f` feat(identity): add aesgcm replay key and encryption for refresh replay | 8 |
| S3 | 2 code | 1, 2, 3 | `6a9bc08` feat(identity): rotate refresh tokens with a single successor and encrypted replay | 7 |
| S4 | 2 code | 4, 6 | `c4368ab` feat(identity): add back-office refresh and logout endpoints | 11 |
| S5 | 2 code | 7 | `e37c45f` feat(identity): purge expired refresh replays every minute | 5 |

#### Tài liệu đã cập nhật

- `docs/architecture/04-api-contract.md`: thêm mã lỗi `REFRESH_REPLAY_UNAVAILABLE` (S4).

#### Ghi chú cho retro

- Red của test API cho route chưa có bị `tdd.py` từ chối vì log "Not Found:", implementer phải gắn view stub 501 trước → state `notes.phase2Drift`; gợi ý: ghi mẹo này vào `phases/2-code.md`.
- expectedRed lập ở phase 1 là `AssertionError` cho function chưa tồn tại, thực tế red là `NotImplementedError` từ stub → state `notes.phase2Drift`; gợi ý: phase 1 cho phép `NotImplementedError` của stub.
