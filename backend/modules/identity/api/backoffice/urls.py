from django.urls import path

from modules.identity.api.backoffice.views import BackofficeLoginView

app_name = "identity-backoffice"

urlpatterns = [path("login", BackofficeLoginView.as_view(), name="login")]
