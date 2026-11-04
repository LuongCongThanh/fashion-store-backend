from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import exceptions, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.api.backoffice.serializers import (
    AccountOutput,
    LoginInput,
    TokenPairOutput,
)
from apps.identity.auth.authentication import JWTAuthentication
from apps.identity.auth.login_attempts import (
    LoginRateLimited,
    get_login_ledger,
)
from apps.identity.services.auth import login_backoffice
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
