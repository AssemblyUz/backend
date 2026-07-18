"""Member associations, services, strategic projects and the partner ecosystem."""

import re

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import OrderedModel


def slugify_name(value: str) -> str:
    """
    Mirror of the frontend `slugify()` in src/data/associations.ts, so slugs
    generated here match the URLs already published and indexed.
    """
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"['\"«»()]", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


class Association(OrderedModel):
    """A member association. Slug is derived from the English name and is stable."""

    slug = models.SlugField(
        max_length=200,
        unique=True,
        blank=True,
        help_text="Left blank, this is generated from the English name.",
    )

    name_uz = models.CharField(max_length=250, blank=True, default="")
    name_ru = models.CharField(max_length=250, blank=True, default="")
    name_en = models.CharField(max_length=250)

    activity_uz = models.TextField(blank=True, default="")
    activity_ru = models.TextField(blank=True, default="")
    activity_en = models.TextField(blank=True, default="")

    chairman = models.CharField(max_length=150, blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")

    is_published = models.BooleanField(default=True)

    class Meta(OrderedModel.Meta):
        verbose_name = _("Association")
        verbose_name_plural = _("Associations")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify_name(self.name_en)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name_en or self.name_uz


class Service(OrderedModel):
    """A professional service offered to members and partners."""

    icon = models.CharField(max_length=8, help_text="A single emoji, e.g. ⚖️")

    name_uz = models.CharField(max_length=200, blank=True, default="")
    name_ru = models.CharField(max_length=200, blank=True, default="")
    name_en = models.CharField(max_length=200, blank=True, default="")

    desc_uz = models.TextField(blank=True, default="")
    desc_ru = models.TextField(blank=True, default="")
    desc_en = models.TextField(blank=True, default="")

    is_published = models.BooleanField(default=True)

    class Meta(OrderedModel.Meta):
        verbose_name = _("Service")
        verbose_name_plural = _("Services")

    def __str__(self) -> str:
        return self.name_uz or self.name_en


class Project(OrderedModel):
    """
    One of the strategic projects.

    `name` is not translated: EDU-JOB, INVEST HUB and the rest are proper nouns
    that read identically in all three locales. A blank `url` renders the
    "In development" badge, which is the behaviour projectLinks.ts already has.
    """

    icon = models.CharField(max_length=8, help_text="A single emoji, e.g. 🎓")
    name = models.CharField(max_length=100, unique=True)

    desc_uz = models.TextField(blank=True, default="")
    desc_ru = models.TextField(blank=True, default="")
    desc_en = models.TextField(blank=True, default="")

    url = models.URLField(
        blank=True,
        default="",
        help_text="Public site. Leave blank to show the 'In development' badge.",
    )
    is_published = models.BooleanField(default=True)

    class Meta(OrderedModel.Meta):
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")

    def __str__(self) -> str:
        return self.name


class PartnerGroup(OrderedModel):
    """A column in the partner ecosystem, e.g. "International financial institutions"."""

    title_uz = models.CharField(max_length=150, blank=True, default="")
    title_ru = models.CharField(max_length=150, blank=True, default="")
    title_en = models.CharField(max_length=150, blank=True, default="")

    class Meta(OrderedModel.Meta):
        verbose_name = _("Partner group")
        verbose_name_plural = _("Partner groups")

    def __str__(self) -> str:
        return self.title_uz or self.title_en


class Partner(OrderedModel):
    """
    A single partner inside a group.

    Most names (EBRD, KPMG, Huawei) are identical across locales, so `name` is
    untranslated; the few that differ — ministries, agencies — use the optional
    per-locale overrides.
    """

    group = models.ForeignKey(
        PartnerGroup, on_delete=models.CASCADE, related_name="partners"
    )

    name = models.CharField(max_length=150, help_text="Used when no override is set.")
    name_uz = models.CharField(max_length=150, blank=True, default="")
    name_ru = models.CharField(max_length=150, blank=True, default="")
    name_en = models.CharField(max_length=150, blank=True, default="")

    url = models.URLField(blank=True, default="")

    class Meta(OrderedModel.Meta):
        verbose_name = _("Partner")
        verbose_name_plural = _("Partners")

    def display_name(self, locale: str) -> str:
        return getattr(self, f"name_{locale}", "") or self.name

    def __str__(self) -> str:
        return self.name
