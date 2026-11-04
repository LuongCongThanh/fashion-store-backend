"""Class cơ sở của sự kiện miền (07 mục 1, 2).

Class con đặt ở `events.py` của module phát, tên `<Danh từ><Động từ quá khứ>V<n>` (13 mục 5),
khai báo `event_type = "<module>.<kebab-case>"` và `schema_version`. Payload chỉ mang ID, Mã đơn,
số tiền và mã trạng thái, không chứa secret hay PII (07 mục 2).
"""

from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID

import structlog
from django.utils import timezone
from pydantic import BaseModel, ConfigDict, Field

from common.events.registry import registry
from common.models import uuid7


def _current_request_id() -> str | None:
    # django-structlog gắn request_id của request gốc vào contextvars
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    return None if request_id is None else str(request_id)


class DomainEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_type: ClassVar[str]
    schema_version: ClassVar[int]

    event_id: UUID = Field(default_factory=uuid7)
    occurred_at: datetime = Field(default_factory=timezone.now)
    correlation_id: str | None = Field(default_factory=_current_request_id)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)
        # Class trung gian chưa khai báo loại sự kiện thì không đăng ký
        if hasattr(cls, "event_type") and hasattr(cls, "schema_version"):
            registry.register_event(cls)

    def to_payload(self) -> dict[str, Any]:
        """Nội dung lưu ở cột `payload`; `event_id`, `occurred_at` đã là cột riêng."""
        return self.model_dump(mode="json", exclude={"event_id", "occurred_at"})
