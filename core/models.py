"""Shared building blocks: locale handling, singletons, ordering, site settings."""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

#: Locales the site publishes in.
LOCALES = ("uz", "ru", "en")

#: Used when a requested locale is unknown, or a translation is left blank.
DEFAULT_LOCALE = "uz"

LOCALE_CHOICES = [("uz", "O'zbekcha"), ("ru", "Русский"), ("en", "English")]


def resolve_locale(value: str | None) -> str:
    """Coerce an untrusted locale string to one we actually support."""
    return value if value in LOCALES else DEFAULT_LOCALE


def translated(obj, field: str, locale: str) -> str:
    """
    Read `field` in `locale`, falling back to the default locale when the
    translation is blank. Editors can publish in Uzbek first and fill in Russian
    and English later without the site rendering empty strings.
    """
    value = getattr(obj, f"{field}_{resolve_locale(locale)}", "")
    return value or getattr(obj, f"{field}_{DEFAULT_LOCALE}", "")


class SingletonModel(models.Model):
    """A model with exactly one row — used for page-level content blocks."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            f"{self._meta.verbose_name} is a singleton and cannot be deleted."
        )

    @classmethod
    def load(cls):
        """Fetch the single row, creating it from field defaults if absent."""
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self) -> str:
        # The admin renders this as the object's subtitle, so it must follow the
        # active language rather than being a hardcoded English name.
        return str(self._meta.verbose_name)


class OrderedModel(models.Model):
    """Editor-controlled display order. Ties break on primary key for stability."""

    order = models.PositiveIntegerField(
        default=0, help_text="Lower numbers appear first."
    )

    class Meta:
        abstract = True
        ordering = ["order", "pk"]


class SiteSettings(SingletonModel):
    """Organisation identity and contact details, shown in the header and footer."""

    name_uz = models.CharField(max_length=200, blank=True, default="")
    name_ru = models.CharField(max_length=200, blank=True, default="")
    name_en = models.CharField(max_length=200, blank=True, default="")

    short_uz = models.CharField(max_length=100, blank=True, default="")
    short_ru = models.CharField(max_length=100, blank=True, default="")
    short_en = models.CharField(max_length=100, blank=True, default="")

    tagline_uz = models.CharField(max_length=250, blank=True, default="")
    tagline_ru = models.CharField(max_length=250, blank=True, default="")
    tagline_en = models.CharField(max_length=250, blank=True, default="")

    description_uz = models.TextField(blank=True, default="")
    description_ru = models.TextField(blank=True, default="")
    description_en = models.TextField(blank=True, default="")

    address_uz = models.CharField(max_length=250, blank=True, default="")
    address_ru = models.CharField(max_length=250, blank=True, default="")
    address_en = models.CharField(max_length=250, blank=True, default="")

    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        verbose_name = _("Site settings")
        verbose_name_plural = _("Site settings")


class SocialLink(OrderedModel):
    """
    Footer social profiles. A blank `url` renders the icon as "not connected
    yet" instead of a dead link — the behaviour the frontend already has.
    """

    PLATFORMS = [
        ("telegram", "Telegram"),
        ("instagram", "Instagram"),
        ("facebook", "Facebook"),
        ("youtube", "YouTube"),
    ]

    platform = models.CharField(max_length=20, choices=PLATFORMS, unique=True)
    name = models.CharField(max_length=50)
    url = models.URLField(blank=True, default="")

    class Meta(OrderedModel.Meta):
        verbose_name = _("Social link")
        verbose_name_plural = _("Social links")

    def __str__(self) -> str:
        return self.name
