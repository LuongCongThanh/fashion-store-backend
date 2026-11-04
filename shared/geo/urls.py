from django.urls import path

from shared.geo import api

urlpatterns = [
    path("provinces", api.ProvinceListView.as_view(), name="geo-provinces"),
    path("provinces/<str:code>/wards", api.WardListView.as_view(), name="geo-wards"),
]
