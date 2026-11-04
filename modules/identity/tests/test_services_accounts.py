import pytest
from django.db import IntegrityError

from modules.identity.constants import AccountKind
from modules.identity.exceptions import EmailAlreadyUsed, InvalidEmail, WeakPassword
from modules.identity.models import Account
from modules.identity.services.accounts import create_staff_account
from modules.identity.tests.factories import DEFAULT_PASSWORD, AccountFactory

pytestmark = pytest.mark.django_db


def test_create_staff_account_stores_lowercase_email() -> None:
    account = create_staff_account(
        email="  An.Nguyen@Example.COM ",
        password=DEFAULT_PASSWORD,
        kind=AccountKind.STAFF,
        full_name="Nguyễn An",
    )

    account.refresh_from_db()
    assert account.email == "an.nguyen@example.com"
    assert account.kind == AccountKind.STAFF
    assert account.full_name == "Nguyễn An"
    assert account.check_password(DEFAULT_PASSWORD)


def test_create_staff_account_rejects_email_used_ignoring_case() -> None:
    # Một email một Tài khoản với mọi `kind` (05 mục 2.3), kể cả Tài khoản Khách hàng
    AccountFactory(email="an.nguyen@example.com", kind=AccountKind.CUSTOMER)

    with pytest.raises(EmailAlreadyUsed):
        create_staff_account(
            email="An.Nguyen@Example.com", password=DEFAULT_PASSWORD, kind=AccountKind.STAFF
        )

    assert Account.objects.count() == 1


def test_create_staff_account_rejects_customer_kind() -> None:
    with pytest.raises(ValueError, match="customer"):
        create_staff_account(
            email="an.nguyen@example.com", password=DEFAULT_PASSWORD, kind=AccountKind.CUSTOMER
        )

    assert not Account.objects.exists()


@pytest.mark.parametrize(
    "email",
    [
        "   ",  # chỉ có khoảng trắng: chuẩn hoá xong là chuỗi rỗng
        "an.nguyen",  # sai định dạng
        "a" * 243 + "@example.com",  # 255 ký tự, quá 254
    ],
)
def test_create_staff_account_rejects_invalid_email(email: str) -> None:
    with pytest.raises(InvalidEmail):
        create_staff_account(email=email, password=DEFAULT_PASSWORD, kind=AccountKind.STAFF)

    assert not Account.objects.exists()


def test_create_staff_account_rejects_weak_password() -> None:
    # UserAttributeSimilarityValidator so mật khẩu với email của Account chưa lưu
    with pytest.raises(WeakPassword) as raised:
        create_staff_account(
            email="an.nguyen@example.com", password="an.nguyen.example", kind=AccountKind.STAFF
        )

    assert raised.value.code == "WEAK_PASSWORD"
    assert raised.value.http_status == 422
    assert len(raised.value.details["messages"]) >= 1
    assert not Account.objects.exists()


def test_create_staff_account_reraises_other_integrity_error() -> None:
    # Vi phạm NOT NULL của full_name, không phải ràng buộc email: không được đổi thành
    # EmailAlreadyUsed
    with pytest.raises(IntegrityError, match="full_name"):
        create_staff_account(
            email="an.nguyen@example.com",
            password=DEFAULT_PASSWORD,
            kind=AccountKind.STAFF,
            full_name=None,  # type: ignore[arg-type]
        )

    assert not Account.objects.exists()
