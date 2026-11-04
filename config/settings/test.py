# Cách tách settings chuẩn của Django: kế thừa mọi giá trị của base rồi ghi đè
from config.settings.base import *  # noqa: F403  # NOSONAR
from config.settings.base import DATABASES

ALLOWED_HOSTS = ["testserver", "localhost"]

# pytest-django tạo test_fashion cho mỗi worker của pytest-xdist; pool giữ kết nối tới DB
# đang bị xoá nên tắt khi test
DATABASES["default"]["OPTIONS"].pop("pool")

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
