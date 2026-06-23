from django.apps import AppConfig
class SocialConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "social"

    def ready(self):
        from . import signals  # noqa: F401  (친구 요청·수락 알림 Signal 등록, F-NTF-01)
