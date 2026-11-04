import pytest
from django.db import DatabaseError
from django.test import Client, override_settings

from config.settings import production


def test_healthz_returns_ok(client: Client) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readyz_returns_ok_when_database_reachable(client: Client) -> None:
    response = client.get("/readyz")

    assert response.status_code == 200


@pytest.mark.django_db
def test_readyz_returns_503_when_database_unreachable(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise DatabaseError("connection refused")

    monkeypatch.setattr("django.db.backends.utils.CursorWrapper.execute", fail)

    response = client.get("/readyz")

    assert response.status_code == 503


@pytest.mark.django_db
@override_settings(
    SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=production.SECURE_REDIRECT_EXEMPT
)
@pytest.mark.parametrize("path", ["/healthz", "/readyz"])
def test_health_checks_skip_https_redirect_in_production(client: Client, path: str) -> None:
    assert client.get(path).status_code == 200


@override_settings(
    SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=production.SECURE_REDIRECT_EXEMPT
)
def test_other_paths_still_redirect_to_https_in_production(client: Client) -> None:
    assert client.get("/api/schema/").status_code == 301
