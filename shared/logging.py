"""Cấu hình structlog và processor che PII (13 mục 10, 10 mục 2)."""

from collections.abc import MutableMapping
from typing import Any

import structlog

# Khớp chuỗi con, không phân biệt hoa thường, để bắt cả `contact_phone`, `access_token`
SENSITIVE_KEY_PARTS = ("email", "phone", "address", "token", "password", "card", "secret")
REDACTED = "[REDACTED]"


def _is_sensitive(key: object) -> bool:
    if not isinstance(key, str):
        return False
    lowered = key.lower()
    # Giá trị `_hmac` đã không đọc ngược được (ADR 0016) và cần thấy khi điều tra sự cố
    if lowered.endswith("_hmac"):
        return False
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: REDACTED if _is_sensitive(k) else _redact(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_redact(item) for item in value]
    return value


def redact_pii(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Lưới an toàn che PII theo tên key, kể cả trong dict và list lồng nhau.

    Không thay cho việc tự kiểm tra trước khi log: giá trị PII nằm dưới key vô hại vẫn lọt.
    """
    redacted: MutableMapping[str, Any] = _redact(dict(event_dict))
    return redacted


def configure_logging(*, json: bool) -> dict[str, Any]:
    """Cấu hình structlog và trả dict cho setting `LOGGING`.

    Log của thư viện qua `logging` chuẩn (Django, Celery) cũng đi qua cùng processor nên cũng
    được che PII và cùng định dạng. `json=False` chỉ dùng ở local cho dễ đọc.
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        redact_pii,
    ]
    renderer: Any
    if json:
        shared_processors.append(structlog.processors.format_exc_info)
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structlog": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": [
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    renderer,
                ],
                # `extra` của log stdlib thành key để redact_pii xét được
                "foreign_pre_chain": [structlog.stdlib.ExtraAdder(), *shared_processors],
            }
        },
        "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "structlog"}},
        "root": {"handlers": ["console"], "level": "INFO"},
    }
