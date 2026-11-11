"""
Keep every Uzbek field in the reformed alphabet, however it was typed.

One `pre_save` handler rather than a `save()` override per model: Uzbek prose
lives in some eighty `*_uz` columns across five apps, and a model added later
is covered without anyone remembering to opt it in. Whatever path the text
takes — the control panel, Django admin, `seed_content`, a shell — it passes
through here.

Only the `_uz` columns are touched. Shared, untranslated columns (project
names, slugs, a chairman's name) are the same string in all three languages and
are left exactly as entered.
"""

from __future__ import annotations

from functools import cache

from django.db import models

from .uzlatin import to_new

UZ_SUFFIX = "_uz"


@cache
def uzbek_text_fields(model: type[models.Model]) -> tuple[str, ...]:
    """Names of the model's Uzbek prose columns."""
    return tuple(
        field.attname
        for field in model._meta.concrete_fields
        if field.attname.endswith(UZ_SUFFIX)
        and isinstance(field, (models.CharField, models.TextField))
    )


def convert_uzbek_fields(sender, instance, raw=False, update_fields=None, **kwargs) -> None:
    # Fixtures are loaded verbatim: `raw` means "write exactly this row".
    if raw:
        return

    # Only columns this save will actually write. Reading a deferred field
    # costs a query, and converting one outside `update_fields` would leave the
    # instance disagreeing with the row.
    deferred = instance.get_deferred_fields()
    for name in uzbek_text_fields(sender):
        if name in deferred or (update_fields is not None and name not in update_fields):
            continue
        value = getattr(instance, name)
        if isinstance(value, str) and value:
            converted = to_new(value)
            if converted != value:
                setattr(instance, name, converted)
