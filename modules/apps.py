from django.apps import AppConfig


class ModulesConfig(AppConfig):
    name = "modules"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        # Import trong ready(): shared.events nạp model, chỉ được làm khi app registry sẵn sàng
        from shared.events.registry import autodiscover

        # Nạp events.py và handlers.py của mọi module con để class sự kiện và handler được
        # đăng ký trước khi relay hay worker chạy (02 mục 5)
        autodiscover(self.name)
