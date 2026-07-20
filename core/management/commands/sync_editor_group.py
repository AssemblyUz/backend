"""
Reconcile the "Editor" group with the current set of content models.

    python manage.py sync_editor_group

This normally runs automatically after every `migrate`, so you only need it by
hand to repair a group somebody edited in the admin, or to check what an editor
can currently reach.
"""

from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS

from core.groups import GROUP_NAME, sync_editor_group


class Command(BaseCommand):
    help = "Create or update the Editor group's permissions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Database to reconcile. Defaults to the default alias.",
        )

    def handle(self, *args, **options):
        count = sync_editor_group(using=options["database"])
        self.stdout.write(
            self.style.SUCCESS(f'"{GROUP_NAME}" group now holds {count} permission(s).')
        )
