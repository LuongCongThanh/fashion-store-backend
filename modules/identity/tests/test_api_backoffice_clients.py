"""Fixture `staff_client`, `admin_client` của `conftest.py` ở gốc repo qua đúng permission."""

import pytest
from django.urls import path
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from modules.identity.auth.authentication import JWTAuthentication
from shared.api.permissions import IsAdmin, IsStaff

pytestmark = [pytest.mark.django_db, pytest.mark.urls(__name__)]


def _guarded_view(permission: type[BasePermission]) -> type[APIView]:
    class GuardedView(APIView):
        authentication_classes = (JWTAuthentication,)
        permission_classes = (permission,)

        def get(self, request: Request) -> Response:
            return Response({})

    return GuardedView


urlpatterns = [
    path("staff-only", _guarded_view(IsStaff).as_view()),
    path("admin-only", _guarded_view(IsAdmin).as_view()),
]


def test_staff_client_passes_is_staff(staff_client: APIClient) -> None:
    response = staff_client.get("/staff-only")

    assert response.status_code == 200


def test_admin_client_passes_is_admin(admin_client: APIClient) -> None:
    response = admin_client.get("/admin-only")

    assert response.status_code == 200


def test_staff_client_denied_by_is_admin(staff_client: APIClient) -> None:
    response = staff_client.get("/admin-only")

    assert response.status_code == 403
