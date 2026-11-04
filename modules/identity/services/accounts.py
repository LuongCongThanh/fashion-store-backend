"""Tạo và quản lý Tài khoản (02 mục 6.1, 7.1)."""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.db import IntegrityError, transaction

from modules.identity.constants import AccountKind
from modules.identity.exceptions import EmailAlreadyUsed, InvalidEmail, WeakPassword
from modules.identity.models import Account

STAFF_KINDS = frozenset({AccountKind.STAFF, AccountKind.ADMIN})
EMAIL_MAX_LENGTH = 254
EMAIL_UNIQUE_CONSTRAINT = "identity_account_email_lower_uniq"


def create_staff_account(
    *, email: str, password: str, kind: AccountKind, full_name: str = ""
) -> Account:
    """Tạo Tài khoản Staff hoặc Admin cho back-office (US-1001 AC2, AC3).

    Email được chuẩn hoá về chữ thường; mỗi email thuộc tối đa một Tài khoản với mọi `kind`
    (05 mục 2.3). Mật khẩu kiểm bằng `AUTH_PASSWORD_VALIDATORS` (05 mục 3).

    Raises:
        InvalidEmail: Email rỗng, sai định dạng hoặc dài quá 254 ký tự.
        WeakPassword: Mật khẩu không qua validator; `details["messages"]` mang thông báo.
        EmailAlreadyUsed: Email đã thuộc một Tài khoản khác, không phân biệt hoa thường.
        ValueError: `kind` không phải `staff` hoặc `admin` (lỗi của bên gọi).
    """
    if kind not in STAFF_KINDS:
        raise ValueError(f"create_staff_account không tạo Tài khoản kind={kind}")
    account = Account(email=Account.objects.normalize_email(email), kind=kind, full_name=full_name)
    _validate_email(account.email)
    try:
        # Account chưa lưu để validator so mật khẩu với email, họ tên
        validate_password(password, user=account)
    except ValidationError as exc:
        raise WeakPassword(details={"messages": list(exc.messages)}) from exc
    account.set_password(password)
    try:
        with transaction.atomic():
            account.save()
    except IntegrityError as exc:
        if _violated_constraint(exc) == EMAIL_UNIQUE_CONSTRAINT:
            raise EmailAlreadyUsed() from exc
        raise
    return account


def _validate_email(email: str) -> None:
    if not email or len(email) > EMAIL_MAX_LENGTH:
        raise InvalidEmail()
    try:
        EmailValidator()(email)
    except ValidationError as exc:
        raise InvalidEmail() from exc


def _violated_constraint(exc: IntegrityError) -> str | None:
    # Django bọc lỗi của psycopg; tên ràng buộc nằm ở `diag` của lỗi gốc
    diag = getattr(exc.__cause__, "diag", None)
    return getattr(diag, "constraint_name", None)
