from collections.abc import Iterator
from datetime import timedelta

import pytest
from django.db import connection, models
from django.utils import timezone

from shared.events.models import EventDelivery, OutboxEvent
from shared.models import BaseModel, BaseQuerySet, UUIDv7Model


class Widget(BaseModel):
    name = models.CharField(max_length=20)

    # Khai báo lại manager: model test-only không có trong app registry lúc mypy chạy, nên khi
    # shared có model cụ thể kế thừa BaseModel, plugin django-stubs gán kiểu manager của BaseModel
    objects = BaseQuerySet.as_manager()

    class Meta:
        app_label = "shared"
        db_table = "shared_test_widget"


@pytest.fixture
def widget_table(db: None) -> Iterator[None]:
    # Model chỉ dùng trong test, không có migration
    with connection.schema_editor() as editor:
        editor.create_model(Widget)
    yield
    with connection.schema_editor() as editor:
        editor.delete_model(Widget)


@pytest.mark.usefixtures("widget_table")
def test_assigns_uuid7_and_both_timestamps() -> None:
    widget = Widget.objects.create(name="a")

    assert widget.id.version == 7
    assert widget.created_at is not None
    assert widget.updated_at is not None


@pytest.mark.usefixtures("widget_table")
def test_bulk_create_fills_timestamps() -> None:
    Widget.objects.bulk_create([Widget(name="a"), Widget(name="b")])

    assert not Widget.objects.filter(updated_at__isnull=True).exists()


@pytest.mark.usefixtures("widget_table")
def test_queryset_update_sets_updated_at() -> None:
    widget = Widget.objects.create(name="a")
    past = timezone.now() - timedelta(days=1)
    Widget.objects.filter(pk=widget.pk).update(updated_at=past)

    Widget.objects.filter(pk=widget.pk).update(name="b")

    widget.refresh_from_db()
    assert widget.updated_at > past
    assert widget.created_at < widget.updated_at


@pytest.mark.usefixtures("widget_table")
def test_bulk_update_sets_updated_at_when_missing_from_fields() -> None:
    widget = Widget.objects.create(name="a")
    past = timezone.now() - timedelta(days=1)
    Widget.objects.filter(pk=widget.pk).update(updated_at=past)
    widget.refresh_from_db()
    widget.name = "b"

    assert Widget.objects.bulk_update([widget], (f for f in ["name"])) == 1

    widget.refresh_from_db()
    assert widget.name == "b"
    assert widget.updated_at > past


@pytest.mark.usefixtures("widget_table")
def test_bulk_update_keeps_caller_updated_at() -> None:
    widget = Widget.objects.create(name="a")
    chosen = timezone.now() - timedelta(hours=1)
    widget.updated_at = chosen

    Widget.objects.bulk_update([widget], ["updated_at"])

    widget.refresh_from_db()
    assert widget.updated_at == chosen


def test_outbox_models_share_uuid7_primary_key() -> None:
    # Khoá chính UUID v7 khai báo một chỗ (ADR 0008); outbox không kế thừa `BaseModel`
    actual = [
        model.__name__
        for model in (BaseModel, OutboxEvent, EventDelivery)
        if not issubclass(model, UUIDv7Model)
    ]
    assert actual == []
