"""Đọc và kiểm tra biến môi trường (08 mục 2.3).

Mỗi biến được khai báo ở mốc đầu tiên dùng tới nó; `.env.example` chỉ chứa biến đã khai báo.
"""

import base64
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import parse_qsl, unquote, urlsplit

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from django.core.exceptions import ImproperlyConfigured
from pydantic import (
    NonNegativeInt,
    PositiveInt,
    SecretStr,
    ValidationError,
    field_validator,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from common.security.privacy import parse_keyring

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
    # Để rỗng ở máy chưa làm M1; deploy check `common.E002` từ chối keyring rỗng.
    JWT_SIGNING_KEYS: SecretStr = SecretStr("")
    JWT_ISSUER: str = "fashion-store"
    JWT_AUDIENCE_BACKOFFICE: str = "backoffice"
    JWT_ACCESS_TTL_SECONDS: PositiveInt = 600
    JWT_BACKOFFICE_REFRESH_TTL_SECONDS: PositiveInt = 43_200
    JWT_LEEWAY_SECONDS: NonNegativeInt = 30
    # Khoá AESGCM của RefreshReplay, độc lập khoá JWT (05 mục 2.1). Để rỗng ở máy chưa cần
    # refresh; deploy check `common.E003` từ chối khi thiếu khoá
    REFRESH_REPLAY_KEY_ID: str = ""
    REFRESH_REPLAY_KEY_PATH: str = ""

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


def _load_ed25519_pair(*, private_pem: str, public_pem: str) -> None:
    """Load thử key Ed25519; ném ValueError nếu không phải Ed25519 hoặc private/public lệch cặp."""
    public_key = serialization.load_pem_public_key(public_pem.encode())
    if not isinstance(public_key, Ed25519PublicKey):
        raise ValueError
    if not private_pem:
        return
    private_key = serialization.load_pem_private_key(private_pem.encode(), password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError
    raw = serialization.Encoding.Raw, serialization.PublicFormat.Raw
    if private_key.public_key().public_bytes(*raw) != public_key.public_bytes(*raw):
        raise ValueError


def jwt_keyring(raw: str) -> dict[str, dict[str, str]]:
    """Đọc keyring JWT `kid|private-key-base64|public-key-base64,...` (05 mục 2).

    Key đầu phát token mới nên phải có private key; các key sau có thể chỉ có public key để
    verify token cũ khi xoay khoá. Mọi key được load thử là Ed25519. Chuỗi rỗng trả keyring rỗng
    để local/CI chưa cần JWT vẫn chạy; deploy check `common.E002` chặn keyring rỗng khi triển khai.

    Raises:
        ImproperlyConfigured: `kid` rỗng, trùng hoặc chứa khoảng trắng; base64/PEM sai; key không
            phải Ed25519; private/public lệch cặp; key đầu thiếu private key.
    """
    keys: dict[str, dict[str, str]] = {}
    if not raw:
        return keys
    try:
        for entry in raw.split(","):
            raw_kid, private_b64, public_b64 = entry.split("|", 2)
            kid = raw_kid.strip()
            if not kid or kid in keys or any(char.isspace() for char in kid):
                raise ValueError
            private_pem = base64.b64decode(private_b64, validate=True).decode()
            public_pem = base64.b64decode(public_b64, validate=True).decode()
            if not keys and not private_pem:
                raise ValueError
            _load_ed25519_pair(private_pem=private_pem, public_pem=public_pem)
            keys[kid] = {"private_key": private_pem, "public_key": public_pem}
    except ValueError, TypeError, UnsupportedAlgorithm:
        # from None: exception gốc có thể chứa byte của private key (13 mục 10)
        raise ImproperlyConfigured("JWT_SIGNING_KEYS sai định dạng") from None
    return keys


REFRESH_REPLAY_KEY_BYTES = 32
REFRESH_REPLAY_KEY_ID_MAX_LENGTH = 32


def refresh_replay_key(*, key_id: str, path: str) -> bytes:
    """Đọc khoá AESGCM của RefreshReplay từ file đúng 32 byte (05 mục 2.1, 08 mục 2.3).

    Đường dẫn tương đối tính từ ``. Cả hai biến rỗng trả `b""` để local/CI chưa cần
    replay vẫn chạy; deploy check `common.E003` chặn khi triển khai. Lỗi không chứa nội dung khoá.

    Raises:
        ImproperlyConfigured: Chỉ có một trong hai biến; `key_id` dài quá 32 ký tự hoặc chứa
            khoảng trắng; file không đọc được hoặc không đúng 32 byte.
    """
    if not key_id and not path:
        return b""
    if not key_id or not path:
        raise ImproperlyConfigured(
            "REFRESH_REPLAY_KEY_ID và REFRESH_REPLAY_KEY_PATH phải đi cùng nhau"
        )
    if len(key_id) > REFRESH_REPLAY_KEY_ID_MAX_LENGTH or any(char.isspace() for char in key_id):
        raise ImproperlyConfigured(
            f"REFRESH_REPLAY_KEY_ID dài quá {REFRESH_REPLAY_KEY_ID_MAX_LENGTH} ký tự "
            "hoặc có khoảng trắng"
        )
    key_path = Path(path)
    if not key_path.is_absolute():
        key_path = BASE_DIR / key_path
    try:
        key = key_path.read_bytes()
    except OSError:
        raise ImproperlyConfigured(
            "REFRESH_REPLAY_KEY_PATH không đọc được; tạo khoá theo 08 mục 2.3"
        ) from None
    if len(key) != REFRESH_REPLAY_KEY_BYTES:
        # Chỉ nêu số byte mong đợi, không nêu độ dài hay nội dung thực của file
        raise ImproperlyConfigured(
            f"REFRESH_REPLAY_KEY_PATH phải chứa đúng {REFRESH_REPLAY_KEY_BYTES} byte"
        )
    return key
