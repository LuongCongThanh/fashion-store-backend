"""Cấu hình chung mọi môi trường."""

from config.env import BASE_DIR, database_config, get_env
from shared.logging import configure_logging

env = get_env()

SECRET_KEY = env.DJANGO_SECRET_KEY.get_secret_value()
# Keyring cho shared.privacy.pii_hmac; khoá đầu dùng cho giá trị mới (ADR 0016)
PII_HMAC_KEYS = tuple((kid, secret.get_secret_value()) for kid, secret in env.PII_HMAC_KEYS)
# Secret Next.js gửi trong X-BFF-Secret; 2 giá trị khi đang xoay (05 mục 5)
BFF_SHARED_SECRETS = tuple(secret.get_secret_value() for secret in env.BFF_SHARED_SECRET)
DEBUG = False
ALLOWED_HOSTS: list[str] = []

# Không dùng django.contrib.admin, auth và sessions: không có Django Admin (ADR 0004),
# xác thực bằng JWT từ M1 (ADR 0002)
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "rest_framework",
    "drf_spectacular",
    "django_celery_beat",
    "django_structlog",
    "shared",
    "modules",
]

# Tài khoản là custom user không kế thừa PermissionsMixin (03 mục 2.1)
AUTH_USER_MODEL = "modules.Account"
# Độ mạnh mật khẩu (05 mục 3); Account không có username, first_name nên so với email, full_name
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {"user_attributes": ("email", "full_name")},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Chọn ngôn ngữ theo Accept-Language, mặc định LANGUAGE_CODE; phải đứng trước Common
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    # Gán request.client_ip cho throttle; đứng trước RequestMiddleware để log dùng được
    "shared.api.client_ip.ClientIpMiddleware",
    "django_structlog.middlewares.RequestMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": database_config(env.DATABASE_URL, host=env.DATABASE_HOST)}
# Dùng connection pool của Django 5.2 thay cho kết nối giữ lâu (02 mục 3.1). Timeout ngắn để
# /readyz trả 503 trong timeout 5 giây của health check ALB khi PostgreSQL chết, thay vì chờ
# 30 giây mặc định của psycopg_pool
DATABASES["default"]["OPTIONS"].setdefault("connect_timeout", 3)
DATABASES["default"]["OPTIONS"]["pool"] = {"timeout": 3}
DATABASES["default"]["CONN_MAX_AGE"] = 0
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env.REDIS_URL,
    }
}

LANGUAGE_CODE = "vi"
LANGUAGES = [("vi", "Tiếng Việt"), ("en", "English")]
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {},
    }
]

EMAIL_HOST = env.EMAIL_HOST
EMAIL_PORT = env.EMAIL_PORT

REST_FRAMEWORK: dict[str, object] = {
    # Chưa có xác thực ở M0; JWT thêm ở M1
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    # Mặc định từ chối; view công khai tự khai báo AllowAny (05 mục 4)
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "UNAUTHENTICATED_USER": None,
    # Thêm ErrorDTO và response lỗi mặc định cho mọi operation (04 mục 5.6)
    "DEFAULT_SCHEMA_CLASS": "shared.api.schema.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "shared.api.pagination.StandardPagination",
    "EXCEPTION_HANDLER": "shared.api.exception_handler.exception_handler",
    # Khoá theo pii_hmac(request.client_ip) hoặc Tài khoản (05 mục 5)
    "DEFAULT_THROTTLE_CLASSES": [
        "shared.api.throttling.AnonThrottle",
        "shared.api.throttling.AccountThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "120/min", "account": "300/min"},
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Fashion Store API",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Log JSON ra stdout, đã che PII; local ghi đè bằng log dễ đọc (02 mục 9.6)
LOGGING = configure_logging(json=True)
# django-structlog mặc định gắn `ip` thô (đọc cả X-Client-IP chưa xác minh) vào contextvars,
# nên mọi dòng log của request mang IP; IP chỉ được log dạng pii_hmac (05 mục 5, ADR 0016)
DJANGO_STRUCTLOG_IP_LOGGING_ENABLED = False

CELERY_BROKER_URL = env.REDIS_URL
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# Worker chết giữa chừng thì task được giao lại; công việc thật vẫn nằm trong PostgreSQL
# (07 mục 3.3)
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
# Ngắn hơn hạn giao lại 3 phút của relay (07 mục 1.1.1)
CELERY_TASK_TIME_LIMIT = 120
CELERY_TASK_IGNORE_RESULT = True

# Bật Swagger UI và schema; production tắt (04 mục 4.4)
API_DOCS_ENABLED = True
