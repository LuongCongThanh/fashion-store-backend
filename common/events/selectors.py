"""Theo dõi công việc giao sự kiện (07 mục 1.1.1)."""

from collections.abc import Iterable
from datetime import timedelta
from uuid import UUID

from django.db.models import Min
from django.utils import timezone

from common.events.models import DeliveryStatus, EventDelivery, OutboxEvent


def delivery_lag() -> timedelta:
    """Tuổi của công việc giao sự kiện mà relay, broker, worker đáng lẽ đã xử lý.

    Lấy lớn nhất giữa tuổi sự kiện chưa lập danh sách delivery và độ trễ của delivery `pending`
    đã tới hạn retry. Delivery `failed`, đã kết thúc hoặc đang chờ tới lượt retry không tính.
    Tính theo `occurred_at` vì `OutboxEvent` không có `created_at`; cột này ghi cùng transaction.
    """
    now = timezone.now()
    oldest_unlisted = OutboxEvent.objects.unlisted().aggregate(oldest=Min("occurred_at"))["oldest"]
    # Không xét `next_dispatch_at`: delivery đã giao mà chưa xong vẫn là tồn đọng
    oldest_due = EventDelivery.objects.attempt_due(now).aggregate(oldest=Min("next_attempt_at"))[
        "oldest"
    ]
    lags = [now - oldest for oldest in (oldest_unlisted, oldest_due) if oldest is not None]
    return max(lags, default=timedelta(0))


def get_delivery_outcomes(
    event_id: UUID, handler_names: Iterable[str]
) -> dict[str, DeliveryStatus | None]:
    """Trạng thái delivery của từng handler được hỏi cho một sự kiện.

    Mọi tên được hỏi đều có trong kết quả; `None` nghĩa là chưa có delivery (missing), không phải
    thành công. Bên gọi (ví dụ ẩn danh) tự quyết định khi nào coi là đủ.
    """
    names = list(handler_names)
    found = dict(
        EventDelivery.objects.filter(event_id=event_id, handler__in=names).values_list(
            "handler", "status"
        )
    )
    return {name: DeliveryStatus(found[name]) if name in found else None for name in names}
