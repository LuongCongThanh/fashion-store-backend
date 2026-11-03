"""Dùng `X-Request-ID` của BFF làm `request_id` của log và `ErrorDTO` (10 mục 4).

`django_structlog.RequestMiddleware` luôn bind một `uuid4`. Receiver này chạy ngay sau đó, trước log
`request_started`, và chỉ thay bằng header khi `X-BFF-Secret` đúng: client khác không đặt được
`request_id` để làm rối log của request khác.
"""

import re
from typing import Any

import structlog
from django.http import HttpRequest

from shared.api.client_ip import bff_secret_matches

logger = structlog.get_logger(__name__)

# Đủ cho UUID, ULID và trace id; chặn ký tự lạ và giá trị dài làm phình log
REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,64}")


def bind_upstream_request_id(request: HttpRequest, **kwargs: Any) -> None:
    """Receiver của `django_structlog.signals.bind_extra_request_metadata`."""
    claimed = request.headers.get("X-Request-ID")
    if claimed is None or not bff_secret_matches(request):
        return
    if REQUEST_ID_PATTERN.fullmatch(claimed) is None:
        # Không ghi giá trị header: dữ liệu tuỳ ý từ upstream
        logger.warning("request_id_invalid")
        return
    structlog.contextvars.bind_contextvars(request_id=claimed)
