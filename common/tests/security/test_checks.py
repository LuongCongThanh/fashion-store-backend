from django.core.checks import Tags, run_checks
from django.test import override_settings

from common.security.checks import check_pii_hmac_key_length


@override_settings(PII_HMAC_KEYS=(("k2", "x" * 32), ("k1", "short")))
def test_deploy_check_flags_short_secret_by_kid() -> None:
    errors = check_pii_hmac_key_length()

    assert [e.id for e in errors] == ["common.E001"]
    assert "k1" in errors[0].msg
    assert "short" not in errors[0].msg


@override_settings(PII_HMAC_KEYS=(("k1", "x" * 32),))
def test_deploy_check_passes_long_secret() -> None:
    assert check_pii_hmac_key_length() == []


@override_settings(JWT_SIGNING_KEYS={})
def test_deploy_check_rejects_empty_jwt_keyring() -> None:
    errors = run_checks(include_deployment_checks=True, tags=[Tags.security])

    assert "common.E002" in [e.id for e in errors]


@override_settings(JWT_SIGNING_KEYS={"k1": {"private_key": "pem", "public_key": "pem"}})
def test_deploy_check_accepts_configured_jwt_keyring() -> None:
    errors = run_checks(include_deployment_checks=True, tags=[Tags.security])

    assert "common.E002" not in [e.id for e in errors]
