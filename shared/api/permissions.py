"""Lớp quyền theo `kind` của Account và `aud` của token (05 mục 4).

`kind` đọc từ `request.user`, `aud` đọc từ claims trong `request.auth`; thiếu một trong hai
thì từ chối. `IsOrderOwner` thuộc `modules/ordering`.
"""

from collections.abc import Mapping
from typing import Any, ClassVar

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class _KindAndAudience(BasePermission):
    kinds: ClassVar[frozenset[str]]
    audience: ClassVar[str]

    def has_permission(self, request: Request, view: APIView) -> bool:
        kind = getattr(request.user, "kind", None)
        claims: Any = request.auth
        aud = claims.get("aud") if isinstance(claims, Mapping) else None
        return kind in self.kinds and aud == self.audience


class IsCustomer(_KindAndAudience):
    kinds = frozenset({"customer"})
    audience = "store"


class IsStaff(_KindAndAudience):
    kinds = frozenset({"staff", "admin"})
    audience = "backoffice"


class IsAdmin(_KindAndAudience):
    kinds = frozenset({"admin"})
    audience = "backoffice"
