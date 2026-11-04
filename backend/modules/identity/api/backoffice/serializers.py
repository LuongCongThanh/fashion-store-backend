from typing import Any

from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

from modules.identity.constants import AccountKind, Language


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Staff login",
            value={"email": "staff@example.com", "password": "correct-horse-battery"},
            request_only=True,
        )
    ]
)
class LoginInput(serializers.Serializer[Any]):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


@extend_schema_serializer(
    component_name="TokenPairDTO",
    examples=[
        OpenApiExample(
            "Token pair",
            value={
                "access_token": "eyJhbGciOiJIUzI1NiJ9.example-access.signature",
                "refresh_token": "eyJhbGciOiJIUzI1NiJ9.example-refresh.signature",
                "token_type": "Bearer",
                "expires_in": 600,
            },
            response_only=True,
        )
    ],
)
class TokenPairOutput(serializers.Serializer[Any]):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField()
    expires_in = serializers.IntegerField(min_value=1)


@extend_schema_serializer(
    component_name="AccountDTO",
    examples=[
        OpenApiExample(
            "Staff account",
            value={
                "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                "created_at": "2026-01-15T08:30:00+07:00",
                "updated_at": "2026-03-02T10:00:00+07:00",
                "email": "staff@example.com",
                "kind": "staff",
                "full_name": "Example Staff",
                "phone": "+84900000000",
                "language": "vi",
                "is_active": True,
                "email_verified": True,
            },
            response_only=True,
        )
    ],
)
class AccountOutput(serializers.Serializer[Any]):
    """`AccountDTO` (04 mục 5.4): không có mật khẩu, `token_version` hay token."""

    id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    email = serializers.EmailField()
    kind = serializers.ChoiceField(choices=AccountKind.choices)
    full_name = serializers.CharField()
    phone = serializers.CharField()
    language = serializers.ChoiceField(choices=Language.choices)
    is_active = serializers.BooleanField()
    email_verified = serializers.BooleanField()
