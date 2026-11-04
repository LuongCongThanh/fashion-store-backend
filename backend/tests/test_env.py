import base64
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.core.exceptions import ImproperlyConfigured

from config.env import Env, jwt_keyring, load_env

M0_VARS = {
    "DJANGO_SECRET_KEY": "test-secret",
    "DATABASE_URL": "postgres://fashion:fashion@localhost:5432/fashion",
    "REDIS_URL": "redis://localhost:6380/0",
    "EMAIL_HOST": "localhost",
    "EMAIL_PORT": "1025",
    "PII_HMAC_KEYS": "test-pii-1:test-pii-secret",
    "STOREFRONT_ORIGIN": "http://localhost:3000",
    "BFF_SHARED_SECRET": "test-bff-secret",
}


@pytest.fixture
def m0_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in Env.model_fields:
        monkeypatch.delenv(name, raising=False)
    for name, value in M0_VARS.items():
        monkeypatch.setenv(name, value)


@pytest.mark.usefixtures("m0_env")
def test_loads_with_only_m0_variables() -> None:
    env = load_env(env_file=None)

    assert env.EMAIL_PORT == 1025


@pytest.mark.usefixtures("m0_env")
def test_missing_required_variable_names_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BFF_SHARED_SECRET")

    with pytest.raises(ImproperlyConfigured, match="BFF_SHARED_SECRET"):
        load_env(env_file=None)


@pytest.mark.usefixtures("m0_env")
def test_parses_keyring_once_and_hides_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_HMAC_KEYS", "k2:secret-2,k1:secret-1")

    env = load_env(env_file=None)

    assert [(kid, secret.get_secret_value()) for kid, secret in env.PII_HMAC_KEYS] == [
        ("k2", "secret-2"),
        ("k1", "secret-1"),
    ]
    assert "secret-2" not in repr(env)


@pytest.mark.usefixtures("m0_env")
def test_malformed_keyring_names_variable_without_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PII_HMAC_KEYS", "k1:top-secret,k1:other")

    with pytest.raises(ImproperlyConfigured, match="PII_HMAC_KEYS") as exc_info:
        load_env(env_file=None)

    assert "top-secret" not in str(exc_info.value)


@pytest.mark.usefixtures("m0_env")
def test_bff_secret_accepts_two_values_for_rotation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BFF_SHARED_SECRET", "new-secret, old-secret")

    env = load_env(env_file=None)

    assert [secret.get_secret_value() for secret in env.BFF_SHARED_SECRET] == [
        "new-secret",
        "old-secret",
    ]
    assert "new-secret" not in repr(env)


@pytest.mark.parametrize("raw", ["", " , ", "a,,b", "a,b,c"])
@pytest.mark.usefixtures("m0_env")
def test_bff_secret_rejects_empty_or_more_than_two_values(
    monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    monkeypatch.setenv("BFF_SHARED_SECRET", raw)

    with pytest.raises(ImproperlyConfigured, match="BFF_SHARED_SECRET") as exc_info:
        load_env(env_file=None)

    assert "a,b" not in str(exc_info.value)


@pytest.mark.usefixtures("m0_env")
def test_redis_port_is_accepted_and_defaults_to_6380(tmp_path: Path) -> None:
    # Compose đọc REDIS_PORT từ .env; extra="forbid" nên Env phải khai báo biến này
    env_file = tmp_path / ".env"
    env_file.write_text("REDIS_PORT=6390\n", encoding="utf-8")

    assert load_env(env_file=env_file).REDIS_PORT == 6390
    assert load_env(env_file=None).REDIS_PORT == 6380


@pytest.mark.usefixtures("m0_env")
def test_database_host_is_accepted_and_defaults_to_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Container trong Compose đặt DATABASE_HOST thay vì ghi DATABASE_URL có mật khẩu
    assert load_env(env_file=None).DATABASE_HOST == ""

    monkeypatch.setenv("DATABASE_HOST", "host.docker.internal")

    assert load_env(env_file=None).DATABASE_HOST == "host.docker.internal"


@pytest.mark.parametrize(
    "name",
    ["JWT_ACCESS_TTL_SECONDS", "JWT_BACKOFFICE_REFRESH_TTL_SECONDS", "JWT_LEEWAY_SECONDS"],
)
@pytest.mark.usefixtures("m0_env")
def test_jwt_durations_reject_negative(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    monkeypatch.setenv(name, "-1")

    with pytest.raises(ImproperlyConfigured, match=name):
        load_env(env_file=None)


@pytest.mark.parametrize("name", ["JWT_ACCESS_TTL_SECONDS", "JWT_BACKOFFICE_REFRESH_TTL_SECONDS"])
@pytest.mark.usefixtures("m0_env")
def test_jwt_ttl_rejects_zero(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    monkeypatch.setenv(name, "0")

    with pytest.raises(ImproperlyConfigured, match=name):
        load_env(env_file=None)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def _ed25519_pems() -> tuple[bytes, bytes]:
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return private_pem, public_pem


def _entry(kid: str, private_pem: bytes | None, public_pem: bytes) -> str:
    private = _b64(private_pem) if private_pem is not None else ""
    return f"{kid}|{private}|{_b64(public_pem)}"


def test_jwt_keyring_reads_current_and_verify_only_keys() -> None:
    current_private, current_public = _ed25519_pems()
    _old_private, old_public = _ed25519_pems()
    raw = f"{_entry(' new ', current_private, current_public)},{_entry('old', None, old_public)}"

    keyring = jwt_keyring(raw)

    assert list(keyring) == ["new", "old"]
    assert keyring["new"]["private_key"] == current_private.decode()
    assert keyring["old"] == {"private_key": "", "public_key": old_public.decode()}


def _ec_public_pem() -> bytes:
    return (
        ec.generate_private_key(ec.SECP256R1())
        .public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )


def _invalid_keyrings() -> dict[str, str]:
    private_pem, public_pem = _ed25519_pems()
    _other_private, other_public = _ed25519_pems()
    valid = _entry("k1", private_pem, public_pem)
    return {
        "duplicate-kid": f"{valid},{_entry('k1', None, other_public)}",
        "blank-kid": _entry("  ", private_pem, public_pem),
        "kid-with-space": _entry("k 1", private_pem, public_pem),
        "not-base64": f"k1|{_b64(private_pem)}|not*base64",
        "not-pem": f"k1|{_b64(private_pem)}|{_b64(b'not a pem')}",
        "not-ed25519": _entry("k1", None, _ec_public_pem()),
        "current-without-private": f"{_entry('k1', None, public_pem)},{valid}",
        "mismatched-pair": _entry("k1", private_pem, other_public),
        "missing-part": f"k1|{_b64(public_pem)}",
    }


@pytest.mark.parametrize("case", list(_invalid_keyrings()))
def test_jwt_keyring_rejects_invalid_entry_without_leaking_key(case: str) -> None:
    raw = _invalid_keyrings()[case]

    with pytest.raises(ImproperlyConfigured, match="JWT_SIGNING_KEYS") as exc_info:
        jwt_keyring(raw)

    # from None: traceback không mang exception gốc chứa byte của key (13 mục 10)
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True
    assert "PRIVATE KEY" not in str(exc_info.value)
