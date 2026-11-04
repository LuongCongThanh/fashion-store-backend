"""Tạo delivery còn thiếu cho sự kiện cũ, ví dụ khi thêm handler mới (07 mục 1.1.1).

Không chạy lại cặp đã có delivery: cặp `failed` mở lại bằng `retry_failed_events`.
"""

from argparse import ArgumentParser
from datetime import datetime
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from shared.events.operations import replay_events
from shared.events.registry import registry


def _aware_datetime(value: str) -> datetime:
    # Mốc không ghi múi giờ được hiểu theo `TIME_ZONE`
    parsed = datetime.fromisoformat(value)
    return parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)


class Command(BaseCommand):
    help = "Tạo EventDelivery còn thiếu cho sự kiện theo loại từ một mốc thời gian."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--type", dest="event_type", required=True, help="event_type cần phát lại."
        )
        parser.add_argument(
            "--since",
            type=_aware_datetime,
            required=True,
            help="Mốc deliveries_created_at, lúc relay lập danh sách delivery (ISO 8601), "
            "tính cả mốc.",
        )
        parser.add_argument("--handler", help="Chỉ handler này; mặc định mọi handler đăng ký.")

    def handle(self, *args: object, **options: Any) -> None:
        handler, event_type = options["handler"], options["event_type"]
        if handler is not None:
            found = registry.get_handler(handler)
            if found is None:
                raise CommandError(f"Handler {handler} chưa đăng ký.")
            if found.event_type != event_type:
                raise CommandError(f"Handler {handler} không đăng ký cho {event_type}.")
        replay_events(event_type=event_type, since=options["since"], handler=handler)
