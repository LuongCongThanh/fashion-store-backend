import pytest
from django.test import Client

from config import urls as config_urls
from shared.tests import api_urls
from shared.tests._helpers import error_of

API_URLS = pytest.mark.urls("shared.tests.api_urls")


def test_unknown_route_returns_error_dto(client: Client) -> None:
    # Dùng urlconf thật để kiểm handler404 khai báo ở config/urls.py
    response = client.get("/api/v1/khong-ton-tai")

    assert response.status_code == 404
    error = error_of(response)
    assert (error["code"], error["details"]) == ("NOT_FOUND", {})


@API_URLS
def test_method_not_allowed_returns_error_dto(client: Client) -> None:
    response = client.post("/paged")

    assert response.status_code == 405
    error = error_of(response)
    assert (error["code"], error["details"]) == ("METHOD_NOT_ALLOWED", {})
    assert "GET" in response["Allow"]


@API_URLS
def test_validation_error_returns_fields(client: Client) -> None:
    response = client.post(
        "/validate",
        {"address": {"city": ""}, "lines": [{"sku": "A"}, {}]},
        content_type="application/json",
    )

    assert response.status_code == 400
    error = error_of(response)
    assert error["code"] == "VALIDATION_ERROR"
    assert set(error["details"]["fields"]) == {"name", "address.city", "lines.1.sku"}
    assert all(isinstance(m, str) for m in error["details"]["fields"]["address.city"])


@API_URLS
def test_domain_error_uses_class_status(client: Client) -> None:
    response = client.get("/domain-error")

    assert response.status_code == 409
    error = error_of(response)
    assert error["code"] == "OUT_OF_STOCK"
    assert error["message"] == "Một số Biến thể không đủ hàng."
    assert error["details"] == {"items": [{"sku": "A", "requested": 3, "available": 1}]}


@API_URLS
def test_throttled_keeps_retry_after_header(client: Client) -> None:
    response = client.get("/throttled")

    assert response.status_code == 429
    assert error_of(response)["code"] == "THROTTLED"
    assert response["Retry-After"] == "30"


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


@API_URLS
def test_default_permission_denies_anonymous(client: Client) -> None:
    response = client.get("/private")

    assert response.status_code == 403
    assert error_of(response)["code"] == "PERMISSION_DENIED"


def test_schema_is_public_despite_default_permission(client: Client) -> None:
    response = client.get("/api/schema/")

    assert response.status_code == 200


@pytest.mark.parametrize("name", ["handler400", "handler403", "handler404", "handler500"])
def test_test_urlconf_declares_same_error_handlers_as_config(name: str) -> None:
    # api_urls.py lặp lại handler vì ghi đè ROOT_URLCONF; không để hai nơi lệch nhau
    assert getattr(api_urls, name) == getattr(config_urls, name)
