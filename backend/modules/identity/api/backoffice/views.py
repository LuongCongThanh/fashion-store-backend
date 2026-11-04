from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import exceptions, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.identity.api.backoffice.serializers import (
    AccountOutputSerializer,
    BackofficeLoginInputSerializer,
    TokenPairOutputSerializer,
)
from modules.identity.auth.authentication import JWTAuthentication
from modules.identity.auth.login_attempts import (
    LoginRateLimited,
    get_login_ledger,
)
from modules.identity.services.auth import login_backoffice
from shared.api.client_ip import get_client_ip
from shared.api.permissions import IsStaff
from shared.api.schema import ErrorOutput


class BackofficeLoginView(APIView):
    # Login không đọc Bearer: token cũ hỏng hay hết hạn không được chặn việc đăng nhập lại
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        request=BackofficeLoginInputSerializer,
        responses={
            200: TokenPairOutputSerializer,
            401: OpenApiResponse(
                ErrorOutput,
                description="Thông tin đăng nhập không hợp lệ (`INVALID_CREDENTIALS`).",
            ),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = BackofficeLoginInputSerializer(data=request.data)
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
        output = TokenPairOutputSerializer(pair)
        return Response(output.data, status=status.HTTP_200_OK)


class BackofficeMeView(APIView):
    # Khai báo tại view: DEFAULT_AUTHENTICATION_CLASSES để trống nên endpoint storefront công khai
    # không nhận nhầm Bearer audience back-office
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsStaff,)

    @extend_schema(responses={200: AccountOutputSerializer})
    def get(self, request: Request) -> Response:
        # `request.user` là Account vừa đọc từ PostgreSQL trong JWTAuthentication
        output = AccountOutputSerializer(request.user)
        return Response(output.data, status=status.HTTP_200_OK)
