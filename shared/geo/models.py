"""Địa giới hành chính 2 cấp sau 07/2025 (03 mục 1.1, 1.2), nạp bằng lệnh `load_geo`.

Khoá chính là mã Cục Thống kê có số 0 đứng đầu, không kế thừa `BaseModel` (ADR 0008).
"""

from django.db import models


class Province(models.Model):
    code = models.CharField(primary_key=True, max_length=10)
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "shared_province"

    def __str__(self) -> str:
        return self.name


class Ward(models.Model):
    code = models.CharField(primary_key=True, max_length=10)
    province = models.ForeignKey(
        Province, on_delete=models.PROTECT, related_name="wards", db_column="province_code"
    )
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "shared_ward"

    def __str__(self) -> str:
        return self.name
