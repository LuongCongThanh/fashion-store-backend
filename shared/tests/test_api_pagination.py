import pytest
from django.test import Client

from shared.tests._helpers import error_of

pytestmark = pytest.mark.urls("shared.tests.api_urls")


def test_page_size_capped_at_100(client: Client) -> None:
    response = client.get("/paged", {"page_size": 500})

    assert response.status_code == 200
    assert len(response.json()["results"]) == 100


def test_default_page_size_is_24(client: Client) -> None:
    response = client.get("/paged")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 250
    assert len(body["results"]) == 24


@pytest.mark.parametrize("page_size", ["0", "-5", "abc"])
def test_invalid_page_size_returns_400(client: Client, page_size: str) -> None:
    response = client.get("/paged", {"page_size": page_size})

    assert response.status_code == 400
    error = error_of(response)
    assert error["code"] == "VALIDATION_ERROR"
    assert set(error["details"]["fields"]) == {"page_size"}


@pytest.mark.parametrize("page", ["0", "-1", "abc", "1.5"])
def test_invalid_page_returns_400(client: Client, page: str) -> None:
    response = client.get("/paged", {"page": page})

    assert response.status_code == 400
    error = error_of(response)
    assert error["code"] == "VALIDATION_ERROR"
    assert set(error["details"]["fields"]) == {"page"}


def test_page_past_end_returns_404(client: Client) -> None:
    response = client.get("/paged", {"page": 99})

    assert response.status_code == 404
    assert error_of(response)["code"] == "NOT_FOUND"
