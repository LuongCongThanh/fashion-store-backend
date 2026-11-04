from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import exceptions, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.api.backoffice.serializers import (
    AccountOutput,
    LoginInput,
    LogoutInput,
    RefreshInput,
    TokenPairOutput,
)
from apps.identity.auth.authentication import JWTAuthentication
from apps.identity.auth.login_attempts import (
    LoginRateLimited,
    get_login_ledger,
)
from apps.identity.services.auth import login_backoffice, logout_session, refresh_session
from common.api.client_ip import get_client_ip
from common.api.permissions import IsStaff
from common.api.schema import EXAMPLE_REQUEST_ID, ErrorOutput


class BackofficeLoginView(APIView):
    # Login không đọc Bearer: token cũ hỏng hay hết hạn không được chặn việc đăng nhập lại
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Log in to the back office",
        request=LoginInput,
        responses={
            200: TokenPairOutput,
            401: OpenApiResponse(
                ErrorOutput,
                description="Invalid email or password (`INVALID_CREDENTIALS`).",
                examples=[
                    OpenApiExample(
                        "Invalid credentials",
                        value={
                            "error": {
                                "code": "INVALID_CREDENTIALS",
                                "message": "Invalid email or password.",
                                "details": {},
                                "request_id": EXAMPLE_REQUEST_ID,
                            }
                        },
                    )
                ],
            ),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = LoginInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            pair = login_backoffice(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
                client_ip=get_client_ip(request),
                ledger=get_login_ledger(),
            )
        except LoginRateLimited as exc:
            raise exceptions.Throttled(wait=exc.retry_after) from exc
        output = TokenPairOutput(pair)
        return Response(output.data, status=status.HTTP_200_OK)


class BackofficeMeView(APIView):
    # Khai báo tại view: DEFAULT_AUTHENTICATION_CLASSES để trống nên endpoint storefront công khai
    # không nhận nhầm Bearer audience back-office
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsStaff,)

    @extend_schema(summary="Get the signed-in staff account", responses={200: AccountOutput})
    def get(self, request: Request) -> Response:
        # `request.user` là Account vừa đọc từ PostgreSQL trong JWTAuthentication
        output = AccountOutput(request.user)
        return Response(output.data, status=status.HTTP_200_OK)


def _error_example(name: str, code: str, message: str) -> OpenApiExample:
    return OpenApiExample(
        name,
        value={
            "error": {
                "code": code,
                "message": message,
                "details": {},
                "request_id": EXAMPLE_REQUEST_ID,
            }
        },
    )


INVALID_REFRESH_TOKEN = _error_example(
    "Invalid refresh token", "NOT_AUTHENTICATED", "Invalid authentication credentials."
)
AUTH_STATE_UNAVAILABLE = _error_example(
    "Auth state unavailable",
    "AUTH_STATE_UNAVAILABLE",
    "Session state could not be verified, please retry.",
)


class BackofficeRefreshView(APIView):
    # Refresh không đọc Bearer: access token đã hết hạn là lý do client gọi endpoint này
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Rotate the back-office refresh token",
        request=RefreshInput,
        responses={
            200: TokenPairOutput,
            401: OpenApiResponse(
                ErrorOutput,
                description=(
                    "Refresh token is invalid, revoked or reused (`NOT_AUTHENTICATED`), "
                    "or expired (`TOKEN_EXPIRED`)."
                ),
                examples=[
                    INVALID_REFRESH_TOKEN,
                    _error_example("Token expired", "TOKEN_EXPIRED", "Session has expired."),
                ],
            ),
            409: OpenApiResponse(
                ErrorOutput,
                description=(
                    "The successor of this refresh token was already used; keep the newer "
                    "token pair (`REFRESH_SUPERSEDED`)."
                ),
                examples=[
                    _error_example(
                        "Refresh superseded",
                        "REFRESH_SUPERSEDED",
                        "Refresh token was replaced by a newer one.",
                    )
                ],
            ),
            503: OpenApiResponse(
                ErrorOutput,
                description=(
                    "Session state could not be read (`AUTH_STATE_UNAVAILABLE`) or the issued "
                    "pair cannot be returned again (`REFRESH_REPLAY_UNAVAILABLE`); retry later."
                ),
                examples=[
                    AUTH_STATE_UNAVAILABLE,
                    _error_example(
                        "Refresh replay unavailable",
                        "REFRESH_REPLAY_UNAVAILABLE",
                        "Session could not be refreshed, please retry.",
                    ),
                ],
            ),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = RefreshInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        pair = refresh_session(
            refresh_token=serializer.validated_data["refresh_token"],
            audience=settings.JWT_AUDIENCE_BACKOFFICE,
            now=timezone.now(),
        )
        output = TokenPairOutput(pair)
        return Response(output.data, status=status.HTTP_200_OK)


class BackofficeLogoutView(APIView):
    # Logout bằng refresh token, không cần access token còn hạn (04 mục 5.6)
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Log out of the back office",
        request=LogoutInput,
        responses={
            204: None,
            401: OpenApiResponse(
                ErrorOutput,
                description=(
                    "Refresh token has a wrong signature, audience or purpose "
                    "(`NOT_AUTHENTICATED`)."
                ),
                examples=[INVALID_REFRESH_TOKEN],
            ),
            503: OpenApiResponse(
                ErrorOutput,
                description=(
                    "Session state could not be updated in the database "
                    "(`AUTH_STATE_UNAVAILABLE`); retry later."
                ),
                examples=[AUTH_STATE_UNAVAILABLE],
            ),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = LogoutInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        logout_session(
            refresh_token=serializer.validated_data["refresh_token"],
            audience=settings.JWT_AUDIENCE_BACKOFFICE,
            now=timezone.now(),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
