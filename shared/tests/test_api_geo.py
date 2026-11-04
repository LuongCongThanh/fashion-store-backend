import pytest
from django.test import Client

from shared.testing.factories import ProvinceFactory, WardFactory
from shared.tests._helpers import error_of

pytestmark = pytest.mark.django_db


def test_provinces_returns_unpaginated_array_ordered_by_code(client: Client) -> None:
    ProvinceFactory(code="79", name="Thành phố Hồ Chí Minh")
    ProvinceFactory(code="01", name="Thành phố Hà Nội")

    response = client.get("/api/v1/store/geo/provinces")

    assert response.status_code == 200
    assert response.json() == [
        {"code": "01", "name": "Thành phố Hà Nội"},
        {"code": "79", "name": "Thành phố Hồ Chí Minh"},
    ]


def test_wards_of_province_returns_unpaginated_array(client: Client) -> None:
    ha_noi = ProvinceFactory(code="01")
    WardFactory(code="00008", province=ha_noi, name="Phường Ngọc Hà")
    WardFactory(code="00004", province=ha_noi, name="Phường Ba Đình")
    WardFactory(code="26734", province=ProvinceFactory(code="79"))
    ProvinceFactory(code="02")

    response = client.get("/api/v1/store/geo/provinces/01/wards")
    empty = client.get("/api/v1/store/geo/provinces/02/wards")

    assert response.status_code == 200
    assert response.json() == [
        {"code": "00004", "name": "Phường Ba Đình"},
        {"code": "00008", "name": "Phường Ngọc Hà"},
    ]
    assert (empty.status_code, empty.json()) == (200, [])


def test_geo_endpoints_are_public(client: Client) -> None:
    # Mặc định view cần đăng nhập (05 mục 4); 04 mục 4.1 ghi địa giới là Công khai
    ProvinceFactory(code="01")

    provinces = client.get("/api/v1/store/geo/provinces")
    wards = client.get("/api/v1/store/geo/provinces/01/wards")

    assert (provinces.status_code, wards.status_code) == (200, 200)


def test_wards_of_unknown_province_returns_404_error_dto(client: Client) -> None:
    response = client.get("/api/v1/store/geo/provinces/99/wards")

    assert response.status_code == 404
    error = error_of(response)
    assert (error["code"], error["details"]) == ("NOT_FOUND", {})
