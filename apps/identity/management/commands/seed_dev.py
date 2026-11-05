"""Tạo dữ liệu mẫu cho máy dev: Tài khoản Admin và Staff với mật khẩu dev cố định.

Mật khẩu nằm trong code nên lệnh chỉ chạy khi `DEBUG` bật và database ở `localhost`. Tạo qua
service nên email, mật khẩu được kiểm như khi tạo thật. Chạy lại không tạo trùng: email đã có thì
giữ nguyên Tài khoản cũ. Customer thêm khi có service đăng ký; dữ liệu catalog, tồn kho thêm khi
các module đó có model.
"""

from typing import NamedTuple

import structlog
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.identity.constants import AccountKind
from apps.identity.exceptions import EmailAlreadyUsed
from apps.identity.services.accounts import create_staff_account
from common.management.commands.reset_db import LOCAL_HOSTS

logger = structlog.get_logger(__name__)


class SeedAccount(NamedTuple):
    email: str
    password: str
    kind: AccountKind
    full_name: str


SEED_ACCOUNTS = (
    SeedAccount("seed.admin@example.test", "Dev-Admin-2026!", AccountKind.ADMIN, "Seed Admin"),
    SeedAccount("seed.staff@example.test", "Dev-Staff-2026!", AccountKind.STAFF, "Seed Staff"),
)


class Command(BaseCommand):
    help = "Tạo Tài khoản Admin, Staff mẫu cho máy dev (chỉ khi DEBUG bật và host là localhost)."

    def handle(self, *args: object, **options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_dev chỉ chạy khi DEBUG bật (máy dev)")
        host = settings.DATABASES["default"]["HOST"]
        if host not in LOCAL_HOSTS:
            raise CommandError(
                f"seed_dev chỉ chạy với database trên máy (localhost, 127.0.0.1, ::1), "
                f"host đang là {host!r}"
            )
        for seed in SEED_ACCOUNTS:
            try:
                account = create_staff_account(
                    email=seed.email,
                    password=seed.password,
                    kind=seed.kind,
                    full_name=seed.full_name,
                )
            except EmailAlreadyUsed:
                self.stdout.write(f"Giữ nguyên {seed.kind}: {seed.email}")
                continue
            # Không ghi email vào log (PII, 13 mục 10); stdout cho dev biết tài khoản nào
            logger.info("seed_account_created", account_id=str(account.id), kind=account.kind)
            self.stdout.write(f"Đã tạo {seed.kind}: {seed.email} / {seed.password}")
