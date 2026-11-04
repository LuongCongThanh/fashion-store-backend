import sys
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

import pytest
import structlog
import time_machine
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction

from shared.events import DomainEvent, handles, publish
from shared.events.models import EventDelivery, OutboxEvent
from shared.events.registry import autodiscover, registry
from shared.events.tests._helpers import NOW, ORDER_CODE, Boom
from shared.events.tests.conftest import SampleHappenedV1

pytestmark = pytest.mark.django_db


@time_machine.travel(NOW, tick=False)
def test_publish_writes_outbox_row_in_current_transaction() -> None:
    with structlog.contextvars.bound_contextvars(request_id="req-1"):
        event = SampleHappenedV1(order_code=ORDER_CODE, amount=250000)

    with transaction.atomic():
        publish(event)
        row = OutboxEvent.objects.get()

    assert row.id == event.event_id
    assert row.id.version == 7
    assert row.event_type == "shared.sample-happened"
    assert row.schema_version == 1
    assert row.occurred_at == NOW
    assert row.payload == {
        "order_code": ORDER_CODE,
        "amount": 250000,
        "correlation_id": "req-1",
    }
    assert row.deliveries_created_at is None


def _publish_then_fail() -> None:
    with transaction.atomic():
        publish(SampleHappenedV1(order_code=ORDER_CODE, amount=1))
        raise Boom


def test_publish_rolled_back_with_transaction() -> None:
    with pytest.raises(Boom):
        _publish_then_fail()

    assert not OutboxEvent.objects.exists()


def test_handles_rejects_duplicate_name() -> None:
    @handles("shared.sample-happened", name="shared.record_sample")
    def first(event: SampleHappenedV1) -> None: ...

    with pytest.raises(ImproperlyConfigured, match=r"shared\.record_sample"):

        @handles("shared.sample-happened", version=1, name="shared.record_sample")
        def second(event: SampleHappenedV1) -> None: ...

    registered = registry.get_handler("shared.record_sample")
    assert registered is not None
    assert registered.func is first
    assert [h.name for h in registry.handlers_for("shared.sample-happened", 1)] == [
        "shared.record_sample"
    ]


def test_duplicate_event_class_rejected() -> None:
    assert registry.get_event_class("shared.sample-happened", 1) is SampleHappenedV1

    with pytest.raises(ImproperlyConfigured, match=r"shared\.sample-happened"):

        class OtherSampleV1(DomainEvent):
            event_type = "shared.sample-happened"
            schema_version = 1

    assert registry.get_event_class("shared.sample-happened", 1) is SampleHappenedV1


@pytest.mark.django_db(transaction=True)
def test_publish_outside_transaction_rejected() -> None:
    # Ghi outbox ngoài transaction thì sự kiện không commit/rollback cùng dữ liệu nghiệp vụ
    event = SampleHappenedV1(order_code=ORDER_CODE, amount=1)

    with pytest.raises(RuntimeError, match="transaction"):
        publish(event)

    assert not OutboxEvent.objects.exists()


def test_handles_rejects_name_longer_than_column() -> None:
    max_length = EventDelivery._meta.get_field("handler").max_length
    assert max_length is not None
    longest = "shared." + "x" * (max_length - len("shared."))
    handles("shared.sample-happened", name=longest)(lambda event: None)

    too_long = longest + "x"
    register = handles("shared.sample-happened", name=too_long)
    with pytest.raises(ImproperlyConfigured, match=str(max_length)):
        register(lambda event: None)

    assert registry.get_handler(too_long) is None


@pytest.fixture
def fake_modules(tmp_path: Path) -> Iterator[str]:
    """Package `fakemods` có module con đủ/thiếu file `events.py`, `handlers.py`."""
    root = tmp_path / "fakemods"
    files = {
        "__init__.py": "",
        "full/__init__.py": "",
        "full/events.py": "\n".join(
            [
                "from shared.events import DomainEvent",
                "class FakeThingDoneV1(DomainEvent):",
                "    event_type = 'full.thing-done'",
                "    schema_version = 1",
                "",
            ]
        ),
        "full/handlers.py": "\n".join(
            [
                "from shared.events import handles",
                "@handles('full.thing-done', name='full.on_thing_done')",
                "def on_thing_done(event): ...",
                "",
            ]
        ),
        "empty/__init__.py": "",
        "plain.py": "",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    try:
        yield "fakemods"
    finally:
        sys.path.remove(str(tmp_path))
        for name in [n for n in sys.modules if n == "fakemods" or n.startswith("fakemods.")]:
            del sys.modules[name]


def test_autodiscover_imports_events_and_handlers(fake_modules: str) -> None:
    autodiscover(fake_modules)

    assert registry.get_event_class("full.thing-done", 1) is not None
    assert [h.name for h in registry.handlers_for("full.thing-done", 1)] == ["full.on_thing_done"]
    # Module con không có events.py/handlers.py thì bỏ qua, không lỗi
    assert "fakemods.empty.events" not in sys.modules
    # Gọi lại không đăng ký trùng: module đã import không chạy lại
    autodiscover(fake_modules)


def test_modules_app_ready_autodiscovers_modules() -> None:
    with mock.patch("shared.events.registry.autodiscover") as discover:
        apps.get_app_config("modules").ready()

    discover.assert_called_once_with("modules")
