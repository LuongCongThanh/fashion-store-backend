from django.apps import AppConfig, apps


class CommonConfig(AppConfig):
    name = "common"
    label = "common"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from django_structlog.signals import bind_extra_request_metadata

        from common.api.request_id import bind_upstream_request_id
        from common.events.registry import autodiscover
        from common.security import checks  # noqa: F401  # đăng ký system check

        bind_extra_request_metadata.connect(
            bind_upstream_request_id, dispatch_uid="common.bind_upstream_request_id"
        )
        # Nạp events.py và handlers.py của mọi app để class sự kiện và handler được đăng ký
        # trước khi relay hay worker chạy (02 mục 5). ready() chạy sau khi mọi app đã nạp model
        autodiscover(config.name for config in apps.get_app_configs())
