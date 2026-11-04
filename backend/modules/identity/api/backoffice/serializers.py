from typing import Any

from rest_framework import serializers

from modules.identity.constants import AccountKind, Language


class BackofficeLoginInputSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class TokenPairOutputSerializer(serializers.Serializer[Any]):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField()
    expires_in = serializers.IntegerField(min_value=1)


class AccountOutputSerializer(serializers.Serializer[Any]):
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
