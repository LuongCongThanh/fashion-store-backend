from django.urls import path

from apps.identity.api.backoffice.views import BackofficeLoginView, BackofficeMeView

app_name = "identity-backoffice"

urlpatterns = [
    path("login", BackofficeLoginView.as_view(), name="login"),
    path("me", BackofficeMeView.as_view(), name="me"),
]
