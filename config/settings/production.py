# Cách tách settings chuẩn của Django: kế thừa mọi giá trị của base rồi ghi đè
from config.settings.base import *  # noqa: F403  # NOSONAR

# ALLOWED_HOSTS, S3, SES và Sentry cấu hình khi dựng hạ tầng AWS (09)
API_DOCS_ENABLED = False

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
# Health check của ALB gọi thẳng target bằng HTTP, không qua chuyển hướng HTTPS
SECURE_REDIRECT_EXEMPT = [r"^healthz$", r"^readyz$"]
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
