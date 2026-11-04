"""Payload sự kiện không chứa secret hay PII, xét theo tên field (07 mục 2, mục 5).

Đặt ở `tests/tooling/` để thấy sự kiện của mọi module. Test chỉ bắt lỗi theo tên field;
reviewer vẫn phải đọc payload của mọi sự kiện mới.
"""

from shared.events import DomainEvent
from shared.events.registry import autodiscover, registry

FORBIDDEN_SUBSTRINGS = ("email", "phone", "address", "name", "token", "password")


def forbidden_field_names(event_class: type[DomainEvent]) -> list[str]:
    return [
        field
        for field in event_class.model_fields
        if field.endswith("_url") or any(word in field for word in FORBIDDEN_SUBSTRINGS)
    ]


def test_forbidden_field_names_detected() -> None:
    class LeakyV1(DomainEvent):
        order_code: str
        contact_name: str
        reset_token: str
        to_address: str
        avatar_url: str
        amount: int

    assert forbidden_field_names(LeakyV1) == [
        "contact_name",
        "reset_token",
        "to_address",
        "avatar_url",
    ]


def test_registered_event_payloads_have_no_pii() -> None:
    # `ModulesConfig.ready()` đã nạp; gọi lại để test không phụ thuộc thứ tự khởi động
    autodiscover("modules")

    leaks = {
        f"{cls.event_type} v{cls.schema_version}": names
        for cls in registry.event_classes()
        if (names := forbidden_field_names(cls))
    }

    assert leaks == {}
