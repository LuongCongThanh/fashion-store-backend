"""Tạo Tài khoản Staff hoặc Admin cho back-office (02 mục 5, 08 mục 2.4 bước 5).

Thiếu `--email` thì hỏi. Mật khẩu luôn nhập qua `getpass` hai lần, không có cờ `--password` để
mật khẩu không nằm trong lịch sử shell; email và độ mạnh mật khẩu do service kiểm (05 mục 3).
"""

from getpass import getpass

import structlog
from django.core.management.base import BaseCommand, CommandError, CommandParser

from modules.identity.constants import AccountKind
from modules.identity.exceptions import WeakPassword
from modules.identity.services.accounts import create_staff_account
from shared.exceptions import DomainError

logger = structlog.get_logger(__name__)


class Command(BaseCommand):
    help = "Tạo Tài khoản Staff (Admin khi có --admin); mật khẩu nhập từ bàn phím."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--admin", action="store_true", help="Tạo Tài khoản Admin.")
        parser.add_argument("--email", help="Email đăng nhập; bỏ trống thì lệnh hỏi.")
        parser.add_argument("--full-name", default="", help="Họ tên hiển thị.")

    def handle(self, *args: object, **options: object) -> None:
        kind = AccountKind.ADMIN if options["admin"] else AccountKind.STAFF
        email = str(options["email"] or input("Email: "))
        full_name = str(options["full_name"])
        password = getpass("Mật khẩu: ")
        if getpass("Nhập lại mật khẩu: ") != password:
            raise CommandError("Hai lần nhập mật khẩu không khớp")
        try:
            account = create_staff_account(
                email=email, password=password, kind=kind, full_name=full_name
            )
        except WeakPassword as exc:
            raise CommandError(f"{exc.message} {' '.join(exc.details['messages'])}") from exc
        except DomainError as exc:
            raise CommandError(str(exc.message)) from exc
        # Không ghi email vào log (PII, 13 mục 10)
        logger.info("staff_account_created", account_id=str(account.id), kind=account.kind)
