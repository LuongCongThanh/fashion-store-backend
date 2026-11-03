"""Factory của identity (13 mục 9, 12 mục 4)."""

import factory
from factory.django import DjangoModelFactory

from modules.identity.constants import AccountKind
from modules.identity.models import Account

DEFAULT_PASSWORD = "Fashion-Store-2026"


class AccountFactory(DjangoModelFactory[Account]):
    """Tài khoản Staff đang hoạt động; trait `admin` cho Admin."""

    class Meta:
        model = Account

    email = factory.Sequence(lambda n: f"staff{n}@example.com")
    kind = AccountKind.STAFF
    password = factory.django.Password(DEFAULT_PASSWORD)

    class Params:
        admin = factory.Trait(kind=AccountKind.ADMIN)
