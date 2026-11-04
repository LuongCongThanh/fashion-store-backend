# Nạp Celery app khi Django khởi động, để @shared_task dùng đúng app
from config.celery import app as celery_app

__all__ = ["celery_app"]
