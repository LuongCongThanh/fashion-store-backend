"""Throttle cơ sở của API (05 mục 5).

Khoá theo IP dùng `pii_hmac(get_client_ip(request))`, không bao giờ là IP thô; IP do
`shared.api.client_ip.ClientIpMiddleware` gán. Hạn mức của từng scope nằm ở
`REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]` trong settings. Cache lỗi thì fail-open: cho
request qua và log `throttle_backend_unavailable` chỉ kèm scope. Scope riêng thêm ở mốc dùng
tới.
"""

from typing import TYPE_CHECKING, Any

import structlog
from redis.exceptions import RedisError
from rest_framework.request import Request
from rest_framework.throttling import SimpleRateThrottle

from shared.api.client_ip import get_client_ip
from shared.privacy import pii_hmac

if TYPE_CHECKING:
    # rest_framework.views đọc DEFAULT_THROTTLE_CLASSES lúc import: import thật gây vòng
    from rest_framework.views import APIView

logger = structlog.get_logger(__name__)


class FailOpenRateThrottle(SimpleRateThrottle):
    """Redis lỗi thì không chặn request: throttle là lớp bảo vệ phụ, không phải điểm hỏng."""

    def allow_request(self, request: Request, view: APIView) -> bool:
        try:
            return super().allow_request(request, view)
        except RedisError:
            # Không log khoá cache, IP hay lỗi gốc: chuỗi lỗi có thể chứa khoá hoặc host Redis.
            logger.warning("throttle_backend_unavailable", scope=self.scope)
            return True


def _is_authenticated(request: Request) -> bool:
    return bool(request.user and request.user.is_authenticated)


class ClientIpRateThrottle(FailOpenRateThrottle):
    """Đếm theo IP đã xác minh, khoá là HMAC của IP."""

    def get_cache_key(self, request: Request, view: APIView) -> str | None:
        ident = pii_hmac(get_client_ip(request))
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AnonThrottle(ClientIpRateThrottle):
    """Request ẩn danh, đếm theo IP; hạn mức ở `DEFAULT_THROTTLE_RATES["anon"]`."""

    scope = "anon"

    def get_cache_key(self, request: Request, view: APIView) -> str | None:
        if _is_authenticated(request):
            return None
        return super().get_cache_key(request, view)


class AccountThrottle(FailOpenRateThrottle):
    """Request đã đăng nhập, đếm theo Tài khoản; hạn mức ở `DEFAULT_THROTTLE_RATES["account"]`.

    Request ẩn danh không bị lớp này đếm.
    """

    scope = "account"

    def get_cache_key(self, request: Request, view: APIView) -> str | None:
        if not _is_authenticated(request):
            return None
        user: Any = request.user
        return self.cache_format % {"scope": self.scope, "ident": user.pk}
