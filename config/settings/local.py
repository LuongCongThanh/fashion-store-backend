# Cách tách settings chuẩn của Django: kế thừa mọi giá trị của base rồi ghi đè
from config.settings.base import *  # noqa: F403  # NOSONAR
from shared.logging import configure_logging

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]  # noqa: S104

# Mailpit (08 mục 2.3)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Log dễ đọc trên terminal thay cho JSON
LOGGING = configure_logging(json=False)
