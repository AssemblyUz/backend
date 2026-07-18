"""Admin plumbing shared across apps, plus site settings and social links."""

from django.contrib import admin
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from .models import LOCALES, SiteSettings, SocialLink

#: Badge appended to a translated field's label, e.g. "Sarlavha (UZ)".
LOCALE_BADGE = {"uz": "UZ", "ru": "RU", "en": "EN"}


def field_label(field_name: str):
    """
    A translated, human label for a model field.

    `hero_title_uz` becomes "<translated 'Hero title'> (UZ)". The base name is
    passed through gettext at request time; a base with no catalogue entry falls
    back to its English humanisation, so a missing translation degrades to
    readable English rather than a blank label.
    """
    base, sep, suffix = field_name.rpartition("_")
    if sep and suffix in LOCALE_BADGE:
        return format_lazy("{} ({})", _(humanize(base)), LOCALE_BADGE[suffix])
    return _(humanize(field_name))


def humanize(field_name: str) -> str:
    return field_name.replace("_", " ").capitalize()


class LocalizedLabelsMixin:
    """
    Translates form field labels on change forms.

    Django derives labels from a field's `verbose_name`. Setting that on all
    ~300 per-locale columns would mean an AlterField migration for every one, so
    the label is resolved here at render time instead.
    """

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if formfield is not None:
            formfield.label = field_label(db_field.name)
        return formfield


class SingletonAdmin(LocalizedLabelsMixin, admin.ModelAdmin):
    """
    Admin for a one-row model: no add, no delete, and the change list jumps
    straight to the single object.
    """

    def has_add_permission(self, request):
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        self.model.load()  # ensure row 1 exists before redirecting to it
        return super().changelist_view(request, extra_context)


def locale_fieldsets(*groups):
    """
    Build fieldsets that group each base field's three locale columns together,
    so an editor sees title (uz/ru/en) side by side rather than scattered.

        locale_fieldsets((_("Hero"), ("hero_title", "hero_lead")))
    """
    fieldsets = []
    for label, base_fields in groups:
        fields = tuple(f"{name}_{loc}" for name in base_fields for loc in LOCALES)
        fieldsets.append((label, {"fields": fields}))
    return fieldsets


@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonAdmin):
    fieldsets = (
        *locale_fieldsets(
            (_("Identity"), ("name", "short", "tagline", "description")),
            (_("Address"), ("address",)),
        ),
        (_("Contact"), {"fields": ("email", "phone")}),
    )


@admin.register(SocialLink)
class SocialLinkAdmin(LocalizedLabelsMixin, admin.ModelAdmin):
    list_display = ("name", "platform", "url", "order")
    list_editable = ("url", "order")
    ordering = ("order", "pk")
