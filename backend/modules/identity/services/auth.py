"""Đăng nhập và phát phiên của identity."""

import hashlib
import uuid
from typing import Any, Protocol

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from modules.identity.auth.tokens import TokenPairDTO, issue_token_pair
from modules.identity.constants import AccountKind
from modules.identity.exceptions import InvalidCredentials
from modules.identity.models import Account, RefreshToken


class AttemptLedger(Protocol):
    def reserve(self, *, email: str, client_ip: str, request_id: str) -> Any: ...

    def complete_failure(self, reservation: Any) -> None: ...

    def complete_success(self, reservation: Any) -> None: ...


def login_backoffice(
    *, email: str, password: str, client_ip: str, request_id: str, ledger: AttemptLedger
) -> TokenPairDTO:
    normalized_email = Account.objects.normalize_email(email)
    reservation = ledger.reserve(
        email=normalized_email, client_ip=client_ip, request_id=request_id or str(uuid.uuid4())
    )
    account = Account.objects.filter(email=normalized_email).first()
    if account is None:
        # Chạy cùng password framework để giảm khác biệt thời gian với email tồn tại.
        check_password(password, make_password(str(uuid.uuid4())))
        valid = False
    else:
        valid = account.check_password(password)
        valid = (
            valid
            and account.is_active
            and account.kind
            in {
                AccountKind.STAFF,
                AccountKind.ADMIN,
            }
        )
    if not valid or account is None:
        ledger.complete_failure(reservation)
        raise InvalidCredentials

    now = timezone.now()
    with transaction.atomic():
        pair = issue_token_pair(account=account, audience="backoffice", now=now)
        RefreshToken.objects.create(
            jti=pair.refresh_jti,
            account=account,
            family_id=pair.family_id,
            token_hash=hashlib.sha256(pair.refresh_token.encode()).hexdigest(),
            expires_at=pair.refresh_expires_at,
        )
    ledger.complete_success(reservation)
    return pair
