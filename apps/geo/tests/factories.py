"""Factory của geo (02 mục 4.4, 13 mục 9)."""

import factory
from factory.django import DjangoModelFactory

from apps.geo.models import Province, Ward


class ProvinceFactory(DjangoModelFactory[Province]):
    class Meta:
        model = Province

    code = factory.Sequence(lambda n: f"{n:02d}")
    name = factory.Sequence(lambda n: f"Tỉnh {n}")


class WardFactory(DjangoModelFactory[Ward]):
    class Meta:
        model = Ward

    code = factory.Sequence(lambda n: f"{n:05d}")
    province = factory.SubFactory(ProvinceFactory)
    name = factory.Sequence(lambda n: f"Phường {n}")
