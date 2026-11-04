"""Django chỉ nhận model qua `<app>/models.py` (02 mục 5): import model của mọi module con."""

from modules.identity.models import Account, RefreshReplay, RefreshToken  # noqa: F401
