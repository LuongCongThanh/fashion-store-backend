"""Sự kiện mẫu, registry cô lập và model test-only cho test của `shared.events`."""

from collections.abc import Iterator
from typing import ClassVar

import pytest
from django.db import connection, models

from shared.events.base import DomainEvent
from shared.events.registry import registry


class SampleHappenedV1(DomainEvent):
    event_type = "shared.sample-happened"
    schema_version = 1

    order_code: str
    amount: int


class HandlerEffect(models.Model):
    """Tác động DB của handler mẫu, để kiểm tra commit/rollback cùng delivery."""

    handler = models.CharField(max_length=100)
    order_code = models.CharField(max_length=32)

    # Khai báo tường minh để mypy thấy manager khi model đi qua tham số `type[HandlerEffect]`
    objects: ClassVar[models.Manager[HandlerEffect]] = models.Manager()

    class Meta:
        app_label = "shared"
        db_table = "shared_test_handler_effect"

    def __str__(self) -> str:
        return f"{self.handler} {self.order_code}"


@pytest.fixture(autouse=True)
def _isolated_registry() -> Iterator[None]:
    # Sự kiện/handler khai báo trong test chỉ sống trong test đó
    with registry.isolated():
        yield


@pytest.fixture
def handler_effect_table(db: None) -> Iterator[type[HandlerEffect]]:
    # Model chỉ dùng trong test, không có migration
    with connection.schema_editor() as editor:
        editor.create_model(HandlerEffect)
    yield HandlerEffect
    with connection.schema_editor() as editor:
        editor.delete_model(HandlerEffect)
