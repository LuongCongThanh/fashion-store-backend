"""Factory gốc dùng chung cho test (02 mục 5, 13 mục 9)."""

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from shared.api import idempotency as idempotency_api
from shared.events.models import DeliveryStatus, EventDelivery, OutboxEvent
from shared.geo.models import Province, Ward
from shared.idempotency import LEASE
from shared.models import IdempotencyKey, IdempotencyStatus, uuid7


class ProvinceFactory(DjangoModelFactory[Province]):
    class Meta:
        model = Province

    code = factory.Sequence(lambda n: f"{n:02d}")
    name = factory.Sequence(lambda n: f"Tỉnh {n}")


class WardFactory(DjangoModelFactory[Ward]):
    class Meta:
        model = Ward

    code = factory.Sequence(lambda n: f"{n:05d}")
    province = factory.SubFactory(ProvinceFactory)
    name = factory.Sequence(lambda n: f"Phường {n}")


class OutboxEventFactory(DjangoModelFactory[OutboxEvent]):
    """Dòng outbox chưa lập danh sách delivery, loại sự kiện trung tính không có class nào parse.

    Trait `sample` khớp sự kiện mẫu `shared.sample-happened` v1 trong test của `shared.events`;
    trait `listed` là sự kiện relay đã lập danh sách delivery ngay lúc `occurred_at`. Module khác
    truyền `event_type`, `schema_version`, `payload` của sự kiện thật.
    """

    class Meta:
        model = OutboxEvent

    event_type = "shared.test-event"
    schema_version = 1
    payload = factory.LazyFunction(dict)
    occurred_at = factory.LazyFunction(timezone.now)

    class Params:
        sample = factory.Trait(
            event_type="shared.sample-happened",
            payload=factory.LazyFunction(lambda: {"order_code": "FS2610-7K3QZD", "amount": 250000}),
        )
        listed = factory.Trait(
            deliveries_created_at=factory.LazyAttribute(lambda event: event.occurred_at)
        )


class EventDeliveryFactory(DjangoModelFactory[EventDelivery]):
    """Delivery `pending` tới hạn cả retry lẫn giao lại; trait `failed` cho delivery đã `failed`."""

    class Meta:
        model = EventDelivery

    event = factory.SubFactory(OutboxEventFactory)
    handler = factory.Sequence(lambda n: f"shared.handler_{n}")
    next_attempt_at = factory.LazyFunction(timezone.now)
    next_dispatch_at = factory.LazyAttribute(lambda delivery: delivery.next_attempt_at)

    class Params:
        failed = factory.Trait(
            status=DeliveryStatus.FAILED,
            failed_at=factory.LazyFunction(timezone.now),
            last_error="Boom",
        )


class IdempotencyKeyFactory(DjangoModelFactory[IdempotencyKey]):
    """Key `in_progress` còn lease, body rỗng `{}`; trait `completed` cho key đã lưu kết quả."""

    class Meta:
        model = IdempotencyKey

    scope = factory.Sequence(lambda n: f"POST /api/v1/store/checkout|account:{n}")
    key = factory.LazyFunction(uuid7)
    request_hash = idempotency_api.request_hash({})
    lease_token = factory.LazyFunction(uuid7)
    lease_expires_at = factory.LazyFunction(lambda: timezone.now() + LEASE)

    class Params:
        completed = factory.Trait(
            status=IdempotencyStatus.COMPLETED,
            completed_at=factory.LazyFunction(timezone.now),
            response_status=201,
            response_body=factory.LazyFunction(dict),
            lease_token=None,
            lease_expires_at=None,
        )
