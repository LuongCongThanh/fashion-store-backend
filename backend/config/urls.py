from django.conf import settings
from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

from shared.health import views as health

# Route lạ, lỗi ngoài DRF và exception không bắt cũng trả ErrorDTO (04 mục 3)
handler400 = "shared.api.views.bad_request"
handler403 = "shared.api.views.permission_denied"
handler404 = "shared.api.views.not_found"
handler500 = "shared.api.views.server_error"

urlpatterns: list[URLPattern | URLResolver] = [
    path("healthz", health.healthz, name="healthz"),
    path("readyz", health.readyz, name="readyz"),
    path("api/v1/store/geo/", include("shared.geo.urls")),
    path("api/v1/backoffice/auth/", include("modules.identity.api.backoffice.urls")),
]

if settings.API_DOCS_ENABLED:
    urlpatterns += [
        # Mặc định mọi view cần đăng nhập; schema và Swagger UI để công khai
        path(
            "api/schema/",
            SpectacularAPIView.as_view(permission_classes=[AllowAny]),
            name="schema",
        ),
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[AllowAny]),
            name="docs",
        ),
    ]
