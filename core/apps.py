from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = _("Site")

    def ready(self):
        # Reconcile the Editor group after every `migrate`, so a database
        # upgraded in place and one built from scratch end up identical.
        from .groups import handle_post_migrate

        post_migrate.connect(handle_post_migrate, sender=self)
