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

from common.events import DomainEvent, handles, publish
from common.events.models import EventDelivery, OutboxEvent
from common.events.registry import autodiscover, registry
from common.tests.conftest import SampleHappenedV1
from common.tests.events._helpers import NOW, ORDER_CODE, Boom

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
    assert row.event_type == "common.sample-happened"
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
    @handles("common.sample-happened", name="common.record_sample")
    def first(event: SampleHappenedV1) -> None: ...

    with pytest.raises(ImproperlyConfigured, match=r"common\.record_sample"):

        @handles("common.sample-happened", version=1, name="common.record_sample")
        def second(event: SampleHappenedV1) -> None: ...

    registered = registry.get_handler("common.record_sample")
    assert registered is not None
    assert registered.func is first
    assert [h.name for h in registry.handlers_for("common.sample-happened", 1)] == [
        "common.record_sample"
    ]


def test_duplicate_event_class_rejected() -> None:
    assert registry.get_event_class("common.sample-happened", 1) is SampleHappenedV1

    with pytest.raises(ImproperlyConfigured, match=r"common\.sample-happened"):

        class OtherSampleV1(DomainEvent):
            event_type = "common.sample-happened"
            schema_version = 1

    assert registry.get_event_class("common.sample-happened", 1) is SampleHappenedV1


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
    longest = "common." + "x" * (max_length - len("common."))
    handles("common.sample-happened", name=longest)(lambda event: None)

    too_long = longest + "x"
    register = handles("common.sample-happened", name=too_long)
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
                "from common.events import DomainEvent",
                "class FakeThingDoneV1(DomainEvent):",
                "    event_type = 'full.thing-done'",
                "    schema_version = 1",
                "",
            ]
        ),
        "full/handlers.py": "\n".join(
            [
                "from common.events import handles",
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
    packages = [f"{fake_modules}.full", f"{fake_modules}.empty"]
    autodiscover(packages)

    assert registry.get_event_class("full.thing-done", 1) is not None
    assert [h.name for h in registry.handlers_for("full.thing-done", 1)] == ["full.on_thing_done"]
    # Module con không có events.py/handlers.py thì bỏ qua, không lỗi
    assert "fakemods.empty.events" not in sys.modules
    # Gọi lại không đăng ký trùng: module đã import không chạy lại
    autodiscover(packages)


def test_common_app_ready_autodiscovers_every_installed_app() -> None:
    with mock.patch("common.events.registry.autodiscover") as discover:
        apps.get_app_config("common").ready()

    (packages,), _ = discover.call_args
    assert {"apps.identity", "apps.geo", "common"} <= set(packages)
