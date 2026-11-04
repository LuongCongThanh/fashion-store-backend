"""Báo cáo các mã quy tắc nghiệp vụ BR-xxx chưa có test gắn marker `br` (12 mục 3)."""

from __future__ import annotations

import argparse
import contextlib
import io
import re
from pathlib import Path

import pytest

DEFAULT_RULES_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "business" / "04-business-rules.md"
)


def extract_rule_codes(markdown_text: str) -> list[str]:
    """Trích xuất danh sách mã `BR-xxx` theo thứ tự xuất hiện, loại bỏ mã trùng."""
    codes: list[str] = []
    seen: set[str] = set()
    for code in re.findall(r"\bBR-[A-Z0-9]+-\d+\b", markdown_text):
        if code not in seen:
            seen.add(code)
            codes.append(code)
    return codes


class _BRMarkerCollector:
    """Plugin pytest thu thập các mã BR được gắn qua marker `@pytest.mark.br(...)`."""

    def __init__(self) -> None:
        self.tested_codes: set[str] = set()

    def pytest_collection_modifyitems(self, items: list[pytest.Item]) -> None:
        for item in items:
            for marker in item.iter_markers("br"):
                for arg in marker.args:
                    if isinstance(arg, str):
                        for part in arg.split(","):
                            code = part.strip()
                            if code:
                                self.tested_codes.add(code)


def collect_tested_codes(pytest_args: list[str]) -> set[str]:
    """Chạy `pytest --collect-only` trong im lặng để thu thập toàn bộ mã BR đã test."""
    collector = _BRMarkerCollector()
    buf = io.StringIO()
    # Ẩn output thu thập test của pytest để br-report chỉ in danh sách mã BR chưa test
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        pytest.main(["--collect-only", "-q", *pytest_args], plugins=[collector])
    return collector.tested_codes


def generate_br_report(rules_file: Path, pytest_args: list[str]) -> list[str]:
    """Tìm các mã `BR-xxx` trong file tài liệu chưa có test nào gắn marker."""
    if not rules_file.is_file():
        return []
    rules_text = rules_file.read_text(encoding="utf-8")
    all_codes = extract_rule_codes(rules_text)
    tested_codes = collect_tested_codes(pytest_args)
    return [code for code in all_codes if code not in tested_codes]


def main() -> int:
    """Entry point lệnh `br-report`: in danh sách mã chưa test và luôn thoát với mã 0."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rules-file",
        type=Path,
        default=DEFAULT_RULES_PATH,
        help="Đường dẫn file tài liệu quy tắc nghiệp vụ (mặc định 04-business-rules.md)",
    )
    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="Tham số tuỳ chọn truyền thêm cho pytest khi thu thập test",
    )
    args = parser.parse_args()

    untested = generate_br_report(args.rules_file, args.pytest_args)
    for code in untested:
        print(code)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
