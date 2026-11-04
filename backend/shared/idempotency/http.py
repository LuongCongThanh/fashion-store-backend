"""Lớp HTTP của `Idempotency-Key` (04 mục 1); lõi claim/lease ở `shared.idempotency`.

Hàm hai bước, không bọc view: view kiểm quyền/sở hữu rồi gọi `begin(request)`. Nhận `Claim`
thì chạy tác động nghiệp vụ và gọi `claim.complete(...)` bên trong `transaction.atomic` của
mình. Nhận `Replay` hoặc `Pending` thì trả `response(outcome)`.
"""

import hashlib
import json
import uuid
from typing import Any

from django.http import QueryDict
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import UnsupportedMediaType, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from shared import idempotency
from shared.idempotency import Claim, Pending, Replay

KEY_HEADER = "Idempotency-Key"
CART_HEADER = "X-Cart-Token"


def begin(request: Request) -> Claim | Replay | Pending:
    """Đọc `Idempotency-Key`, dựng scope và hash của body rồi giao cho lõi claim key.

    Raises:
        ValidationError: Thiếu `Idempotency-Key`, key không phải UUID, hoặc request không có
            danh tính (Tài khoản hay `X-Cart-Token`).
        UnsupportedMediaType: Body không phải JSON (form, multipart).
        IdempotencyConflict: Cùng key nhưng body khác lần gửi trước.
    """
    key = _parse_key(request)
    scope = _scope(request)
    if isinstance(request.data, QueryDict):
        # QueryDict gộp giá trị lặp và chứa file: không chuẩn hoá được để tính hash
        raise UnsupportedMediaType(request.content_type)
    return idempotency.claim(scope, key, request_hash(request.data))


def response(outcome: Replay | Pending) -> Response:
    """`Replay`: nguyên status và body đã lưu. `Pending`: `202 IdempotencyPendingDTO` (04 mục
    5.2) kèm `Retry-After`; endpoint cần body 202 khác tự dựng."""
    if isinstance(outcome, Replay):
        return Response(outcome.body, status=outcome.status)
    return Response(
        {"code": "IDEMPOTENCY_IN_PROGRESS", "retry_after": outcome.retry_after},
        status=202,
        headers={"Retry-After": str(outcome.retry_after)},
    )


def request_hash(data: Any) -> str:
    """SHA-256 của body đã parse, chuẩn hoá để thứ tự key không đổi hash."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    # JSON hợp lệ có thể chứa surrogate lẻ (`"\ud800"`), UTF-8 strict không encode được
    return hashlib.sha256(canonical.encode("utf-8", "surrogatepass")).hexdigest()


def _parse_key(request: Request) -> uuid.UUID:
    try:
        return uuid.UUID(request.headers.get(KEY_HEADER, ""))
    except ValueError:
        raise ValidationError({KEY_HEADER: [_("Cần header Idempotency-Key dạng UUID.")]}) from None


def _scope(request: Request) -> str:
    """`"{METHOD} {path}|{identity}"`; path đã gồm ID/mã tài nguyên, bỏ `/` cuối."""
    user: Any = request.user
    if user and user.is_authenticated:
        identity = f"account:{user.pk}"
    elif token := request.headers.get(CART_HEADER):
        # Không lưu token thô của giỏ
        identity = f"cart:{hashlib.sha256(token.encode()).hexdigest()}"
    else:
        message = _("Cần đăng nhập hoặc gửi X-Cart-Token để dùng Idempotency-Key.")
        raise ValidationError({CART_HEADER: [message]})
    return f"{request.method} {request.path.rstrip('/')}|{identity}"
