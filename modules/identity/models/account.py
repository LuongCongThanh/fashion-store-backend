"""Tài khoản: custom user model (03 mục 2.1)."""

from typing import ClassVar

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower

from modules.identity.constants import AccountKind, Language
from shared.models import BaseModel, BaseQuerySet

# Gán tên ở cấp module để plugin django-stubs suy được kiểu của manager sinh động
_AccountManagerBase = BaseUserManager.from_queryset(BaseQuerySet)


class AccountManager(_AccountManagerBase):
    """Manager của user model, giữ việc tự gán `updated_at` khi ghi bulk của `BaseQuerySet`."""

    @classmethod
    def normalize_email(cls, email: str | None) -> str:
        # 03 mục 2.1 lưu cả email chữ thường; mặc định của Django chỉ hạ chữ phần tên miền
        return (email or "").strip().lower()


# Không kế thừa PermissionsMixin: quyền dựa trên `kind` (05), nên không có bảng group/permission
class Account(AbstractBaseUser, BaseModel):
    email = models.EmailField(max_length=254)
    kind = models.CharField(max_length=32, choices=AccountKind.choices)
    full_name = models.CharField(max_length=255, blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    language = models.CharField(max_length=32, choices=Language.choices, default=Language.VI)
    # Tăng để vô hiệu mọi access token (05)
    token_version = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)
    anonymized_at = models.DateTimeField(null=True, blank=True)

    # Cùng BaseQuerySet với manager của BaseModel nhưng thêm hàm của user manager; stub coi hai
    # lớp manager sinh từ from_queryset là khác kiểu
    objects: ClassVar[AccountManager] = AccountManager()  # type: ignore[assignment]

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        db_table = "identity_account"
        constraints = (
            # Một email chỉ thuộc một Tài khoản, cho mọi `kind` (03 mục 2.1)
            models.UniqueConstraint(Lower("email"), name="identity_account_email_lower_uniq"),
            models.CheckConstraint(
                condition=models.Q(kind__in=AccountKind.values), name="identity_account_kind_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(language__in=Language.values),
                name="identity_account_language_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(anonymized_at__isnull=True) | models.Q(is_active=False),
                name="identity_account_anonymized_inactive",
            ),
        )

    def __str__(self) -> str:
        return f"{self.kind} {self.id}"
