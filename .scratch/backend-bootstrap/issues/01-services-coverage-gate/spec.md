# Chặn branch coverage dưới 80% cho `services` và `handlers` của từng module trong CI

Status: ready-for-agent

Blocked by: 07

Spec: [spec.md](../../spec.md)

## Việc cần làm

- `coverage` và `pytest-cov` đã có trong dependency dev. Đặt `[tool.coverage.run] branch = true` trong `pyproject.toml`; giữ dependency và lockfile hiện tại.
- Chạy test bằng `pytest -n auto --cov=modules --cov=shared --cov-report=`. `pytest-cov` gom dữ liệu coverage từ các worker của `pytest-xdist`.
- Thêm `scripts/check_module_coverage.py` và gọi sau test trong cả `make test` lẫn job `backend` của `.github/workflows/ci.yml`:

  ```bash
  python scripts/check_module_coverage.py
  ```

- Đo số nhánh riêng bằng API public `Coverage.branch_stats(file)`, cộng theo từng nhóm và chặn dưới 80%; không dùng tỷ lệ tổng dòng + nhánh của `coverage report --fail-under`.
- Target mỗi module: `modules/<module>/services/**/*.py`, `modules/<module>/handlers.py`. Target `shared` theo 12 mục 8: `shared/events/**/*.py` (bỏ test), `shared/idempotency.py`, `shared/api/idempotency.py`, `shared/tasks.py`. Module chưa có target được bỏ qua; target không có nhánh ghi rõ không có nhánh. File chưa được chạy vẫn phải được phân tích. Thiếu dữ liệu hoặc chỉ có statement coverage phải báo lỗi.
- Không đặt `fail_under` trong `pyproject.toml` và không áp ngưỡng toàn repo. Cập nhật cách chạy trong 12 mục 8 và 08 mục 3/5; bổ sung script vào cây 02 mục 2.

## Quyết định

Chốt khi grilling ngày 01/11/2026. Người dùng duyệt G1: mode full, hai slice, đo branch riêng cho từng module và nhóm shared; dùng API coverage có sẵn, không đổi code nghiệp vụ hoặc thêm dependency.

| Chủ đề | Quyết định |
| --- | --- |
| Tài liệu chi phối | Script, cấu hình, workflow → 12 §8 (ngưỡng và phạm vi), 02 §2 (cây thư mục); test → 02 §9.5, 12 §1/§8; lệnh local → 08 §3/§5; tên nhánh/commit/PR → 11 §2. Không đổi code trong `backend/shared/` |
| Mode | full vì có 5 AC; hai slice, mỗi slice một commit |
| Sửa cách đo | `coverage report --fail-under` hiện ghi trong 12 §8 kiểm tỷ lệ gộp dòng và nhánh; thay bằng branch riêng để giữ đúng yêu cầu đã chốt. Nguồn: [coverage branch measurement](https://coverage.readthedocs.io/en/latest/branch.html), API public [branch_stats](https://coverage.readthedocs.io/en/latest/api_coverage.html#coverage.Coverage.branch_stats). Đồng bộ tài liệu cùng PR |
| Phạm vi | Mỗi module kiểm gộp `services/` + `handlers.py` của chính nó; hạ tầng `shared` là nhóm riêng theo 12 §8, loại test khỏi mẫu số. File ngoài target không ảnh hưởng gate |
| Target idempotency | Nhóm `shared` gồm cả lõi `shared/idempotency.py` (claim, lease, `LeaseLost`, purge; 02 dòng 182) cạnh lớp HTTP `shared/api/idempotency.py`. 12 §8 viết ngày 29/10, trước khi PR #40 (30/10) tách lõi ra khỏi lớp HTTP, nên chỉ nêu file HTTP và bỏ sót lõi. Người dùng duyệt ở review ngày 01/11/2026; sửa 12 §8 cùng PR |
| Ngưỡng | So số nguyên `covered * 100 >= total * 80`, tránh làm tròn 79.x thành 80; nhóm không có nhánh được báo rõ và qua; module chưa có target được bỏ qua |
| Interface / seam | Script hạ tầng dùng lại `coverage.Coverage.load`, `get_data().has_arcs`, `branch_stats`; CLI đọc `.coverage`, in số nhánh từng nhóm và exit code. Không thêm interface nghiệp vụ, adapter hoặc dependency |
| Test | Dữ liệu coverage thật trong package tạm, không mock API coverage. Subprocess pytest cô lập plugin/config/env; serial và `-n auto` dùng data file riêng, giới hạn auto 2 worker trong fixture; so cả số nhánh và exit code |
| Baseline | `manage.py check --database default` xanh; 327 test chạy xdist + coverage branch qua trong 14.49s. Nhóm identity 6/6 nhánh (100%); shared theo target đề xuất 67/68 (98.53%). Log local `.git/ship-ticket-fashion/logs/module-coverage-baseline.log` và JSON cùng tên; baseline không phải bằng chứng đã triển khai gate |

## Acceptance criteria

- [ ] PR có branch coverage dưới 80% ở nhóm `services/` + `handlers.py` của bất kỳ module nào, hoặc nhóm hạ tầng `shared` theo 12 mục 8, thì bị CI chặn.
- [ ] Module A đạt 100% không giúp module B đạt 60% qua cổng.
- [ ] Module chưa có `services/` và `handlers.py` không làm bước này lỗi.
- [ ] Coverage đo đúng khi chạy song song bằng `pytest -n auto` (kết quả bằng khi chạy tuần tự).
- [ ] Không có ngưỡng coverage cho toàn repo.
