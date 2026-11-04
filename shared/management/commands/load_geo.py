"""Nạp tỉnh/thành, phường/xã từ `vietnam-provinces` vào database (03 mục 0.7 bước 4).

Package trả mã dạng int enum; lệnh đệm số 0 đứng đầu theo mã Cục Thống kê (tỉnh 2 chữ số,
phường/xã 5 chữ số). Upsert theo mã trong một transaction: thêm mã mới, cập nhật dòng đổi tên.
Mã có trong DB mà không còn trong nguồn được giữ lại vì còn là FK của Địa chỉ, Đơn hàng; lệnh
chỉ log cảnh báo kèm số lượng. Chạy lại không đổi gì.
"""

import structlog
from django.core.management.base import BaseCommand
from django.db import models, transaction
from vietnam_provinces import Province as SourceProvince
from vietnam_provinces import Ward as SourceWard

from shared.geo.models import Province, Ward

logger = structlog.get_logger(__name__)


class Command(BaseCommand):
    help = "Nạp tỉnh/thành, phường/xã từ vietnam-provinces vào database."

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        provinces = [
            Province(code=_province_code(p.code), name=p.name) for p in SourceProvince.iter_all()
        ]
        wards = [
            Ward(code=_ward_code(w.code), province_id=_province_code(w.province_code), name=w.name)
            for w in SourceWard.iter_all()
        ]
        province_counts, stale_provinces = _upsert(Province, provinces, ["name"])
        ward_counts, stale_wards = _upsert(Ward, wards, ["province_id", "name"])
        if stale_provinces or stale_wards:
            logger.warning("geo_stale_codes", provinces=stale_provinces, wards=stale_wards)
        logger.info("geo_loaded", provinces=province_counts, wards=ward_counts)


def _province_code(n: int) -> str:
    return f"{int(n):02d}"


def _ward_code(n: int) -> str:
    return f"{int(n):05d}"


def _upsert[M: models.Model](
    model: type[M], rows: list[M], fields: list[str]
) -> tuple[dict[str, int], int]:
    """Ghi các dòng mới hoặc khác DB ở `fields`; trả số dòng theo loại và số mã chỉ còn ở DB."""
    existing = {
        pk: tuple(values) for pk, *values in model._default_manager.values_list("pk", *fields)
    }
    created = [row for row in rows if row.pk not in existing]
    updated = [
        row
        for row in rows
        if row.pk in existing and tuple(getattr(row, f) for f in fields) != existing[row.pk]
    ]
    model._default_manager.bulk_create(
        created + updated,
        update_conflicts=True,
        unique_fields=[model._meta.pk.name],
        update_fields=fields,
    )
    counts = {
        "created": len(created),
        "updated": len(updated),
        "unchanged": len(rows) - len(created) - len(updated),
    }
    return counts, len(existing.keys() - {row.pk for row in rows})
