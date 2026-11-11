"""
Rewrite the Uzbek content already in the database into the reformed alphabet.

    python manage.py convert_uz_alphabet --dry-run   # report only
    python manage.py convert_uz_alphabet             # write

New and edited content is converted as it is saved (core.signals); this is the
one-off for rows that were written before that existed. It is safe to run more
than once — converted text passes through unchanged, so a second run reports
nothing to do.

Rows are written with `update()` rather than `save()`: that leaves `updated_at`
alone, so re-spelling an article does not make it look freshly edited, and it
does not re-trigger machine translation.
"""

from __future__ import annotations

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from core.signals import uzbek_text_fields
from core.uzlatin import to_new

_SAMPLES_PER_MODEL = 3


class Command(BaseCommand):
    help = "Convert stored Uzbek text (oʻ gʻ sh ch) to the reformed alphabet (õ ğ ş ç)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        total_rows = 0
        total_fields = 0

        with transaction.atomic():
            for model in apps.get_models():
                fields = uzbek_text_fields(model)
                if not fields:
                    continue

                rows, changed_fields, samples = self._convert_model(model, fields, dry_run)
                if not rows:
                    continue

                total_rows += rows
                total_fields += changed_fields
                self.stdout.write(
                    f"  {model._meta.label:<28} {rows} rows, {changed_fields} fields"
                )
                if options["verbosity"] >= 2:
                    for before, after in samples:
                        self.stdout.write(f"      {before}\n   -> {after}")

        if not total_rows:
            self.stdout.write(self.style.SUCCESS("Nothing to convert."))
            return

        summary = f"{total_rows} rows, {total_fields} fields"
        if dry_run:
            self.stdout.write(self.style.WARNING(f"Dry run — would convert {summary}."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Converted {summary}."))

    def _convert_model(self, model, fields, dry_run):
        rows = 0
        changed_fields = 0
        samples: list[tuple[str, str]] = []

        for pk, *values in model._default_manager.values_list("pk", *fields).iterator():
            changes = {
                name: to_new(value)
                for name, value in zip(fields, values)
                if value and to_new(value) != value
            }
            if not changes:
                continue

            rows += 1
            changed_fields += len(changes)
            if len(samples) < _SAMPLES_PER_MODEL:
                name, after = next(iter(changes.items()))
                before = values[fields.index(name)]
                samples.append((before[:100], after[:100]))
            if not dry_run:
                model._default_manager.filter(pk=pk).update(**changes)

        return rows, changed_fields, samples
