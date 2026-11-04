import pytest
from django.core.management import call_command
from django.db import connection


@pytest.mark.django_db
def test_extensions_and_immutable_unaccent_exist_after_migrate() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT extname FROM pg_extension")
        extensions = {row[0] for row in cursor.fetchall()}
        cursor.execute("SELECT provolatile FROM pg_proc WHERE proname = 'immutable_unaccent'")
        volatility = cursor.fetchone()
        cursor.execute("SELECT public.immutable_unaccent(lower('Áo Thun Đỏ'))")
        unaccented = cursor.fetchone()

    assert {"unaccent", "pg_trgm", "btree_gist"} <= extensions
    assert volatility == ("i",)
    assert unaccented == ("ao thun do",)


@pytest.mark.django_db(transaction=True)
def test_reverse_drops_function_but_keeps_extensions() -> None:
    try:
        call_command("migrate", "shared", "zero", verbosity=0)
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_proc WHERE proname = 'immutable_unaccent'")
            function = cursor.fetchone()
            cursor.execute("SELECT extname FROM pg_extension")
            extensions = {row[0] for row in cursor.fetchall()}
    finally:
        # `migrate shared zero` gỡ cả migration của `modules`, nên chạy lại mọi app
        call_command("migrate", verbosity=0)

    assert function is None
    assert {"unaccent", "pg_trgm", "btree_gist"} <= extensions
