"""Xoá và tạo lại database của máy dev cho `make db-reset` (08 mục 3).

Nối database `postgres` bằng chính role của `DATABASES["default"]`, `DROP DATABASE … WITH
(FORCE)` rồi `CREATE DATABASE … OWNER <role>`; role giữ nguyên. Chỉ chạy khi `DEBUG` bật,
host là `localhost`/`127.0.0.1`/`::1` và chính server xác nhận nó nghe ở loopback, để không xoá
database của staging hoặc production, kể cả khi SSH tunnel/port-forward trình nó ra localhost.
Tunnel tới máy mà PostgreSQL chạy ngay trên đó vẫn lọt kiểm tra này (server cũng thấy loopback).
Migrate và `sync_beat_schedule` do recipe của Makefile gọi sau lệnh này.
"""

import psycopg
import structlog
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from psycopg import errors, sql

logger = structlog.get_logger(__name__)

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
# Địa chỉ server trả về từ inet_server_addr(); None khi nối qua Unix socket
LOOPBACK_SERVER_ADDRS = frozenset({None, "127.0.0.1", "::1"})


class Command(BaseCommand):
    help = "Xoá và tạo lại database của máy dev (chỉ khi DEBUG bật và host là localhost)."

    def handle(self, *args: object, **options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("reset_db chỉ chạy khi DEBUG bật (máy dev)")
        db = settings.DATABASES["default"]
        if db["HOST"] not in LOCAL_HOSTS:
            raise CommandError(
                f"reset_db chỉ chạy với database trên máy (localhost, 127.0.0.1, ::1), "
                f"host đang là {db['HOST']!r}"
            )

        name, owner = db["NAME"], db["USER"]
        # Đóng kết nối Django đang giữ tới database sắp xoá
        connections.close_all()
        with psycopg.connect(
            dbname="postgres",
            host=db["HOST"],
            port=db["PORT"],
            user=owner,
            password=db["PASSWORD"],
            autocommit=True,  # DROP/CREATE DATABASE không chạy được trong transaction
        ) as conn:
            # SSH tunnel, port-forward cũng trình database từ xa ra localhost: hỏi chính server
            row = conn.execute("SELECT host(inet_server_addr())").fetchone()
            server_addr = row[0] if row else None
            if server_addr not in LOOPBACK_SERVER_ADDRS:
                raise CommandError(
                    f"reset_db chỉ chạy với PostgreSQL trên máy, server đang nghe ở "
                    f"{server_addr!r} (SSH tunnel hoặc port-forward?)"
                )
            try:
                conn.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
                )
            except errors.InsufficientPrivilege as exc:
                # FORCE chỉ ngắt được kết nối của chính role; kết nối bằng role khác (thường là
                # postgres) phải đóng tay
                raise CommandError(
                    f"Không ngắt được kết nối của role khác tới {name!r}: đóng pgAdmin, psql "
                    f"hoặc IDE đang nối database này rồi chạy lại"
                ) from exc
            conn.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(name), sql.Identifier(owner)
                )
            )
        logger.info("database_reset", name=name)
