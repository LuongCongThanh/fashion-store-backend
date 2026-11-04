from django.urls import path

from apps.identity.api.backoffice.views import (
    BackofficeLoginView,
    BackofficeLogoutView,
    BackofficeMeView,
    BackofficeRefreshView,
)

app_name = "identity-backoffice"

urlpatterns = [
    path("login", BackofficeLoginView.as_view(), name="login"),
    path("refresh", BackofficeRefreshView.as_view(), name="refresh"),
    path("logout", BackofficeLogoutView.as_view(), name="logout"),
    path("me", BackofficeMeView.as_view(), name="me"),
]
