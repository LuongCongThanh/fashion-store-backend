import pytest

from shared.phones import InvalidPhoneNumber, normalize_vn_phone


@pytest.mark.parametrize(
    "raw", ["0901234567", "+84 901 234 567", "+84901234567", "090-123-4567", "(090) 1234567"]
)
def test_normalizes_vietnamese_mobile_to_e164(raw: str) -> None:
    assert normalize_vn_phone(raw) == "+84901234567"


def test_accepts_vietnamese_landline() -> None:
    assert normalize_vn_phone("028 3822 1234") == "+842838221234"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "abc",
        "090123",  # thiếu số, không tự đoán
        "09012345678901",
        "+1 650 253 0000",  # số hợp lệ của nước khác
        "0901-CALL-ME",  # phonenumbers tự đổi chữ thành số
        "0901234567 ext 12",  # phonenumbers tự bỏ extension
        "84901234567",  # thiếu `+`, không tự đoán mã nước
        "0084901234567",  # đầu quay số quốc tế `00` thay cho `+`
        "+" + chr(0xFF18) + chr(0xFF14) + "901234567",  # chữ số full-width
        "+" + chr(0x0668) + chr(0x0664) + "901234567",  # chữ số Ả Rập
        "+84 901+234567",
    ],
)
def test_rejects_invalid_or_foreign_number(raw: str) -> None:
    with pytest.raises(InvalidPhoneNumber):
        normalize_vn_phone(raw)


def test_error_message_does_not_contain_input() -> None:
    with pytest.raises(InvalidPhoneNumber) as exc_info:
        normalize_vn_phone("0901 23")

    assert "0901" not in str(exc_info.value)
