import json
from datetime import timedelta
from typing import Any

import pytest
from celery.schedules import crontab
from django.core.management import call_command
from django_celery_beat.models import (
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)
from structlog.testing import capture_logs

from config.celery import app

CODE_SCHEDULE: dict[str, dict[str, Any]] = {
    "shared.every_minute_job": {
        "task": "shared.tasks.every_minute_job",
        "schedule": timedelta(minutes=1),
        "args": [7],
        "kwargs": {"batch_size": 100},
        "options": {"queue": "events", "expire_seconds": 50},
    },
    "shared.nightly_job": {
        "task": "shared.tasks.nightly_job",
        "schedule": crontab(minute="30", hour="3"),
    },
}

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _code_schedule(monkeypatch: pytest.MonkeyPatch) -> None:
    # Thay lịch thật của config/celery.py bằng lịch giả có cả interval và crontab
    monkeypatch.setitem(app.conf, "beat_schedule", CODE_SCHEDULE)


def test_empty_db_creates_every_job_from_code() -> None:
    with capture_logs() as logs:
        call_command("sync_beat_schedule")

    assert sorted(PeriodicTask.objects.values_list("name", flat=True)) == sorted(CODE_SCHEDULE)
    every_minute = PeriodicTask.objects.get(name="shared.every_minute_job")
    assert every_minute.task == "shared.tasks.every_minute_job"
    assert every_minute.enabled
    assert every_minute.queue == "events"
    assert json.loads(every_minute.args) == [7]
    assert json.loads(every_minute.kwargs) == {"batch_size": 100}
    assert every_minute.expire_seconds == 50
    assert every_minute.crontab is None
    assert every_minute.interval is not None
    assert every_minute.interval.every == 60
    assert every_minute.interval.period == IntervalSchedule.SECONDS

    nightly = PeriodicTask.objects.get(name="shared.nightly_job")
    assert nightly.task == "shared.tasks.nightly_job"
    assert nightly.enabled
    assert nightly.queue is None
    assert nightly.interval is None
    assert nightly.crontab is not None
    assert nightly.crontab.minute == "30"
    assert nightly.crontab.hour == "3"
    assert str(nightly.crontab.timezone) == "Asia/Ho_Chi_Minh"

    assert sorted(log["name"] for log in logs if log["event"] == "beat_job_created") == sorted(
        CODE_SCHEDULE
    )


def test_second_run_changes_nothing() -> None:
    call_command("sync_beat_schedule")
    before = list(PeriodicTask.objects.order_by("name").values())
    schedules_before = (IntervalSchedule.objects.count(), CrontabSchedule.objects.count())

    with capture_logs() as logs:
        call_command("sync_beat_schedule")

    assert list(PeriodicTask.objects.order_by("name").values()) == before
    schedules_after = (IntervalSchedule.objects.count(), CrontabSchedule.objects.count())
    assert schedules_after == schedules_before
    assert logs == []


def test_job_missing_from_code_is_disabled_not_deleted() -> None:
    hourly, _ = IntervalSchedule.objects.get_or_create(every=1, period=IntervalSchedule.HOURS)
    PeriodicTask.objects.create(name="shared.removed_job", task="shared.tasks.x", interval=hourly)

    with capture_logs() as logs:
        call_command("sync_beat_schedule")

    removed = PeriodicTask.objects.get(name="shared.removed_job")
    assert not removed.enabled
    assert [log["name"] for log in logs if log["event"] == "beat_job_disabled"] == [
        "shared.removed_job"
    ]


def test_db_frequency_differing_from_code_is_corrected() -> None:
    call_command("sync_beat_schedule")
    every_five_minutes, _ = IntervalSchedule.objects.get_or_create(
        every=5, period=IntervalSchedule.MINUTES
    )
    PeriodicTask.objects.filter(name="shared.every_minute_job").update(interval=every_five_minutes)
    nightly = PeriodicTask.objects.get(name="shared.nightly_job")
    assert nightly.crontab is not None
    CrontabSchedule.objects.filter(pk=nightly.crontab.pk).update(hour="5")

    with capture_logs() as logs:
        call_command("sync_beat_schedule")

    every_minute = PeriodicTask.objects.get(name="shared.every_minute_job")
    assert every_minute.interval is not None
    assert every_minute.interval.every == 60
    assert every_minute.interval.period == IntervalSchedule.SECONDS
    nightly.refresh_from_db()
    assert nightly.crontab is not None
    assert nightly.crontab.minute == "30"
    assert nightly.crontab.hour == "3"
    updated = {log["name"]: log["fields"] for log in logs if log["event"] == "beat_job_updated"}
    assert updated == {
        "shared.every_minute_job": ["interval"],
        "shared.nightly_job": ["crontab"],
    }


def test_db_args_and_options_differing_from_code_are_corrected() -> None:
    call_command("sync_beat_schedule")
    PeriodicTask.objects.filter(name="shared.every_minute_job").update(
        args="[]", kwargs="{}", expire_seconds=None
    )

    with capture_logs() as logs:
        call_command("sync_beat_schedule")

    every_minute = PeriodicTask.objects.get(name="shared.every_minute_job")
    assert json.loads(every_minute.args) == [7]
    assert json.loads(every_minute.kwargs) == {"batch_size": 100}
    assert every_minute.expire_seconds == 50
    updated = {log["name"]: log["fields"] for log in logs if log["event"] == "beat_job_updated"}
    assert updated == {"shared.every_minute_job": ["args", "kwargs", "expire_seconds"]}


def test_db_job_on_other_schedule_type_is_switched_to_code_schedule() -> None:
    sunrise = SolarSchedule.objects.create(event="sunrise", latitude=10.8, longitude=106.7)
    PeriodicTask.objects.create(
        name="shared.every_minute_job", task="shared.tasks.every_minute_job", solar=sunrise
    )

    call_command("sync_beat_schedule")

    every_minute = PeriodicTask.objects.get(name="shared.every_minute_job")
    assert every_minute.solar is None
    assert every_minute.interval is not None
    assert every_minute.interval.every == 60
    assert every_minute.interval.period == IntervalSchedule.SECONDS
