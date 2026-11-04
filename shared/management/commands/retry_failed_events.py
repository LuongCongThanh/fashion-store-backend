"""Mở lại delivery `failed` để relay giao lại (07 mục 1.3, 03 mục 1.4).

Bộ lọc `--event-id`, `--handler`, `--type` kết hợp với nhau; muốn mở lại mọi delivery `failed`
phải ghi rõ `--all`, để lệnh gõ thiếu bộ lọc không mở lại toàn bộ.
"""

from argparse import ArgumentParser
from typing import Any
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError

from shared.events.operations import retry_failed_events
from shared.events.registry import registry


class Command(BaseCommand):
    help = "Mở lại EventDelivery failed theo bộ lọc, đặt lại bộ đếm và lịch retry."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--event-id", type=UUID, help="Chỉ delivery của sự kiện này.")
        parser.add_argument("--handler", help="Chỉ delivery của handler này.")
        parser.add_argument("--type", dest="event_type", help="Chỉ sự kiện có event_type này.")
        parser.add_argument("--all", action="store_true", help="Mọi delivery failed.")

    def handle(self, *args: object, **options: Any) -> None:
        event_id, handler, event_type = (
            options["event_id"],
            options["handler"],
            options["event_type"],
        )
        if not options["all"] and event_id is None and handler is None and event_type is None:
            raise CommandError("Cần ít nhất một bộ lọc --event-id, --handler, --type hoặc --all.")
        if handler is not None and registry.get_handler(handler) is None:
            raise CommandError(f"Handler {handler} chưa đăng ký.")
        retry_failed_events(event_id=event_id, handler=handler, event_type=event_type)
