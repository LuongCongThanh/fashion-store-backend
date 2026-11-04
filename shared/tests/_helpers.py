"""Hằng số và helper dùng chung cho test của shared/api."""

from typing import Any

from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from shared.api.client_ip import CLIENT_IP_ATTR

BFF_IP = "10.0.0.5"
CLIENT_IP = "203.0.113.7"
BFF_SECRET = "secret-new"
OLD_BFF_SECRET = "secret-old"


def drf_request(user: Any = None, client_ip: str = CLIENT_IP) -> Request:
    """Request DRF như sau `ClientIpMiddleware`, có `user` đã xác thực nếu truyền vào."""
    django_request = APIRequestFactory().get("/")
    if user is not None:
        force_authenticate(django_request, user=user)
    setattr(django_request, CLIENT_IP_ATTR, client_ip)
    return APIView().initialize_request(django_request)


def error_of(response: Any) -> dict[str, Any]:
    """Kiểm đủ shape `ErrorDTO` (04 mục 3) rồi trả phần `error`."""
    body = response.json()
    assert set(body) == {"error"}
    error: dict[str, Any] = body["error"]
    assert set(error) == {"code", "message", "details", "request_id"}
    assert error["request_id"]
    assert error["message"]
    return error
