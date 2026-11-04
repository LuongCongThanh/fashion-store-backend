"""Celery app, queue và lịch job (nguồn chuẩn cho `sync_beat_schedule`, 07 mục 3.2)."""

from celery import Celery
from celery.schedules import crontab
from kombu import Queue

# Không mặc định DJANGO_SETTINGS_MODULE: worker deploy thiếu biến thì Django báo lỗi khi đọc
# settings, thay vì chạy với settings local (DEBUG = True)
app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Local chạy một worker cho cả 4 queue (07 mục 3.1)
app.conf.task_queues = [Queue(name) for name in ("default", "events", "emails", "integrations")]

# Không có result backend (07 mục 3.3): tắt hạn kết quả để Beat không tự thêm job
# celery.backend_cleanup
app.conf.result_expires = None

# Lịch job thêm ở ticket tạo ra job đó; giờ theo CELERY_TIMEZONE
app.conf.beat_schedule = {
    "shared.purge_old_outbox_events": {
        "task": "shared.purge_old_outbox_events",
        "schedule": crontab(hour=3, minute=30),
    },
    "shared.purge_idempotency_keys": {
        "task": "shared.purge_idempotency_keys",
        "schedule": crontab(hour=3, minute=45),
    },
}

# Mặc định Celery chỉ tìm <app>.tasks, nên liệt kê từng package có tasks.py (02 mục 5)
app.autodiscover_tasks(["shared", "shared.events", "shared.idempotency"])
