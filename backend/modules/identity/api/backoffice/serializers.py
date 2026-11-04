from typing import Any

from rest_framework import serializers


class BackofficeLoginInputSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class TokenPairOutputSerializer(serializers.Serializer[Any]):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField()
    expires_in = serializers.IntegerField(min_value=1)
