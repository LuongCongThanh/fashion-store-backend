from django.db import models


class AccountKind(models.TextChoices):
    CUSTOMER = "customer"
    STAFF = "staff"
    ADMIN = "admin"


class Language(models.TextChoices):
    VI = "vi"
    EN = "en"


# Loại Tài khoản được đăng nhập back-office (05 mục 2.3)
BACKOFFICE_KINDS = frozenset({AccountKind.STAFF, AccountKind.ADMIN})
