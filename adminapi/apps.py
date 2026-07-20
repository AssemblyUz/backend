from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AdminApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "adminapi"
    verbose_name = _("Control panel API")
