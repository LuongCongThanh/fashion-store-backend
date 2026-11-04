"""Đọc và kiểm tra biến môi trường (08 mục 2.3).

Mỗi biến được khai báo ở mốc đầu tiên dùng tới nó; `.env.example` chỉ chứa biến đã khai báo.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import parse_qsl, unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured
from pydantic import SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from shared.privacy import parse_keyring

BASE_DIR = Path(__file__).resolve().parent.parent


class Env(BaseSettings):
    # extra="forbid": biến lạ hoặc gõ sai tên trong .env bị báo ngay, không bị bỏ qua êm
    model_config = SettingsConfigDict(extra="forbid")

    # Từ M0
    # Không dùng để chọn settings: lúc đọc .env thì settings đã được chọn. Khai báo để .env
    # chứa được biến này, vì Compose nạp .env vào biến môi trường của container; chạy trên
    # máy thì đặt bằng `export` hoặc dùng mặc định `local` của manage.py
    DJANGO_SETTINGS_MODULE: str = "config.settings.local"
    DJANGO_SECRET_KEY: SecretStr
    DATABASE_URL: str
    # Khác rỗng thì thay host của DATABASE_URL: container trong Compose đặt host.docker.internal
    # để không phải ghi DATABASE_URL có mật khẩu vào docker-compose.yml
    DATABASE_HOST: str = ""
    # Script setup in ra cùng DATABASE_URL; không code nào đọc (cổng nằm trong DATABASE_URL).
    # Khai báo để pydantic-settings không báo biến thừa khi đọc .env
    PG_PORT: int = 5432
    # Chỉ Compose dùng: cổng Redis của Compose mở ra máy, tránh 6379 của project khác
    REDIS_PORT: int = 6380
    REDIS_URL: str
    EMAIL_HOST: str
    EMAIL_PORT: int
    # Dạng `kid2:s2,kid1:s1`, không phải JSON: NoDecode để pydantic-settings không tự decode
    PII_HMAC_KEYS: Annotated[tuple[tuple[str, SecretStr], ...], NoDecode]
    STOREFRONT_ORIGIN: str
    # 1 hoặc 2 secret cách nhau bằng dấu phẩy để xoay không gián đoạn (05 mục 5)
    BFF_SHARED_SECRET: Annotated[tuple[SecretStr, ...], NoDecode]
    # `kid|private-key-base64|public-key-base64`, nhiều khoá cách nhau bằng dấu phẩy.
    # Để rỗng ở máy chưa làm M1; deploy check và token codec từ chối keyring rỗng.
    JWT_SIGNING_KEYS: SecretStr = SecretStr("")
    JWT_ISSUER: str = "fashion-store"
    JWT_AUDIENCE_BACKOFFICE: str = "backoffice"
    JWT_ACCESS_TTL_SECONDS: int = 600
    JWT_BACKOFFICE_REFRESH_TTL_SECONDS: int = 43_200
    JWT_LEEWAY_SECONDS: int = 30

    @field_validator("PII_HMAC_KEYS", mode="before")
    @classmethod
    def _parse_keyring(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        # Bọc secret trong SecretStr để repr của Env và lỗi validate không lộ secret
        return tuple((kid, SecretStr(secret)) for kid, secret in parse_keyring(value))

    @field_validator("BFF_SHARED_SECRET", mode="before")
    @classmethod
    def _parse_bff_secrets(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        secrets = [secret.strip() for secret in value.split(",")]
        # Thông báo lỗi không chứa secret
        if not 1 <= len(secrets) <= 2 or not all(secrets):
            raise ValueError("cần 1 hoặc 2 secret không rỗng, cách nhau bằng dấu phẩy")
        return tuple(SecretStr(secret) for secret in secrets)


def load_env(env_file: Path | None = BASE_DIR / ".env") -> Env:
    try:
        return Env(_env_file=env_file)  # type: ignore[call-arg]
    except ValidationError as exc:
        names = ", ".join(str(err["loc"][0]) for err in exc.errors() if err["loc"])
        raise ImproperlyConfigured(f"Thiếu hoặc sai biến môi trường: {names}") from exc


@lru_cache(maxsize=1)
def get_env() -> Env:
    return load_env()


def _malformed_database_url(problem: str) -> ImproperlyConfigured:
    # Chỉ nêu phần sai và dạng đúng, không chứa giá trị nào của URL (có thể chứa password)
    return ImproperlyConfigured(
        f"DATABASE_URL {problem}, dạng đúng: postgres://user:pass@host:port/name"
    )


def database_config(url: str, host: str = "") -> dict[str, Any]:
    """Chuyển `postgres://user:pass@host:port/name?opt=v` thành một mục của `DATABASES`.

    Tham số query (ví dụ `sslmode=require` cho RDS) được giữ lại trong `OPTIONS`. `host` khác
    rỗng thì thay host của URL (container trong Compose gọi PostgreSQL trên máy).

    Raises:
        ImproperlyConfigured: URL sai scheme, thiếu user, thiếu host, có tên database rỗng
            hoặc chứa `/`, `@`, `:`, hoặc có port không hợp lệ.
    """
    parts = urlsplit(url)
    if parts.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured("DATABASE_URL phải bắt đầu bằng postgres://")
    # URL sai cấu trúc vẫn tách được: phần còn lại rơi vào NAME và lỗi chỉ lộ ra khi kết nối,
    # kèm nguyên chuỗi (có thể chứa password)
    if not parts.username:
        raise _malformed_database_url("thiếu user")
    if not parts.hostname:
        raise _malformed_database_url("thiếu host")
    # removeprefix, không lstrip: "///fashion" phải giữ "/" để bị từ chối, không thành "fashion"
    name = unquote(parts.path.removeprefix("/"))
    if not name or any(char in name for char in "/@:"):
        raise _malformed_database_url("có tên database rỗng hoặc chứa /, @, :")
    # Kiểm port sau cùng: password chứa "/" làm phần sau ":" bị hiểu là port, kiểm trước thì
    # báo "port không hợp lệ" thay vì chỉ ra URL thiếu user
    try:
        port = parts.port or 5432
    except ValueError:
        # from None: ValueError của urllib chứa nguyên phần bị hiểu là port, có thể là password
        raise ImproperlyConfigured("DATABASE_URL có port không hợp lệ") from None
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": name,
        "USER": unquote(parts.username or ""),
        "PASSWORD": unquote(parts.password or ""),
        "HOST": host or parts.hostname or "",
        "PORT": str(port),
        "OPTIONS": dict(parse_qsl(parts.query)),
    }
