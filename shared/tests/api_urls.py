"""Urlconf chỉ dùng cho test của shared/api."""

from typing import Any, ClassVar

from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.db import models, transaction
from django.http import HttpRequest, HttpResponse
from django.urls import path
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import Throttled
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.api.client_ip import get_client_ip
from shared.api.throttling import AnonThrottle
from shared.exceptions import DomainError
from shared.idempotency import Claim
from shared.idempotency import http as idempotency

# Stub của DRF chỉ nhận QuerySet; paginator thật nhận mọi sequence, nên dùng list cho gọn
PAGED_ROWS: Any = [{"id": i} for i in range(1, 251)]

# Urlconf ghi đè ROOT_URLCONF nên phải khai báo lại handler như config/urls.py; test kiểm hai
# nơi khớp nhau
handler400 = "shared.api.views.bad_request"
handler403 = "shared.api.views.permission_denied"
handler404 = "shared.api.views.not_found"
handler500 = "shared.api.views.server_error"


class PagedListView(GenericAPIView[Any]):
    """Danh sách giả, phân trang bằng `DEFAULT_PAGINATION_CLASS` như view list thật."""

    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        paginator = self.paginator
        assert paginator is not None
        page: list[Any] | None = paginator.paginate_queryset(PAGED_ROWS, request, view=self)
        return paginator.get_paginated_response(page)


class AddressSerializer(serializers.Serializer[Any]):
    city = serializers.CharField()


class LineSerializer(serializers.Serializer[Any]):
    sku = serializers.CharField()


class ProfileSerializer(serializers.Serializer[Any]):
    name = serializers.CharField()
    address = AddressSerializer()
    lines = LineSerializer(many=True, required=False)


class ValidateView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request: Request) -> Response:
        serializer = ProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class OutOfStock(DomainError):
    code = "OUT_OF_STOCK"
    http_status = 409
    message = _("Một số Biến thể không đủ hàng.")


class DomainErrorView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        raise OutOfStock(details={"items": [{"sku": "A", "requested": 3, "available": 1}]})


class ThrottledView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        raise Throttled(wait=30)


class BoomView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        raise RuntimeError("secret internal detail")


class DefaultPermissionView(APIView):
    """Không khai báo `permission_classes`: dùng `DEFAULT_PERMISSION_CLASSES`."""

    def get(self, request: Request) -> Response:
        return Response({})


class ThrottleKeyView(APIView):
    """Trả IP đã xác minh và khoá mà `AnonThrottle` dùng, để test IP mà throttle thấy."""

    permission_classes = (AllowAny,)
    throttle_classes = ()

    def get(self, request: Request) -> Response:
        return Response(
            {
                "client_ip": get_client_ip(request),
                "key": AnonThrottle().get_cache_key(request, self),
            }
        )


class LanguageView(APIView):
    """Trả ngôn ngữ `LocaleMiddleware` đã chọn cho request."""

    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        return Response({"language": translation.get_language()})


class IdempotentEffect(models.Model):
    """Tác động nghiệp vụ của endpoint mẫu, để đếm số lần thật sự chạy."""

    note = models.CharField(max_length=100)

    # Khai báo tường minh để mypy thấy manager khi model đi qua tham số `type[...]`
    objects: ClassVar[models.Manager[IdempotentEffect]] = models.Manager()

    class Meta:
        app_label = "shared"
        db_table = "shared_test_idempotent_effect"

    def __str__(self) -> str:
        return self.note


class IdempotentCreateView(APIView):
    """Endpoint mẫu dùng `Idempotency-Key` như checkout: claim, ghi tác động, lưu kết quả.

    Body có `fail_after_effect` thì ném lỗi nghiệp vụ sau khi đã ghi tác động,
    `fail_after_complete` thì ném sau khi đã lưu kết quả, cùng transaction.
    """

    permission_classes = (AllowAny,)

    def post(self, request: Request, code: str) -> Response:
        outcome = idempotency.begin(request)
        if not isinstance(outcome, Claim):
            return idempotency.response(outcome)
        with outcome, transaction.atomic():
            effect = IdempotentEffect.objects.create(note=str(request.data.get("note", "")))
            if request.data.get("fail_after_effect"):
                raise OutOfStock
            body = {"effect_id": str(effect.pk), "operation_id": str(outcome.operation_id)}
            outcome.complete(201, body)
            if request.data.get("fail_after_complete"):
                raise OutOfStock
        return Response(body, status=201)

    # Cùng luồng với POST, để test scope tách theo method
    put = post


def suspicious_view(request: HttpRequest) -> HttpResponse:
    """View Django thường; Django đổi `SuspiciousOperation` thành 400 qua `handler400`."""
    raise SuspiciousOperation("secret internal detail")


def forbidden_view(request: HttpRequest) -> HttpResponse:
    """View Django thường, ngoài DRF: `PermissionDenied` đi qua `handler403`."""
    raise PermissionDenied


urlpatterns = [
    path("paged", PagedListView.as_view()),
    path("validate", ValidateView.as_view()),
    path("domain-error", DomainErrorView.as_view()),
    path("throttled", ThrottledView.as_view()),
    path("boom", BoomView.as_view()),
    path("private", DefaultPermissionView.as_view()),
    path("throttle-key", ThrottleKeyView.as_view()),
    path("suspicious", suspicious_view),
    path("forbidden", forbidden_view),
    path("language", LanguageView.as_view()),
    path("idempotent/<str:code>/", IdempotentCreateView.as_view()),
]
