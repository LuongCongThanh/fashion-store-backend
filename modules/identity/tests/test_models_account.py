import ast
from pathlib import Path

import pytest
from django.apps import apps
from django.db import IntegrityError, connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.operations import CreateModel
from django.utils import timezone

import config.settings
from modules.identity.models import Account
from modules.identity.tests.factories import AccountFactory


@pytest.mark.django_db
def test_initial_migration_creates_identity_account() -> None:
    initial = MigrationLoader(connection).get_migration("modules", "0001_initial")
    created = [
        operation.options.get("db_table")
        for operation in initial.operations
        if isinstance(operation, CreateModel)
    ]

    assert created == ["identity_account"]
    assert "identity_account" in connection.introspection.table_names()


@pytest.mark.django_db
def test_email_unique_ignores_case() -> None:
    AccountFactory(email="lan@example.com")
    duplicate = AccountFactory.build(email="LAN@Example.com")

    with pytest.raises(IntegrityError, match="identity_account_email_lower_uniq"):
        duplicate.save()


def test_manager_normalizes_email_to_lowercase() -> None:
    normalized = Account.objects.normalize_email("  Lan@Example.COM ")

    assert normalized == "lan@example.com"


@pytest.mark.django_db
def test_anonymized_account_must_be_inactive() -> None:
    account = AccountFactory.build(anonymized_at=timezone.now(), is_active=True)

    with pytest.raises(IntegrityError, match="identity_account_anonymized_inactive"):
        account.save()


@pytest.mark.django_db
def test_unknown_kind_rejected_by_db() -> None:
    account = AccountFactory.build(kind="superuser")

    with pytest.raises(IntegrityError, match="identity_account_kind_valid"):
        account.save()


@pytest.mark.django_db
def test_unknown_language_rejected_by_db() -> None:
    account = AccountFactory.build(language="fr")

    with pytest.raises(IntegrityError, match="identity_account_language_valid"):
        account.save()


@pytest.mark.django_db
def test_no_django_auth_tables_after_migrate() -> None:
    tables = connection.introspection.table_names()

    django_auth_tables = [
        t
        for t in tables
        if t.startswith("auth_") or t == "django_admin_log" or "group" in t or "permission" in t
    ]
    assert django_auth_tables == []


def _installed_apps_in(settings_file: Path) -> set[str]:
    """Chuỗi trong mọi phép gán `INSTALLED_APPS` của file, đọc bằng ast thay vì import.

    Import `config.settings.local` gọi `structlog.configure` toàn cục, làm đổi log của test khác.
    """
    tree = ast.parse(settings_file.read_text(encoding="utf-8"))
    apps_found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AugAssign | ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        if any(isinstance(t, ast.Name) and t.id == "INSTALLED_APPS" for t in targets):
            apps_found |= {
                c.value
                for c in ast.walk(value)
                if isinstance(c, ast.Constant) and isinstance(c.value, str)
            }
    return apps_found


def test_django_admin_not_installed_in_any_settings() -> None:
    # Không dùng Django Admin ở mọi môi trường (ADR 0004, 08 mục 2.4)
    settings_files = {
        path.stem: path
        for path in Path(config.settings.__file__).parent.glob("*.py")
        if path.stem != "__init__"
    }

    with_admin = sorted(
        name
        for name, path in settings_files.items()
        if "django.contrib.admin" in _installed_apps_in(path)
    )
    assert sorted(settings_files) == ["base", "local", "production", "test"]
    assert with_admin == []
    assert "django.contrib.contenttypes" in _installed_apps_in(settings_files["base"])
    assert not apps.is_installed("django.contrib.admin")
