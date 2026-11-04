"""Lỗi nghiệp vụ của identity (02 mục 6.1)."""

from django.utils.translation import gettext_lazy as _

from common.exceptions import DomainError


class EmailAlreadyUsed(DomainError):
    """Email đã thuộc một Tài khoản khác, không phân biệt hoa thường và `kind` (05 mục 2.3)."""

    code = "EMAIL_ALREADY_USED"
    http_status = 409
    message = _("Email đã được dùng cho một Tài khoản khác.")


class InvalidEmail(DomainError):
    """Email rỗng, sai định dạng hoặc dài quá 254 ký tự (03 mục 2.1)."""

    code = "INVALID_EMAIL"
    http_status = 422
    message = _("Email không hợp lệ.")


class WeakPassword(DomainError):
    """Mật khẩu không qua `AUTH_PASSWORD_VALIDATORS` (05 mục 3).

    `details["messages"]` là danh sách thông báo của các validator không đạt.
    """

    code = "WEAK_PASSWORD"
    http_status = 422
    message = _("Mật khẩu chưa đủ mạnh.")


class InvalidCredentials(DomainError):
    """Lỗi chung cho mọi nguyên nhân đăng nhập không hợp lệ."""

    code = "INVALID_CREDENTIALS"
    http_status = 401
    message = _("Email hoặc mật khẩu không hợp lệ.")


class RefreshRejected(DomainError):
    """Refresh/logout token sai chữ ký/claim/mục đích hoặc không khớp trạng thái trong DB.

    Gồm cả family đã thu hồi và token dùng lại ngoài cửa sổ replay (05 mục 2.1). Không nêu
    nguyên nhân để không giúp dò token.
    """

    code = "NOT_AUTHENTICATED"
    http_status = 401
    message = _("Thông tin xác thực không hợp lệ.")


class RefreshExpired(DomainError):
    """Refresh token có chữ ký hợp lệ nhưng đã hết hạn."""

    code = "TOKEN_EXPIRED"
    http_status = 401
    message = _("Phiên đăng nhập đã hết hạn.")


class RefreshSuperseded(DomainError):
    """Successor của refresh token đã được dùng; client giữ cặp token mới hơn (ADR 0014)."""

    code = "REFRESH_SUPERSEDED"
    http_status = 409
    message = _("Refresh token đã được thay bằng token mới hơn.")


class RefreshReplayUnavailable(DomainError):
    """Không trả lại được response refresh đã cấp (mất/hỏng ciphertext, thiếu khoá) hoặc không
    lưu được replay cho lần refresh đầu; không cấp nhánh token khác (05 mục 2.1)."""

    code = "REFRESH_REPLAY_UNAVAILABLE"
    http_status = 503
    message = _("Chưa làm mới được phiên đăng nhập, vui lòng thử lại.")


class SessionStateUnavailable(DomainError):
    """DB không đọc/ghi được trạng thái phiên: fail-closed (05 mục 2.2)."""

    code = "AUTH_STATE_UNAVAILABLE"
    http_status = 503
    message = _("Chưa xác minh được phiên đăng nhập, vui lòng thử lại.")
