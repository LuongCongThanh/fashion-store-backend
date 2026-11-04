"""Chuẩn hoá số điện thoại Việt Nam về E.164 (03 mục 0.6)."""

import re

import phonenumbers
from django.utils.translation import gettext_lazy as _

INVALID_PHONE_MESSAGE = _("Số điện thoại không hợp lệ")

# Chỉ chữ số và dấu phân cách thường gặp; số trong nước bắt đầu bằng `0`, số quốc tế bằng `+`.
# Chặn trước khi gọi `phonenumbers.parse` vì thư viện tự đổi chữ cái thành số, tự bỏ extension
# và tự đoán mã nước khi thiếu `+`. `re.ASCII` để `\d` không khớp chữ số Unicode (full-width, Ả Rập)
_ALLOWED_FORMAT = re.compile(r"\s*\+?[\d\s().-]+", re.ASCII)
_SEPARATORS = re.compile(r"[\s().-]", re.ASCII)


class InvalidPhoneNumber(ValueError):
    """Không phải số hợp lệ thuộc Việt Nam. Serializer đổi thành lỗi validate của field."""

    def __init__(self) -> None:
        super().__init__(str(INVALID_PHONE_MESSAGE))


def normalize_vn_phone(raw: str) -> str:
    """Trả số E.164, ví dụ `0901234567` và `+84 901 234 567` đều thành `+84901234567`.

    Nhận mọi số hợp lệ thuộc Việt Nam, kể cả số cố định; số hợp lệ của nước khác bị từ chối.
    Không tự đoán: số thiếu đầu số, thiếu `+` trước mã nước, có chữ cái hoặc extension đều bị
    từ chối.

    Raises:
        InvalidPhoneNumber: đầu vào không phải số hợp lệ thuộc Việt Nam. Thông báo lỗi không
            chứa số gốc để không lọt vào log.
    """
    if not _ALLOWED_FORMAT.fullmatch(raw):
        raise InvalidPhoneNumber
    compact = _SEPARATORS.sub("", raw)
    # `00` là đầu quay số quốc tế: thiếu `+` trước mã nước, phonenumbers sẽ tự đoán
    if not compact.startswith(("0", "+")) or compact.startswith("00"):
        raise InvalidPhoneNumber
    try:
        number = phonenumbers.parse(compact, "VN")
    except phonenumbers.NumberParseException as exc:
        raise InvalidPhoneNumber from exc
    if not phonenumbers.is_valid_number_for_region(number, "VN"):
        raise InvalidPhoneNumber
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
