"""File test đặt theo đường dẫn soi gương code (02 mục 4.4, 12 mục 2).

`<pkg>/tests/<dir>/test_<x>.py` kiểm `<pkg>/<dir>/<x>.py` hoặc package `<pkg>/<dir>/<x>/`, với
`<pkg>` là `common` hoặc `apps/<module>`. Thư mục `concurrency/`, `flows/` trong `tests/` của app
không soi gương; `tests/` ở gốc repo (flows, tooling) không thuộc quy tắc này.
"""

from pathlib import Path

import pytest

from tests.tooling.helpers import ROOT, write_tree

# Thư mục con của `<pkg>/tests/` chứa test theo kịch bản, không theo file nguồn
SCENARIO_DIRS = frozenset({"concurrency", "flows"})

# File test không ứng với một file nguồn, kèm lý do
EXCEPTIONS = {
    "common/tests/api/test_i18n.py": "kiểm LocaleMiddleware và Accept-Language của settings",
    "common/tests/test_factories.py": "kiểm factory dùng chung ở common/tests/factories.py",
}


def packages(root: Path) -> list[Path]:
    apps = root / "apps"
    found = [root / "common"]
    if apps.is_dir():
        found += sorted(path for path in apps.iterdir() if (path / "__init__.py").is_file())
    return [package for package in found if (package / "tests").is_dir()]


def misplaced(root: Path, exceptions: dict[str, str]) -> list[str]:
    """Đường dẫn (tính từ `root`) của file test không ứng với file hay package nguồn nào."""
    wrong = []
    for package in packages(root):
        tests = package / "tests"
        for path in sorted(tests.rglob("test_*.py")):
            relative = path.relative_to(tests)
            name = path.relative_to(root).as_posix()
            if relative.parts[0] in SCENARIO_DIRS or name in exceptions:
                continue
            source = package / relative.parent / path.stem.removeprefix("test_")
            if not (source.with_suffix(".py").is_file() or source.is_dir()):
                wrong.append(name)
    return wrong


def test_every_test_file_mirrors_a_source_file() -> None:
    assert misplaced(ROOT, EXCEPTIONS) == []


def test_exceptions_point_to_existing_files() -> None:
    assert [name for name in EXCEPTIONS if not (ROOT / name).is_file()] == []


@pytest.mark.parametrize(
    ("test_file", "expected"),
    [
        ("apps/shop/tests/services/test_checkout.py", []),
        ("apps/shop/tests/test_services.py", []),
        ("apps/shop/tests/concurrency/test_anything.py", []),
        (
            "apps/shop/tests/test_services_checkout.py",
            ["apps/shop/tests/test_services_checkout.py"],
        ),
        ("apps/shop/tests/services/test_cart.py", ["apps/shop/tests/services/test_cart.py"]),
        ("common/tests/test_money.py", ["common/tests/test_money.py"]),
    ],
)
def test_misplaced_test_file_is_reported(
    tmp_path: Path, test_file: str, expected: list[str]
) -> None:
    write_tree(
        tmp_path,
        {
            "apps/shop/__init__.py": "",
            "apps/shop/services/checkout.py": "",
            "common/values/money.py": "",
            test_file: "",
        },
    )

    assert misplaced(tmp_path, {}) == expected
