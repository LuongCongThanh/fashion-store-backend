"""Job `identity.purge_refresh_replays` (07 mục 3.2; 03 mục 2.5)."""

from datetime import UTC, datetime, timedelta

import pytest
import time_machine
from structlog.testing import capture_logs

from apps.identity.models import RefreshReplay
from apps.identity.tasks import purge_refresh_replays
from apps.identity.tests.factories import RefreshTokenFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)


def _replay(*, expires_at: datetime) -> RefreshReplay:
    parent = RefreshTokenFactory.create(used_at=expires_at - timedelta(seconds=10))
    return RefreshReplay.objects.create(
        parent=parent,
        encryption_key_id="test-replay-1",
        nonce=b"0" * 12,
        response_ciphertext=b"ciphertext",
        expires_at=expires_at,
    )


@time_machine.travel(NOW, tick=False)
def test_purge_deletes_only_expired_replays() -> None:
    _replay(expires_at=NOW - timedelta(seconds=1))
    _replay(expires_at=NOW)
    kept = _replay(expires_at=NOW + timedelta(seconds=1))

    with capture_logs() as logs:
        purge_refresh_replays()

    assert list(RefreshReplay.objects.values_list("id", flat=True)) == [kept.id]
    purged = [log for log in logs if log["event"] == "refresh_replays_purged"]
    assert [log["count"] for log in purged] == [2]
    assert "ciphertext" not in repr([log for log in logs if log["event"] != "task_started"])
