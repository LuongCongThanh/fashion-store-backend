"""Phân trang chuẩn cho API: `page_size` mặc định 24, tối đa 100 (04 mục 5.1).

`page` hoặc `page_size` không phải số nguyên dương → `400 VALIDATION_ERROR`; trang vượt quá
cuối vẫn là `404 NOT_FOUND`.
"""

from django.core.paginator import Paginator
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request

NOT_AN_INTEGER_MESSAGE = _("Phải là số nguyên.")
BELOW_ONE_MESSAGE = _("Phải lớn hơn hoặc bằng 1.")


def _positive_int(raw: str, field: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise ValidationError({field: [NOT_AN_INTEGER_MESSAGE]}) from None
    if value < 1:
        raise ValidationError({field: [BELOW_ONE_MESSAGE]})
    return value


class StandardPagination(PageNumberPagination):
    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_page_size(self, request: Request) -> int:
        raw = request.query_params.get(self.page_size_query_param)
        if raw is None:
            return self.page_size
        return min(_positive_int(raw, self.page_size_query_param), self.max_page_size)

    def get_page_number(self, request: Request, paginator: Paginator) -> int:
        # Như DRF: thiếu hoặc rỗng thì trang 1, "last" là trang cuối
        raw = request.query_params.get(self.page_query_param) or "1"
        if raw in self.last_page_strings:
            return paginator.num_pages
        return _positive_int(raw, self.page_query_param)
