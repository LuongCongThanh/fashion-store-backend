import copy
from types import SimpleNamespace
from typing import Any

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from psycopg import errors, sql

from shared.management.commands import reset_db

# Ghi đè DATABASES là cố ý: trỏ lệnh tới DB không tồn tại để không chạm database thật
pytestmark = pytest.mark.filterwarnings("ignore:Overriding setting DATABASES")


def _databases(host: str) -> dict[str, Any]:
    # Port 1 không có PostgreSQL: lệnh bỏ qua kiểm tra mà nối DB thì lỗi kết nối, không phải
    # CommandError, nên test đỏ mà không chạm vào database thật
    databases = copy.deepcopy(settings.DATABASES)
    databases["default"].update(HOST=host, PORT="1", NAME="reset_db_guard")
    return databases


def test_refuses_when_debug_is_off() -> None:
    with (
        override_settings(DEBUG=False, DATABASES=_databases("localhost")),
        pytest.raises(CommandError, match="DEBUG"),
    ):
        call_command("reset_db")


@pytest.mark.parametrize("host", ["db.example.com", "fashion.abc123.rds.amazonaws.com", ""])
def test_refuses_non_local_database_host(host: str) -> None:
    with (
        override_settings(DEBUG=True, DATABASES=_databases(host)),
        pytest.raises(CommandError, match="localhost"),
    ):
        call_command("reset_db")


class _FakeConnection:
    """Thay psycopg.connect: trả địa chỉ server cho trước, ghi lại lệnh DROP/CREATE đã chạy."""

    def __init__(self, server_addr: str | None, drop_error: Exception | None = None) -> None:
        self.server_addr = server_addr
        self.drop_error = drop_error
        self.statements: list[sql.Composed] = []

    def __enter__(self) -> _FakeConnection:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def execute(self, query: str | sql.Composed) -> Any:
        if isinstance(query, str):
            return SimpleNamespace(fetchone=lambda: (self.server_addr,))
        if self.drop_error is not None and not self.statements:
            raise self.drop_error
        self.statements.append(query)
        return None


def _patch_connect(monkeypatch: pytest.MonkeyPatch, conn: _FakeConnection) -> None:
    monkeypatch.setattr(reset_db.psycopg, "connect", lambda **kwargs: conn)


@pytest.mark.parametrize(("host", "server_addr"), [("::1", "::1"), ("localhost", None)])
def test_drops_and_recreates_local_database(
    monkeypatch: pytest.MonkeyPatch, host: str, server_addr: str | None
) -> None:
    conn = _FakeConnection(server_addr)
    _patch_connect(monkeypatch, conn)

    with override_settings(DEBUG=True, DATABASES=_databases(host)):
        call_command("reset_db")

    assert [type(s) for s in conn.statements] == [sql.Composed, sql.Composed]
    drop, create = (repr(s) for s in conn.statements)
    assert "DROP DATABASE" in drop
    assert "reset_db_guard" in drop
    assert "CREATE DATABASE" in create


def test_refuses_when_server_behind_localhost_is_remote(monkeypatch: pytest.MonkeyPatch) -> None:
    # SSH tunnel tới RDS: client nối localhost nhưng server nghe ở địa chỉ trong VPC
    conn = _FakeConnection("10.0.3.17")
    _patch_connect(monkeypatch, conn)

    with (
        override_settings(DEBUG=True, DATABASES=_databases("localhost")),
        pytest.raises(CommandError, match="tunnel"),
    ):
        call_command("reset_db")

    assert conn.statements == []


def test_connection_of_other_role_gives_actionable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = _FakeConnection("127.0.0.1", errors.InsufficientPrivilege("permission denied"))
    _patch_connect(monkeypatch, conn)

    with (
        override_settings(DEBUG=True, DATABASES=_databases("localhost")),
        pytest.raises(CommandError, match="pgAdmin"),
    ):
        call_command("reset_db")

    assert conn.statements == []
