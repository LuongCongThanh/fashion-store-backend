"""Đăng nhập, xoay refresh token và đăng xuất của identity (05 mục 2.1, 2.2, 3)."""

import hashlib
import hmac
import json
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Protocol

import structlog
from django.conf import settings
from django.db import DatabaseError, transaction
from django.utils import timezone

from apps.identity.auth.login_attempts import LoginReservation
from apps.identity.auth.replay_crypto import (
    ReplayUnavailable,
    SealedReplay,
    decrypt_replay,
    encrypt_replay,
)
from apps.identity.auth.tokens import (
    ExpiredToken,
    InvalidToken,
    RefreshClaimsDTO,
    TokenPairDTO,
    decode_refresh_token,
    issue_token_pair,
)
from apps.identity.constants import BACKOFFICE_KINDS
from apps.identity.exceptions import (
    InvalidCredentials,
    RefreshExpired,
    RefreshRejected,
    RefreshReplayUnavailable,
    RefreshSuperseded,
    SessionStateUnavailable,
)
from apps.identity.models import Account, RefreshReplay, RefreshToken

logger = structlog.get_logger(__name__)

# Cửa sổ trả lại đúng response đã cấp, tính từ `used_at`, không gia hạn (ADR 0014)
REFRESH_REPLAY_WINDOW = timedelta(seconds=10)


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
        issued = issue_token_pair(
            account=account, audience=settings.JWT_AUDIENCE_BACKOFFICE, now=timezone.now()
        )
        RefreshToken.objects.create(
            jti=issued.refresh_jti,
            account=account,
            family_id=issued.family_id,
            token_hash=_hash_token(issued.refresh_token),
            expires_at=issued.refresh_expires_at,
        )
    return issued.pair


def refresh_session(*, refresh_token: str, audience: str, now: datetime) -> TokenPairDTO:
    """Đổi refresh token lấy đúng một successor cùng family (05 mục 2.1; ADR 0014).

    Khoá Account rồi RefreshToken, kiểm trạng thái từ DB. Lần đầu phát cặp mới, đánh dấu
    predecessor và lưu replay mã hoá trong cùng transaction. Retry trước `used_at + 10 giây`
    nhận lại đúng cặp đã cấp, không gia hạn cửa sổ; dùng lại sau cửa sổ thu hồi cả family (đã
    commit khi lỗi trả về).

    Raises:
        RefreshRejected: Token sai chữ ký/claim/mục đích, hash lệch, không có trong DB, family
            đã thu hồi, Tài khoản vô hiệu hay lệch `kind`/`tv`, hoặc dùng lại ngoài cửa sổ.
        RefreshExpired: Refresh token đã hết hạn.
        RefreshSuperseded: Retry trong cửa sổ nhưng successor đã dùng hoặc đã thu hồi.
        RefreshReplayUnavailable: Thiếu khoá replay, hoặc trong cửa sổ mà replay mất/hỏng.
        SessionStateUnavailable: DB không đọc/ghi được.
    """
    claims = _verify_refresh_token(refresh_token, audience=audience, now=now)
    try:
        with transaction.atomic():
            account, token = _lock_session(claims=claims, refresh_token=refresh_token, now=now)
            if token.used_at is None:
                return _rotate(account=account, parent=token, audience=audience, now=now)
            if now < token.used_at + REFRESH_REPLAY_WINDOW:
                return _replay(parent=token, audience=audience, now=now)
            _revoke_family(family_id=token.family_id, now=now)
    except DatabaseError:
        # Lỗi gốc có thể chứa host/connection string: không log, không nối exception
        logger.warning("auth_state_unavailable")
        raise SessionStateUnavailable from None
    logger.warning(
        "refresh_reuse_detected", account_id=str(claims.subject), family_id=str(claims.family_id)
    )
    raise RefreshRejected


def logout_session(*, refresh_token: str, audience: str, now: datetime) -> None:
    """Đăng xuất: thu hồi family của refresh token và xoá replay của nó (05 mục 2.2).

    Chỉ cần chữ ký, audience và `token_use` đúng; token hết hạn vẫn đăng xuất được. Family đã
    thu hồi hay `jti` không còn trong DB vẫn thành công (idempotent). Không tăng `tv` và không
    đụng family khác.

    Raises:
        RefreshRejected: Token sai chữ ký/claim/audience/mục đích.
        SessionStateUnavailable: DB không đọc/ghi được.
    """
    claims = _verify_refresh_token(refresh_token, audience=audience, now=now, verify_exp=False)
    try:
        with transaction.atomic():
            # Cùng thứ tự khoá Account → token với refresh để không chen successor giữa chừng
            Account.objects.select_for_update().filter(pk=claims.subject).first()
            family = RefreshToken.objects.select_for_update().filter(
                family_id=claims.family_id, account_id=claims.subject
            )
            list(family.order_by("id"))
            _revoke_family(family_id=claims.family_id, now=now)
    except DatabaseError:
        logger.warning("auth_state_unavailable")
        raise SessionStateUnavailable from None
    logger.info(
        "session_logged_out", account_id=str(claims.subject), family_id=str(claims.family_id)
    )


