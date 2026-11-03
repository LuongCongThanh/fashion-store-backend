"""Dùng `X-Request-ID` của BFF làm `request_id` của log và `ErrorDTO` (10 mục 4).

`django_structlog.RequestMiddleware` luôn bind một `uuid4`. Receiver này chạy ngay sau đó, trước log
`request_started`, và chỉ thay bằng header khi `X-BFF-Secret` đúng, tức request đi qua BFF. Secret
không chứng minh BFF tự sinh id: BFF phải bỏ `X-Request-ID` do browser gửi và dựng lại (05 mục 1.1),
nếu không browser vẫn chọn được `request_id`.
"""

import re
from typing import Any

import structlog
from django.http import HttpRequest

from shared.api.client_ip import bff_secret_matches

logger = structlog.get_logger(__name__)

# Đủ cho UUID, ULID và trace id; chặn ký tự lạ và giá trị dài làm phình log
_REQUEST_ID_MAX_LENGTH = 64
_REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]+")


def bind_upstream_request_id(request: HttpRequest, **kwargs: Any) -> None:
    """Receiver của `django_structlog.signals.bind_extra_request_metadata`."""
    claimed = request.headers.get("X-Request-ID")
    # Header rỗng coi như không gửi: giữ id tự sinh, không cảnh báo
    if not claimed or not bff_secret_matches(request):
        return
    if len(claimed) > _REQUEST_ID_MAX_LENGTH:
        reason = "too_long"
    elif _REQUEST_ID_PATTERN.fullmatch(claimed) is None:
        reason = "invalid_chars"
    else:
        structlog.contextvars.bind_contextvars(request_id=claimed)
        return
    # Không ghi giá trị header: dữ liệu tuỳ ý từ upstream
    logger.warning("request_id_invalid", reason=reason)
