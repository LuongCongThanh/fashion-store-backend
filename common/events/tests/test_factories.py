"""Mặc định và trait của factory outbox (12 mục 4)."""

import pytest

from common.events.models import DeliveryStatus
from common.events.tests._helpers import NOW, ORDER_CODE
from common.events.tests.conftest import SampleHappenedV1
from common.tests.factories import EventDeliveryFactory, OutboxEventFactory

pytestmark = pytest.mark.django_db


def test_outbox_event_factory_default_is_neutral() -> None:
    event = OutboxEventFactory.build()

    actual = (event.event_type, event.payload)
    assert actual == ("common.test-event", {})


def test_factory_traits_build_sample_listed_and_failed() -> None:
    sample = OutboxEventFactory.build(sample=True)
    listed = OutboxEventFactory.build(listed=True, occurred_at=NOW)
    failed = EventDeliveryFactory.build(failed=True)

    actual = (
        sample.event_type,
        sample.schema_version,
        SampleHappenedV1.model_validate(sample.payload).order_code,
        listed.deliveries_created_at,
        failed.status,
        failed.failed_at is not None,
        failed.last_error,
    )
    expected = (
        SampleHappenedV1.event_type,
        SampleHappenedV1.schema_version,
        ORDER_CODE,
        NOW,
        DeliveryStatus.FAILED,
        True,
        "Boom",
    )
    assert actual == expected
