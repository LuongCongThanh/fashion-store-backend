"""Health check cho ALB và ECS (04 mục 4.4, 10 mục 2)."""

import structlog
from django.db import DatabaseError, connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

logger = structlog.get_logger(__name__)


@require_GET
def healthz(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@require_GET
def readyz(request: HttpRequest) -> JsonResponse:
    # Chỉ kiểm tra PostgreSQL, không kiểm tra Redis, để API vẫn phục vụ khi Redis lỗi
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        logger.warning("readyz_database_unavailable")
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
