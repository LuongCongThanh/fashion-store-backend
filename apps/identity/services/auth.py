"""Đăng nhập và phát phiên của identity."""

import hashlib
from typing import Protocol

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.identity.auth.login_attempts import LoginReservation
from apps.identity.auth.tokens import TokenPairDTO, issue_token_pair
from apps.identity.constants import BACKOFFICE_KINDS
from apps.identity.exceptions import InvalidCredentials
from apps.identity.models import Account, RefreshToken


class AttemptLedger(Protocol):
    def reserve(self, *, email: str, client_ip: str) -> LoginReservation: ...

    def complete_failure(self, reservation: LoginReservation) -> None: ...

    def complete_success(self, reservation: LoginReservation) -> None: ...

    def release(self, reservation: LoginReservation) -> None: ...


def login_backoffice(
    *, email: str, password: str, client_ip: str, ledger: AttemptLedger
) -> TokenPairDTO:
    """Đăng nhập back-office bằng email/mật khẩu và phát cặp token audience back-office.

    Giữ suất trong failure ledger trước khi thử mật khẩu (05 mục 5). Mọi nguyên nhân từ chối
    (email không tồn tại, sai mật khẩu, Khách hàng, Tài khoản vô hiệu) ghi một failure và dùng
    cùng một lỗi. Refresh token chỉ được lưu dạng SHA-256 cùng family.

    Raises:
        LoginRateLimited: Email hoặc IP đã chạm hạn mức đăng nhập sai.
        InvalidCredentials: Thông tin đăng nhập không hợp lệ, không nêu nguyên nhân.
    """
    normalized_email = Account.objects.normalize_email(email)
    reservation = ledger.reserve(email=normalized_email, client_ip=client_ip)
    try:
        account = _authenticate_backoffice(email=normalized_email, password=password)
        if account is None:
            ledger.complete_failure(reservation)
            raise InvalidCredentials
        pair = _issue_backoffice_session(account=account)
    except InvalidCredentials:
        raise
    except Exception:
        # Lỗi hạ tầng (DB, keyring) không phải lần đăng nhập sai: trả suất, không ghi failure
        ledger.release(reservation)
        raise
    ledger.complete_success(reservation)
    return pair


def _authenticate_backoffice(*, email: str, password: str) -> Account | None:
    account: Account | None = Account.objects.filter(email=email).first()
    if account is None:
        # Băm mật khẩu đúng một lần như nhánh email tồn tại (verify một lần) để thời gian xử lý
        # không lộ email nào có Tài khoản; cùng cách ModelBackend của Django
        Account().set_password(password)
        return None
    is_valid = account.check_password(password)
    if is_valid and account.is_active and account.kind in BACKOFFICE_KINDS:
        return account
    return None


def _issue_backoffice_session(*, account: Account) -> TokenPairDTO:
    with transaction.atomic():
        pair = issue_token_pair(
            account=account, audience=settings.JWT_AUDIENCE_BACKOFFICE, now=timezone.now()
        )
        RefreshToken.objects.create(
            jti=pair.refresh_jti,
            account=account,
            family_id=pair.family_id,
            token_hash=hashlib.sha256(pair.refresh_token.encode()).hexdigest(),
            expires_at=pair.refresh_expires_at,
        )
    return pair
