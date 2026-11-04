from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.identity.api.backoffice.serializers import (
    BackofficeLoginInputSerializer,
    TokenPairOutputSerializer,
)
from modules.identity.auth.login_attempts import (
    LoginRateLimited,
    get_login_ledger,
)
from modules.identity.services.auth import login_backoffice
from shared.api.client_ip import get_client_ip
from shared.api.exception_handler import current_request_id


class BackofficeLoginView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        request=BackofficeLoginInputSerializer,
        responses={200: TokenPairOutputSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = BackofficeLoginInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            pair = login_backoffice(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
                client_ip=get_client_ip(request),
                request_id=current_request_id(),
                ledger=get_login_ledger(),
            )
        except LoginRateLimited as exc:
            raise exceptions.Throttled(wait=exc.retry_after) from exc
        output = TokenPairOutputSerializer(pair)
        return Response(output.data, status=status.HTTP_200_OK)
