import pytest
from django.test import Client

from common.tests import api_urls
from common.tests._helpers import error_of
from config import urls as config_urls

API_URLS = pytest.mark.urls("common.tests.api_urls")


def test_unknown_route_returns_error_dto(client: Client) -> None:
    # Dùng urlconf thật để kiểm handler404 khai báo ở config/urls.py
    response = client.get("/api/v1/khong-ton-tai")

    assert response.status_code == 404
    error = error_of(response)
    assert (error["code"], error["details"]) == ("NOT_FOUND", {})


@API_URLS
def test_unhandled_exception_returns_internal_error() -> None:
    client = Client(raise_request_exception=False)

    response = client.get("/boom")

    assert response.status_code == 500
    error = error_of(response)
    assert (error["code"], error["details"]) == ("INTERNAL_ERROR", {})
    assert "secret internal detail" not in response.content.decode()


@API_URLS
def test_suspicious_operation_outside_drf_returns_bad_request(client: Client) -> None:
    response = client.get("/suspicious")

    assert response.status_code == 400
    error = error_of(response)
    assert (error["code"], error["details"]) == ("BAD_REQUEST", {})
    assert "secret internal detail" not in response.content.decode()


@API_URLS
def test_permission_denied_outside_drf_returns_error_dto(client: Client) -> None:
    response = client.get("/forbidden")

    assert response.status_code == 403
    error = error_of(response)
    assert (error["code"], error["details"]) == ("PERMISSION_DENIED", {})


@pytest.mark.parametrize("name", ["handler400", "handler403", "handler404", "handler500"])
def test_test_urlconf_declares_same_error_handlers_as_config(name: str) -> None:
    # api_urls.py lặp lại handler vì ghi đè ROOT_URLCONF; không để hai nơi lệch nhau
    assert getattr(api_urls, name) == getattr(config_urls, name)
