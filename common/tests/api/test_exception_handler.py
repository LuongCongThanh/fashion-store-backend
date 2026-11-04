import pytest
from django.test import Client

from common.tests._helpers import error_of

API_URLS = pytest.mark.urls("common.tests.api_urls")


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
def test_default_permission_denies_anonymous(client: Client) -> None:
    response = client.get("/private")

    assert response.status_code == 403
    assert error_of(response)["code"] == "PERMISSION_DENIED"


def test_schema_is_public_despite_default_permission(client: Client) -> None:
    response = client.get("/api/schema/")

    assert response.status_code == 200
