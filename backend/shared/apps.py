from django.apps import AppConfig


class SharedConfig(AppConfig):
    name = "shared"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from django_structlog.signals import bind_extra_request_metadata

        from shared import checks  # noqa: F401  # đăng ký system check
        from shared.api.request_id import bind_upstream_request_id

        bind_extra_request_metadata.connect(bind_upstream_request_id)
