"""Model cơ sở cho các bảng do dự án định nghĩa (03 mục 0.1, ADR 0008)."""

import uuid
from typing import Any

from django.db import models
from django.utils import timezone


def uuid7() -> uuid.UUID:
    # Migration ghi đường dẫn hàm này, không ghi `uuid.uuid7`: đổi cách sinh UUID chỉ cần sửa
    # thân hàm (ADR 0008)
    return uuid.uuid7()


class BaseQuerySet[M: models.Model](models.QuerySet[M]):
    """Giữ `updated_at` đúng cho các đường ghi bulk, nơi `auto_now` không chạy."""

    def update(self, **kwargs: Any) -> int:
        kwargs.setdefault("updated_at", timezone.now())
        return super().update(**kwargs)

    def bulk_update(self, objs: Any, fields: Any, batch_size: int | None = None) -> int:
        # `fields` có thể là generator: đổi sang list trước khi kiểm tra để không dùng hết nó.
        # Bên gọi có `updated_at` trong `fields` thì giữ giá trị riêng của từng object
        objs, fields = list(objs), list(fields)
        if "updated_at" not in fields:
            now = timezone.now()
            for obj in objs:
                obj.updated_at = now
            fields.append("updated_at")
        return super().bulk_update(objs, fields, batch_size=batch_size)


class UUIDv7Model(models.Model):
    """Khoá chính UUID v7 (ADR 0008), dùng chung cho mọi bảng do dự án định nghĩa."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    class Meta:
        abstract = True


class BaseModel(UUIDv7Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BaseQuerySet.as_manager()

    class Meta:
        abstract = True


# Django chỉ nhận model qua `<app>/models.py` (02 mục 4). Import ở cuối file vì
# model của package con cần `uuid7`, `BaseModel` ở trên
from shared.events.models import EventDelivery, OutboxEvent  # noqa: E402, F401
from shared.geo.models import Province, Ward  # noqa: E402, F401
from shared.idempotency.models import IdempotencyKey  # noqa: E402, F401
