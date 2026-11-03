"""Gán `request.client_ip`: IP mà throttle tính hạn mức (ADR 0009, 05 mục 5).

Mọi request đi qua Next.js nên `REMOTE_ADDR` là IP của BFF. Chỉ tin `X-Client-IP` khi
`X-BFF-Secret` khớp một secret trong `BFF_SHARED_SECRETS` và giá trị là IPv4/IPv6 hợp lệ;
ngược lại dùng `REMOTE_ADDR`.

`bff_secret_matches` là quy tắc tin BFF dùng chung: `shared.api.request_id` cũng chỉ tin
`X-Request-ID` khi hàm này đúng.
"""

import hmac
import ipaddress
from collections.abc import Callable

import structlog
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from rest_framework.request import Request

logger = structlog.get_logger(__name__)

# Tên thuộc tính middleware gán lên request; đọc qua get_client_ip
CLIENT_IP_ATTR = "client_ip"


def bff_secret_matches(request: HttpRequest) -> bool:
    """`X-BFF-Secret` khớp một secret trong `BFF_SHARED_SECRETS`: request đến từ BFF."""
    provided = request.headers.get("X-BFF-Secret")
    if provided is None:
        return False
    # So với mọi secret, không dừng sớm, để thời gian không lộ secret nào khớp
    matched = False
    for secret in settings.BFF_SHARED_SECRETS:
        matched |= hmac.compare_digest(provided.encode(), secret.encode())
    return matched


def resolve_client_ip(request: HttpRequest) -> str:
    remote_addr: str = request.META.get("REMOTE_ADDR", "")
    if not bff_secret_matches(request):
        return remote_addr
    claimed = request.headers.get("X-Client-IP")
    if claimed is None:
        return remote_addr
    try:
        return str(ipaddress.ip_address(claimed.strip()))
    except ValueError:
        # Không ghi giá trị header: có thể là IP thô hoặc dữ liệu tuỳ ý
        logger.warning("client_ip_invalid")
        return remote_addr


def get_client_ip(request: HttpRequest | Request) -> str:
    """IP mà `ClientIpMiddleware` đã xác minh; nhận cả `Request` của DRF."""
    client_ip: str = getattr(request, CLIENT_IP_ATTR)
    return client_ip


class ClientIpMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        setattr(request, CLIENT_IP_ATTR, resolve_client_ip(request))
        return self.get_response(request)
