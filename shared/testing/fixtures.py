"""Fixture pytest không cần nghiệp vụ; `conftest.py` ở gốc repo nạp qua `pytest_plugins`."""

import logging
from collections.abc import Iterator
from typing import Any

import pytest
import structlog
from django.core.cache import cache

from shared.logging import configure_logging


@pytest.fixture(autouse=True)
def _clear_cache() -> Iterator[None]:
    # Bộ đếm throttle nằm trong cache: không để hạn mức của test này ảnh hưởng test khác
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def json_logging() -> Iterator[dict[str, Any]]:
    """Cấu hình structlog như production (log JSON); trả dict `LOGGING` để test `dictConfig`."""
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield configure_logging(json=True)
    root.handlers[:] = handlers
    root.setLevel(level)
    structlog.reset_defaults()
