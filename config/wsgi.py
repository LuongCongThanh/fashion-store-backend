import os

from django.core.exceptions import ImproperlyConfigured
from django.core.wsgi import get_wsgi_application

# Không mặc định về settings nào: process deploy thiếu biến thì dừng, thay vì chạy với
# settings local (DEBUG = True)
if "DJANGO_SETTINGS_MODULE" not in os.environ:
    raise ImproperlyConfigured("Chưa đặt biến môi trường DJANGO_SETTINGS_MODULE")

application = get_wsgi_application()
