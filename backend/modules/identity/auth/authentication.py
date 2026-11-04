"""Xác thực Bearer access token của back-office (05 mục 2, 2.2, 4; ADR 0002).

Token chỉ chứng minh danh tính đã được ký; quyền dựa trên trạng thái auth (`is_active`, `kind`,
`token_version`) đọc từ PostgreSQL ở mọi request back-office, không qua cache.
"""

from typing import TYPE_CHECKING, Any

import structlog
from django.conf import settings
from django.db import DatabaseError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme_object
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.request import Request

from modules.identity.auth.tokens import (
    AUTH_SCHEME,
    AccessClaimsDTO,
    ExpiredToken,
    InvalidToken,
    decode_access_token,
)
from modules.identity.models import Account

if TYPE_CHECKING:
    # drf_spectacular.openapi import rest_framework.generics → views; module này được nạp từ
    # DEFAULT_AUTHENTICATION_CLASSES lúc rest_framework.views đang import nên gây vòng
    from drf_spectacular.openapi import AutoSchema

logger = structlog.get_logger(__name__)


class TokenRejected(exceptions.AuthenticationFailed):
    """Token sai chữ ký/claims/mục đích hoặc không còn khớp trạng thái auth trong DB."""

    default_code = "not_authenticated"
    default_detail = _("Thông tin xác thực không hợp lệ.")


class TokenExpired(exceptions.AuthenticationFailed):
    default_code = "token_expired"
    default_detail = _("Phiên đăng nhập đã hết hạn.")


class AuthStateUnavailable(exceptions.APIException):
    """DB không đọc được nên không xác minh được trạng thái auth: fail-closed (05 mục 2.2)."""

    status_code = 503
    default_code = "auth_state_unavailable"
    default_detail = _("Chưa xác minh được phiên đăng nhập, vui lòng thử lại.")


class JWTAuthentication(BaseAuthentication):
    """`Authorization: Bearer <access token>` với `aud` back-office.

    Không có header Bearer thì trả `None` để permission quyết định (401 cho endpoint cần đăng
    nhập). Token storefront sẽ có authenticator riêng theo audience của nhánh route.
    """

    def authenticate(self, request: Request) -> tuple[Account, dict[str, Any]] | None:
        parts = get_authorization_header(request).split()
        if not parts or parts[0].lower() != AUTH_SCHEME.lower().encode():
            return None
        if len(parts) != 2:
            raise TokenRejected
        claims = self._verify(parts[1])
        account = self._load_account(claims)
        if (
            account is None
            or not account.is_active
            or account.kind != claims.kind
            or account.token_version != claims.token_version
        ):
            raise TokenRejected
        auth = {
            "aud": claims.audience,
            "jti": str(claims.jti),
            "kind": claims.kind,
            "tv": claims.token_version,
        }
        return account, auth

    def authenticate_header(self, request: Request) -> str:
        return f'{AUTH_SCHEME} realm="api"'

    def _verify(self, raw_token: bytes) -> AccessClaimsDTO:
        try:
            return decode_access_token(
                raw_token.decode("ascii"),
                expected_audience=settings.JWT_AUDIENCE_BACKOFFICE,
                now=timezone.now(),
            )
        except ExpiredToken:
            raise TokenExpired from None
        except InvalidToken, UnicodeDecodeError:
            raise TokenRejected from None

    def _load_account(self, claims: AccessClaimsDTO) -> Account | None:
        try:
            return Account.objects.filter(pk=claims.subject).first()
        except DatabaseError:
            # Lỗi gốc có thể chứa host/connection string: không log, không nối exception
            logger.warning("auth_state_unavailable")
            raise AuthStateUnavailable from None


class JWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """Khai báo security scheme Bearer JWT cho drf-spectacular."""

    target_class = JWTAuthentication
    name = "BackofficeBearer"

    def get_security_definition(self, auto_schema: AutoSchema) -> dict[str, Any]:
        definition: dict[str, Any] = build_bearer_security_scheme_object(
            header_name="AUTHORIZATION", token_prefix=AUTH_SCHEME, bearer_format="JWT"
        )
        return definition
