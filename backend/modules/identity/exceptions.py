"""Lỗi nghiệp vụ của identity (02 mục 6.1)."""

from django.utils.translation import gettext_lazy as _

from shared.exceptions import DomainError


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
