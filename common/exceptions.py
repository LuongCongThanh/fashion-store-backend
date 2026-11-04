"""Lỗi chung cho mọi module (02 mục 6.1, 04 mục 3, 07 mục 1.3)."""

from typing import Any, ClassVar

from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _


class DomainError(Exception):
    """Lỗi nghiệp vụ; lớp con khai báo `code`, `http_status` và `message` mặc định.

    `http_status` theo 04 mục 3: 409 khi kết quả phụ thuộc trạng thái có thể đã đổi, 422 khi
    chính yêu cầu không thoả quy tắc. `exception_handler` của API đọc các thuộc tính này để
    dựng `ErrorDTO`; consumer của outbox chuyển delivery sang `rejected`.
    """

    code: ClassVar[str] = "DOMAIN_ERROR"
    http_status: ClassVar[int] = 422
    message: str | Promise = _("Yêu cầu không thoả quy tắc nghiệp vụ.")

    def __init__(
        self, message: str | Promise | None = None, details: dict[str, Any] | None = None
    ) -> None:
        if message is not None:
            self.message = message
        self.details: dict[str, Any] = details or {}
        super().__init__(str(self.message))


class RetryLater(Exception):
    """Handler báo consumer thử lại sau, ví dụ sự kiện tới trước trạng thái nguồn.

    Không kế thừa `DomainError`: `DomainError` làm delivery bị `rejected`, còn lỗi này giữ
    delivery `pending` để retry (07 mục 1.3).
    """
