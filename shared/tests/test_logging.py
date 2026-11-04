import json
import logging
import logging.config
from typing import Any

import pytest
import structlog

from shared.logging import REDACTED, redact_pii


def test_redacts_sensitive_keys_including_substrings() -> None:
    event = redact_pii(
        None,
        "info",
        {
            "event": "order_placed",
            "email": "a@b.vn",
            "contact_phone": "+84901234567",
            "Access_Token": "x",
            "order_code": "FS2610-7K3QZD",
        },
    )

    assert event == {
        "event": "order_placed",
        "email": REDACTED,
        "contact_phone": REDACTED,
        "Access_Token": REDACTED,
        "order_code": "FS2610-7K3QZD",
    }


def test_redacts_nested_values() -> None:
    event = redact_pii(
        None, "info", {"event": "x", "payload": {"items": [{"phone": "1", "sku": "A"}]}}
    )

    assert event["payload"] == {"items": [{"phone": REDACTED, "sku": "A"}]}


def test_keeps_hmac_values() -> None:
    event = redact_pii(None, "info", {"event": "x", "subject_phone_hmac": "k1:ab"})

    assert event["subject_phone_hmac"] == "k1:ab"


def test_json_output_is_redacted_for_structlog_and_stdlib_loggers(
    json_logging: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    logging.config.dictConfig(json_logging)

    structlog.get_logger("shared.tests").info("login_failed", email="a@b.vn", token="t")
    logging.getLogger("django").warning("lib_log", extra={"phone": "+84901234567"})

    lines = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    assert lines[0]["event"] == "login_failed"
    assert lines[0]["email"] == REDACTED
    assert lines[0]["token"] == REDACTED
    assert lines[1]["event"] == "lib_log"
    assert lines[1]["phone"] == REDACTED
