"""Hai refresh đồng thời bằng cùng token chỉ tạo một successor (05 mục 2.1, 9; ADR 0014)."""

import os
import threading
from typing import Any

import pytest
from django.db import connection
from django.utils import timezone

from apps.identity.auth.tokens import TokenPairDTO
from apps.identity.models import RefreshReplay, RefreshToken
from apps.identity.services.auth import refresh_session
from apps.identity.tests.factories import AccountFactory, stored_refresh_session

AUDIENCE = "backoffice"


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("jwt_keyring")
def test_concurrent_refresh_creates_one_successor(settings: Any) -> None:
    settings.REFRESH_REPLAY_KEY_ID = "test-replay-1"
    settings.REFRESH_REPLAY_KEY = os.urandom(32)
    login = stored_refresh_session(account=AccountFactory.create(), now=timezone.now())
    barrier = threading.Barrier(2)
    pairs: list[TokenPairDTO] = []
    errors: list[BaseException] = []

    def run() -> None:
        try:
            barrier.wait()
            pairs.append(
                refresh_session(
                    refresh_token=login.refresh_token, audience=AUDIENCE, now=timezone.now()
                )
            )
        except BaseException as exc:
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert pairs[0] == pairs[1]
    assert RefreshToken.objects.filter(family_id=login.family_id).count() == 2
    assert RefreshReplay.objects.filter(parent__jti=login.refresh_jti).count() == 1