def _verify_refresh_token(
    refresh_token: str, *, audience: str, now: datetime, verify_exp: bool = True
) -> RefreshClaimsDTO:
    try:
        return decode_refresh_token(
            refresh_token, expected_audience=audience, now=now, verify_exp=verify_exp
        )
    except ExpiredToken:
        raise RefreshExpired from None
    except InvalidToken:
        raise RefreshRejected from None


def _lock_session(
    *, claims: RefreshClaimsDTO, refresh_token: str, now: datetime
) -> tuple[Account, RefreshToken]:
    """Khoá Account rồi RefreshToken (thứ tự khoá 05 mục 2.1) và kiểm trạng thái auth từ DB."""
    account = Account.objects.select_for_update().filter(pk=claims.subject).first()
    token = RefreshToken.objects.select_for_update().filter(jti=claims.jti).first()
    if (
        account is None
        or token is None
        or token.account_id != account.pk
        or token.family_id != claims.family_id
        or not hmac.compare_digest(token.token_hash, _hash_token(refresh_token))
        or token.revoked_at is not None
        or token.expires_at <= now
        or not account.is_active
        or account.kind != claims.kind
        or account.token_version != claims.token_version
    ):
        raise RefreshRejected
    return account, token


def _rotate(
    *, account: Account, parent: RefreshToken, audience: str, now: datetime
) -> TokenPairDTO:
    issued = issue_token_pair(
        account=account, audience=audience, now=now, family_id=parent.family_id
    )
    try:
        sealed = encrypt_replay(
            json.dumps(asdict(issued.pair)).encode(),
            parent_jti=parent.jti,
            family_id=parent.family_id,
            audience=audience,
        )
    except ReplayUnavailable:
        # Không lưu được replay thì không cấp successor: retry sẽ tạo nhánh thứ hai (ADR 0014)
        logger.warning("refresh_replay_unavailable", family_id=str(parent.family_id))
        raise RefreshReplayUnavailable from None
    successor = RefreshToken.objects.create(
        jti=issued.refresh_jti,
        account=account,
        family_id=issued.family_id,
        token_hash=_hash_token(issued.refresh_token),
        expires_at=issued.refresh_expires_at,
    )
    parent.mark_used(successor=successor, now=now)
    RefreshReplay.objects.create(
        parent=parent,
        encryption_key_id=sealed.key_id,
        nonce=sealed.nonce,
        response_ciphertext=sealed.ciphertext,
        expires_at=now + REFRESH_REPLAY_WINDOW,
    )
    logger.info("refresh_rotated", account_id=str(account.pk), family_id=str(parent.family_id))
    return issued.pair


def _replay(*, parent: RefreshToken, audience: str, now: datetime) -> TokenPairDTO:
    successor = parent.successor
    is_superseded = successor is not None and (
        successor.used_at is not None or successor.revoked_at is not None
    )
    if is_superseded:
        raise RefreshSuperseded
    replay = RefreshReplay.objects.filter(parent=parent, expires_at__gt=now).first()
    try:
        if replay is None:
            raise ReplayUnavailable("Refresh replay is missing")
        payload = decrypt_replay(
            SealedReplay(
                key_id=replay.encryption_key_id,
                nonce=bytes(replay.nonce),
                ciphertext=bytes(replay.response_ciphertext),
            ),
            parent_jti=parent.jti,
            family_id=parent.family_id,
            audience=audience,
        )
        return TokenPairDTO(**json.loads(payload))
    except ReplayUnavailable, ValueError, TypeError:
        logger.warning("refresh_replay_unavailable", family_id=str(parent.family_id))
        raise RefreshReplayUnavailable from None


def _revoke_family(*, family_id: uuid.UUID, now: datetime) -> None:
    """Thu hồi family và xoá replay của nó; replay không được khôi phục phiên đã thu hồi."""
    RefreshToken.revoke_family(family_id, now=now)
    RefreshReplay.objects.filter(parent__family_id=family_id).delete()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
