from django.apps import AppConfig


class TasteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "taste"

    def ready(self):
        from . import signals  # noqa: F401  (시그널 등록)
