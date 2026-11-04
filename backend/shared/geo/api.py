"""GET /api/v1/store/geo/provinces và /geo/provinces/{code}/wards (04 mục 4.1).

Công khai, trả array `GeoDTO` không phân trang (04 mục 5.1).
"""

from typing import Any

from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_serializer
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from shared.geo import selectors
from shared.geo.models import Province, Ward


@extend_schema_serializer(component_name="GeoDTO")
class GeoOutput(serializers.Serializer[Any]):
    code = serializers.CharField(max_length=10)
    name = serializers.CharField(max_length=255)


# View khai ví dụ riêng vì `GeoDTO` dùng chung cho tỉnh và phường/xã; tên giữ không dấu vì chữ
# trên Swagger viết tiếng Anh
@extend_schema(
    summary="List provinces",
    examples=[OpenApiExample("Province", value={"code": "01", "name": "Ha Noi"})],
)
class ProvinceListView(ListAPIView[Province]):
    permission_classes = (AllowAny,)
    pagination_class = None
    serializer_class = GeoOutput

    def get_queryset(self) -> QuerySet[Province]:
        return selectors.list_provinces()


@extend_schema(
    summary="List wards of a province",
    examples=[OpenApiExample("Ward", value={"code": "00004", "name": "Ba Dinh"})],
)
class WardListView(ListAPIView[Ward]):
    permission_classes = (AllowAny,)
    pagination_class = None
    serializer_class = GeoOutput

    def get_queryset(self) -> QuerySet[Ward]:
        code = self.kwargs["code"]
        # Tỉnh có nhưng chưa có phường/xã vẫn trả []; chỉ mã tỉnh lạ mới là 404
        if not selectors.province_exists(code=code):
            raise NotFound
        return selectors.list_wards(province_code=code)
