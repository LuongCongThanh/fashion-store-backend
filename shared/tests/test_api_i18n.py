import pytest
from django.test import Client

pytestmark = pytest.mark.urls("shared.tests.api_urls")


def test_language_defaults_to_vietnamese_without_accept_language(client: Client) -> None:
    response = client.get("/language")

    assert response.json() == {"language": "vi"}


def test_accept_language_selects_english(client: Client) -> None:
    response = client.get("/language", HTTP_ACCEPT_LANGUAGE="en")

    assert response.json() == {"language": "en"}
