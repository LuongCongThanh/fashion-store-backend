import os
import subprocess
import sys
import traceback

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.env import BASE_DIR, database_config

# Password chèn sai chỗ: netloc rỗng, mọi thứ rơi vào path (lỗi đã gặp thật trên máy dev)
MISPLACED_PASSWORD_URL = "postgres:///top-secret//fashion:fashion@localhost:5432/fashion"


def test_keeps_query_parameters_as_options() -> None:
    config = database_config("postgres://u:p@rds-host:5432/fashion?sslmode=require")

    assert config["OPTIONS"] == {"sslmode": "require"}
    assert config["HOST"] == "rds-host"


def test_allows_url_without_password() -> None:
    config = database_config("postgres://fashion@localhost:5432/fashion")

    assert config["USER"] == "fashion"
    assert config["PASSWORD"] == ""


def test_host_argument_overrides_host_of_url() -> None:
    # Compose chỉ đặt DATABASE_HOST, user và mật khẩu vẫn lấy từ DATABASE_URL của .env
    url = "postgres://fashion:secret@localhost:5433/fashion"

    config = database_config(url, host="host.docker.internal")

    assert config["HOST"] == "host.docker.internal"
    assert (config["USER"], config["PASSWORD"], config["PORT"]) == ("fashion", "secret", "5433")
    assert database_config(url, host="")["HOST"] == "localhost"


def test_invalid_port_raises_improperly_configured() -> None:
    with pytest.raises(ImproperlyConfigured, match="port"):
        database_config("postgres://u:p@localhost:54x2/fashion")


@pytest.mark.parametrize(
    ("url", "problem"),
    [
        ("postgres://localhost:5432/fashion", "user"),
        ("postgres://:p@localhost:5432/fashion", "user"),
        ("postgres://u:p@:5432/fashion", "host"),
        (MISPLACED_PASSWORD_URL, "user"),
        # Password chứa "/" không mã hoá: netloc dừng ở "/", không còn "@" nên không có user.
        # Phần sau ":" bị hiểu là port, nhưng chỗ cần sửa là user/password
        ("postgres://u:ab/cd@localhost:5432/fashion", "user"),
        ("postgres://u:p@localhost:5432", "tên database"),
        ("postgres://u:p@localhost:5432/", "tên database"),
        ("postgres://u:p@localhost:5432/a/b", "tên database"),
        ("postgres://u:p@localhost:5432///fashion", "tên database"),
        ("postgres://u:p@localhost:5432/a%40b", "tên database"),
        ("postgres://u:p@localhost:5432/a:b", "tên database"),
    ],
)
def test_rejects_malformed_url(url: str, problem: str) -> None:
    # Không tới bước kết nối: lỗi nêu biến và phần sai để người dùng sửa .env
    with pytest.raises(ImproperlyConfigured, match=f"DATABASE_URL.*{problem}"):
        database_config(url, host="host.docker.internal")


@pytest.mark.parametrize(
    "url",
    [
        pytest.param(MISPLACED_PASSWORD_URL, id="misplaced-password"),
        # Tới nhánh port: ValueError của urllib nêu nguyên phần bị hiểu là port
        pytest.param("postgres://u:p@localhost:top-secret/fashion", id="secret-in-port"),
    ],
)
def test_error_message_hides_url_and_password(url: str) -> None:
    with pytest.raises(ImproperlyConfigured) as exc_info:
        database_config(url)

    # Kiểm cả traceback, gồm exception được nối vào: manage.py và pytest in ra toàn bộ
    report = "".join(traceback.format_exception(exc_info.value))
    assert "top-secret" not in report
    assert "localhost" not in report


def test_manage_py_check_stops_before_connecting() -> None:
    # Biến môi trường thắng .env, nên chạy được cả trên máy dev lẫn CI
    # PYTHONUTF8: trên Windows, output bị chuyển hướng mặc định ghi bằng cp1252
    env = {
        **os.environ,
        "DATABASE_URL": MISPLACED_PASSWORD_URL,
        "PYTHONUTF8": "1",
    }

    result = subprocess.run(
        [sys.executable, "manage.py", "check", "--database", "default"],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "ImproperlyConfigured: DATABASE_URL thiếu user" in output
    assert "top-secret" not in output
