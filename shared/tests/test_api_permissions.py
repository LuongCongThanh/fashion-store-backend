from types import SimpleNamespace
from typing import Any, cast

import pytest
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from shared.api.permissions import IsAdmin, IsCustomer, IsStaff
from shared.tests._helpers import drf_request

MISSING = object()


def _request(kind: Any = MISSING, aud: Any = MISSING) -> Request:
    # Account chưa có ở M0: dùng đối tượng giả có `kind` và claims giả có `aud`
    request = drf_request()
    user = SimpleNamespace() if kind is MISSING else SimpleNamespace(kind=kind)
    request.user = cast(Any, user)
    request.auth = {} if aud is MISSING else {"aud": aud}
    return request


@pytest.mark.parametrize(
    ("permission", "kind", "aud", "allowed"),
    [
        (IsCustomer, "customer", "store", True),
        (IsCustomer, "customer", "backoffice", False),
        (IsCustomer, "staff", "store", False),
        (IsStaff, "staff", "backoffice", True),
        (IsStaff, "admin", "backoffice", True),
        (IsStaff, "staff", "store", False),
        (IsStaff, "customer", "backoffice", False),
        (IsAdmin, "admin", "backoffice", True),
        (IsAdmin, "staff", "backoffice", False),
        (IsAdmin, "admin", "store", False),
    ],
)
def test_permission_checks_kind_and_aud(
    permission: type[BasePermission], kind: str, aud: str, allowed: bool
) -> None:
    assert permission().has_permission(_request(kind, aud), view=None) is allowed  # type: ignore[arg-type]


@pytest.mark.parametrize("permission", [IsCustomer, IsStaff, IsAdmin])
@pytest.mark.parametrize(
    "request_kwargs",
    [{"aud": "store"}, {"kind": "admin"}, {}],
    ids=["missing_kind", "missing_aud", "missing_both"],
)
def test_permission_denies_when_kind_or_aud_missing(
    permission: type[BasePermission], request_kwargs: dict[str, str]
) -> None:
    assert permission().has_permission(_request(**request_kwargs), view=None) is False  # type: ignore[arg-type]


@pytest.mark.parametrize("permission", [IsCustomer, IsStaff, IsAdmin])
def test_permission_denies_anonymous(permission: type[BasePermission]) -> None:
    request = drf_request()
    request.user = cast(Any, None)
    request.auth = None

    assert permission().has_permission(request, view=None) is False  # type: ignore[arg-type]
