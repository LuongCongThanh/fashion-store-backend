import copy
from collections.abc import Iterator
from typing import Any

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.identity.constants import AccountKind
from apps.identity.management.commands.seed_dev import SEED_ACCOUNTS
from apps.identity.models import Account

# Ghi đè DATABASES là cố ý: lệnh chỉ đọc HOST để chặn, kết nối test không đổi
pytestmark = [
    pytest.mark.django_db,
    pytest.mark.filterwarnings("ignore:Overriding setting DATABASES"),
]


def _databases(host: str) -> dict[str, Any]:
    databases = copy.deepcopy(settings.DATABASES)
    databases["default"]["HOST"] = host
    return databases


@pytest.fixture
def dev_settings() -> Iterator[None]:
    with override_settings(DEBUG=True, DATABASES=_databases("localhost")):
        yield


@pytest.mark.usefixtures("dev_settings")
def test_seed_dev_creates_admin_and_staff_with_working_passwords() -> None:
    call_command("seed_dev")

    for seed in SEED_ACCOUNTS:
        account = Account.objects.get(email=seed.email)
        assert account.kind == seed.kind
        assert account.check_password(seed.password)
    assert {seed.kind for seed in SEED_ACCOUNTS} == {AccountKind.ADMIN, AccountKind.STAFF}


@pytest.mark.usefixtures("dev_settings")
def test_seed_dev_twice_keeps_existing_accounts() -> None:
    call_command("seed_dev")
    ids = set(Account.objects.values_list("id", flat=True))

    call_command("seed_dev")

    assert set(Account.objects.values_list("id", flat=True)) == ids


@pytest.mark.parametrize(
    ("debug", "host", "message"),
    [(False, "localhost", "DEBUG"), (True, "db.example.com", "localhost")],
)
def test_seed_dev_refuses_outside_local_dev(debug: bool, host: str, message: str) -> None:
    with (
        override_settings(DEBUG=debug, DATABASES=_databases(host)),
        pytest.raises(CommandError, match=message),
    ):
        call_command("seed_dev")

    assert not Account.objects.exists()
