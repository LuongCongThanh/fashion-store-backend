import pytest
from django.test import override_settings

from shared.privacy import parse_keyring, pii_hmac, pii_hmac_candidates

KEYRING = (("k1", "secret-1"),)
ROTATED = (("k2", "secret-2"), ("k1", "secret-1"))


@override_settings(PII_HMAC_KEYS=KEYRING)
def test_same_input_gives_same_value_with_kid_prefix() -> None:
    value = pii_hmac("+84901234567")

    assert value == pii_hmac("+84901234567")
    assert value.startswith("k1:")
    assert len(value.removeprefix("k1:")) == 64
    assert value != pii_hmac("+84901234568")


def test_rotating_key_gives_new_kid_and_old_value_still_found() -> None:
    with override_settings(PII_HMAC_KEYS=KEYRING):
        old = pii_hmac("+84901234567")

    with override_settings(PII_HMAC_KEYS=ROTATED):
        new = pii_hmac("+84901234567")
        candidates = pii_hmac_candidates("+84901234567")

    assert new.startswith("k2:")
    assert candidates == [new, old]


def test_parse_keyring_keeps_order_and_allows_colon_in_secret() -> None:
    assert parse_keyring("k2:a:b, k1:c") == (("k2", "a:b"), ("k1", "c"))


def test_parse_keyring_strips_whitespace_around_kid_and_secret() -> None:
    assert parse_keyring("k2 : a , k1:b") == (("k2", "a"), ("k1", "b"))


@pytest.mark.parametrize(
    "raw", ["", "k1", "k1:", ":secret", "k1:a,k1:b", "k1:a,", " :a", "k1: ", "k1 :a,k1:b"]
)
def test_parse_keyring_rejects_malformed(raw: str) -> None:
    with pytest.raises(ValueError):  # noqa: PT011  # thông báo khác nhau theo từng lỗi
        parse_keyring(raw)


def test_parse_keyring_error_does_not_leak_secret() -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        parse_keyring("k1:top-secret,k1:other")

    assert "top-secret" not in str(exc_info.value)
