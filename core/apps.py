from django.apps import AppConfig
from django.db.models.signals import post_migrate, pre_save
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

        # Uzbek text is stored in the reformed alphabet whatever the editor
        # typed. No `sender`: it applies to every model with `*_uz` columns.
        from .signals import convert_uzbek_fields

        pre_save.connect(convert_uzbek_fields, dispatch_uid="core.convert_uzbek_fields")
