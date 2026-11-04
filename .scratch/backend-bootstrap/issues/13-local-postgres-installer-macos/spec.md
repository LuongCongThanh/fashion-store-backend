# 13 – Bộ cài PostgreSQL local cho macOS

Status: ready-for-human · Ưu tiên: 20 · Blocked by: — · **PR:**

Spec: [spec.md](../../spec.md)

## Mục tiêu
Dev dùng Mac chạy `scripts/setup/postgres.sh` là có PostgreSQL local dùng được từ máy và từ container. Tách từ ticket [08](../08-local-postgres-installer/spec.md) (phần Windows/WSL2 làm ở đó; script làm gì: xem 08). Cần người có máy Mac.

## Việc cần làm
- [ ] Chạy `scripts/setup/postgres.sh` trên macOS (Apple Silicon) có Homebrew, hai lần để chắc chạy lại vẫn an toàn.
- [ ] Thử trường hợp đã có cluster bản cũ giữ cổng 5432.
- [ ] Xác minh container trong Docker Desktop (hoặc OrbStack) gọi được `host.docker.internal:<PG_PORT>`. Nếu không được: ghi cách sửa (`listen_addresses`, `pg_hba.conf`) vào [08 mục 2.2](../../../../docs/architecture/08-local-development.md) và sửa script.
- [ ] Gỡ nhãn **[Cần xác minh]** phần macOS trong 08.

## Quyết định
- Không chặn M0; làm khi team có người dùng Mac. Trước đó phần macOS trong 08 giữ nhãn **[Cần xác minh]**.

## Acceptance criteria
- [ ] Script chạy xong trên macOS; lần thứ hai không lỗi và không đổi gì.
- [ ] Máy có sẵn cluster cũ ở 5432: cluster cũ giữ nguyên, cluster mới chạy cổng khác, `DATABASE_URL` in ra đúng cổng.
- [ ] `psql postgres://fashion:fashion@localhost:<PG_PORT>/fashion` vào được.
- [ ] Từ container vào được: `docker run --rm postgres psql postgres://fashion:fashion@host.docker.internal:<PG_PORT>/fashion -c 'select 1'`.
- [ ] 08 không còn nhãn **[Cần xác minh]** về kết nối PostgreSQL trên macOS.
