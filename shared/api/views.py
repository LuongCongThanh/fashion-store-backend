"""`handler400`/`403`/`404`/`500` của Django trả `ErrorDTO` như lỗi trong view DRF (04 mục 3).

Các handler này lo lỗi ngoài DRF (route lạ, view Django thường, `SuspiciousOperation`, exception
không bắt). Không đưa nội dung exception vào response.

Chữ ký `(request, exception)` / `(request)` là bắt buộc: Django gọi `callback(request,
exception=exception)` theo tên và `check` (`urls.E007`) kiểm số tham số, nên `NOSONAR` bỏ cảnh
báo tham số không dùng.
"""

from django.http import HttpRequest, JsonResponse
from django.utils.translation import gettext_lazy as _

from shared.api.exception_handler import error_body


def bad_request(request: HttpRequest, exception: Exception) -> JsonResponse:  # NOSONAR
    # Không có field cụ thể như VALIDATION_ERROR: thường là SuspiciousOperation (host lạ,
    # header hoặc body sai), Django đã log ở logger django.security
    return JsonResponse(error_body("BAD_REQUEST", _("Yêu cầu không hợp lệ.")), status=400)


def permission_denied(request: HttpRequest, exception: Exception) -> JsonResponse:  # NOSONAR
    return JsonResponse(
        error_body("PERMISSION_DENIED", _("Bạn không có quyền thực hiện thao tác này.")),
        status=403,
    )


def not_found(request: HttpRequest, exception: Exception) -> JsonResponse:  # NOSONAR
    return JsonResponse(error_body("NOT_FOUND", _("Không tìm thấy.")), status=404)


def server_error(request: HttpRequest) -> JsonResponse:  # NOSONAR
    # Django đã log kèm traceback
    return JsonResponse(error_body("INTERNAL_ERROR", _("Lỗi hệ thống.")), status=500)
