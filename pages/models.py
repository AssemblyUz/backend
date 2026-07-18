"""
Editorial content for the home and about pages.

Prose that an editor should be able to change lives here. Interaction chrome
(nav labels, "View all", form placeholders) stays in the frontend message files
— it changes with the code, not with the editor.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import OrderedModel, SingletonModel


class HomeContent(SingletonModel):
    """Hero, section headings and the closing CTA banner on the home page."""

    hero_badge_uz = models.CharField(max_length=200, blank=True, default="")
    hero_badge_ru = models.CharField(max_length=200, blank=True, default="")
    hero_badge_en = models.CharField(max_length=200, blank=True, default="")

    hero_title_uz = models.CharField(max_length=200, blank=True, default="")
    hero_title_ru = models.CharField(max_length=200, blank=True, default="")
    hero_title_en = models.CharField(max_length=200, blank=True, default="")

    hero_lead_uz = models.TextField(blank=True, default="")
    hero_lead_ru = models.TextField(blank=True, default="")
    hero_lead_en = models.TextField(blank=True, default="")

    cta_primary_uz = models.CharField(max_length=100, blank=True, default="")
    cta_primary_ru = models.CharField(max_length=100, blank=True, default="")
    cta_primary_en = models.CharField(max_length=100, blank=True, default="")

    cta_secondary_uz = models.CharField(max_length=100, blank=True, default="")
    cta_secondary_ru = models.CharField(max_length=100, blank=True, default="")
    cta_secondary_en = models.CharField(max_length=100, blank=True, default="")

    about_title_uz = models.CharField(max_length=200, blank=True, default="")
    about_title_ru = models.CharField(max_length=200, blank=True, default="")
    about_title_en = models.CharField(max_length=200, blank=True, default="")

    about_lead_uz = models.TextField(blank=True, default="")
    about_lead_ru = models.TextField(blank=True, default="")
    about_lead_en = models.TextField(blank=True, default="")

    assoc_title_uz = models.CharField(max_length=200, blank=True, default="")
    assoc_title_ru = models.CharField(max_length=200, blank=True, default="")
    assoc_title_en = models.CharField(max_length=200, blank=True, default="")

    assoc_lead_uz = models.TextField(blank=True, default="")
    assoc_lead_ru = models.TextField(blank=True, default="")
    assoc_lead_en = models.TextField(blank=True, default="")

    services_title_uz = models.CharField(max_length=200, blank=True, default="")
    services_title_ru = models.CharField(max_length=200, blank=True, default="")
    services_title_en = models.CharField(max_length=200, blank=True, default="")

    services_lead_uz = models.TextField(blank=True, default="")
    services_lead_ru = models.TextField(blank=True, default="")
    services_lead_en = models.TextField(blank=True, default="")

    projects_title_uz = models.CharField(max_length=200, blank=True, default="")
    projects_title_ru = models.CharField(max_length=200, blank=True, default="")
    projects_title_en = models.CharField(max_length=200, blank=True, default="")

    projects_lead_uz = models.TextField(blank=True, default="")
    projects_lead_ru = models.TextField(blank=True, default="")
    projects_lead_en = models.TextField(blank=True, default="")

    news_title_uz = models.CharField(max_length=200, blank=True, default="")
    news_title_ru = models.CharField(max_length=200, blank=True, default="")
    news_title_en = models.CharField(max_length=200, blank=True, default="")

    news_lead_uz = models.TextField(blank=True, default="")
    news_lead_ru = models.TextField(blank=True, default="")
    news_lead_en = models.TextField(blank=True, default="")

    cta_banner_title_uz = models.CharField(max_length=200, blank=True, default="")
    cta_banner_title_ru = models.CharField(max_length=200, blank=True, default="")
    cta_banner_title_en = models.CharField(max_length=200, blank=True, default="")

    cta_banner_lead_uz = models.TextField(blank=True, default="")
    cta_banner_lead_ru = models.TextField(blank=True, default="")
    cta_banner_lead_en = models.TextField(blank=True, default="")

    cta_banner_btn_uz = models.CharField(max_length=100, blank=True, default="")
    cta_banner_btn_ru = models.CharField(max_length=100, blank=True, default="")
    cta_banner_btn_en = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        verbose_name = _("Home page content")
        verbose_name_plural = _("Home page content")


class Stat(OrderedModel):
    """
    A tile in the home page stats strip.

    `value` is free text, not a number, because the real figures are things like
    "15 000+" and "$ mlrd+". Editing these here is what keeps the strip from
    contradicting the about page.
    """

    value = models.CharField(max_length=30, help_text='e.g. "50+", "10 000+"')

    label_uz = models.CharField(max_length=100, blank=True, default="")
    label_ru = models.CharField(max_length=100, blank=True, default="")
    label_en = models.CharField(max_length=100, blank=True, default="")

    class Meta(OrderedModel.Meta):
        verbose_name = _("Stat")
        verbose_name_plural = _("Stats")

    def __str__(self) -> str:
        return f"{self.value} — {self.label_uz}"


class AboutContent(SingletonModel):
    """Every prose block on the about page. Repeating blocks are separate models."""

    title_uz = models.CharField(max_length=200, blank=True, default="")
    title_ru = models.CharField(max_length=200, blank=True, default="")
    title_en = models.CharField(max_length=200, blank=True, default="")

    lead_uz = models.TextField(blank=True, default="")
    lead_ru = models.TextField(blank=True, default="")
    lead_en = models.TextField(blank=True, default="")

    intro_title_uz = models.CharField(max_length=200, blank=True, default="")
    intro_title_ru = models.CharField(max_length=200, blank=True, default="")
    intro_title_en = models.CharField(max_length=200, blank=True, default="")

    intro_uz = models.TextField(blank=True, default="")
    intro_ru = models.TextField(blank=True, default="")
    intro_en = models.TextField(blank=True, default="")

    principle_uz = models.CharField(max_length=250, blank=True, default="")
    principle_ru = models.CharField(max_length=250, blank=True, default="")
    principle_en = models.CharField(max_length=250, blank=True, default="")

    intro_note_uz = models.TextField(blank=True, default="")
    intro_note_ru = models.TextField(blank=True, default="")
    intro_note_en = models.TextField(blank=True, default="")

    role_title_uz = models.CharField(max_length=200, blank=True, default="")
    role_title_ru = models.CharField(max_length=200, blank=True, default="")
    role_title_en = models.CharField(max_length=200, blank=True, default="")

    mission_section_title_uz = models.CharField(max_length=200, blank=True, default="")
    mission_section_title_ru = models.CharField(max_length=200, blank=True, default="")
    mission_section_title_en = models.CharField(max_length=200, blank=True, default="")

    mission_section_lead_uz = models.TextField(blank=True, default="")
    mission_section_lead_ru = models.TextField(blank=True, default="")
    mission_section_lead_en = models.TextField(blank=True, default="")

    mission_title_uz = models.CharField(max_length=200, blank=True, default="")
    mission_title_ru = models.CharField(max_length=200, blank=True, default="")
    mission_title_en = models.CharField(max_length=200, blank=True, default="")

    mission_uz = models.TextField(blank=True, default="")
    mission_ru = models.TextField(blank=True, default="")
    mission_en = models.TextField(blank=True, default="")

    goal_title_uz = models.CharField(max_length=200, blank=True, default="")
    goal_title_ru = models.CharField(max_length=200, blank=True, default="")
    goal_title_en = models.CharField(max_length=200, blank=True, default="")

    goal_uz = models.TextField(blank=True, default="")
    goal_ru = models.TextField(blank=True, default="")
    goal_en = models.TextField(blank=True, default="")

    goal_note_uz = models.TextField(blank=True, default="")
    goal_note_ru = models.TextField(blank=True, default="")
    goal_note_en = models.TextField(blank=True, default="")

    values_title_uz = models.CharField(max_length=200, blank=True, default="")
    values_title_ru = models.CharField(max_length=200, blank=True, default="")
    values_title_en = models.CharField(max_length=200, blank=True, default="")

    values_lead_uz = models.TextField(blank=True, default="")
    values_lead_ru = models.TextField(blank=True, default="")
    values_lead_en = models.TextField(blank=True, default="")

    directions_title_uz = models.CharField(max_length=200, blank=True, default="")
    directions_title_ru = models.CharField(max_length=200, blank=True, default="")
    directions_title_en = models.CharField(max_length=200, blank=True, default="")

    directions_lead_uz = models.TextField(blank=True, default="")
    directions_lead_ru = models.TextField(blank=True, default="")
    directions_lead_en = models.TextField(blank=True, default="")

    architecture_title_uz = models.CharField(max_length=200, blank=True, default="")
    architecture_title_ru = models.CharField(max_length=200, blank=True, default="")
    architecture_title_en = models.CharField(max_length=200, blank=True, default="")

    architecture_lead_uz = models.TextField(blank=True, default="")
    architecture_lead_ru = models.TextField(blank=True, default="")
    architecture_lead_en = models.TextField(blank=True, default="")

    core_title_uz = models.CharField(max_length=100, blank=True, default="")
    core_title_ru = models.CharField(max_length=100, blank=True, default="")
    core_title_en = models.CharField(max_length=100, blank=True, default="")

    core_sub_uz = models.CharField(max_length=200, blank=True, default="")
    core_sub_ru = models.CharField(max_length=200, blank=True, default="")
    core_sub_en = models.CharField(max_length=200, blank=True, default="")

    architecture_note_uz = models.TextField(blank=True, default="")
    architecture_note_ru = models.TextField(blank=True, default="")
    architecture_note_en = models.TextField(blank=True, default="")

    mechanism_title_uz = models.CharField(max_length=200, blank=True, default="")
    mechanism_title_ru = models.CharField(max_length=200, blank=True, default="")
    mechanism_title_en = models.CharField(max_length=200, blank=True, default="")

    mechanism_lead_uz = models.TextField(blank=True, default="")
    mechanism_lead_ru = models.TextField(blank=True, default="")
    mechanism_lead_en = models.TextField(blank=True, default="")

    formula_title_uz = models.CharField(max_length=200, blank=True, default="")
    formula_title_ru = models.CharField(max_length=200, blank=True, default="")
    formula_title_en = models.CharField(max_length=200, blank=True, default="")

    formula_uz = models.TextField(blank=True, default="")
    formula_ru = models.TextField(blank=True, default="")
    formula_en = models.TextField(blank=True, default="")

    blocks_title_uz = models.CharField(max_length=200, blank=True, default="")
    blocks_title_ru = models.CharField(max_length=200, blank=True, default="")
    blocks_title_en = models.CharField(max_length=200, blank=True, default="")

    blocks_lead_uz = models.TextField(blank=True, default="")
    blocks_lead_ru = models.TextField(blank=True, default="")
    blocks_lead_en = models.TextField(blank=True, default="")

    media_title_uz = models.CharField(max_length=200, blank=True, default="")
    media_title_ru = models.CharField(max_length=200, blank=True, default="")
    media_title_en = models.CharField(max_length=200, blank=True, default="")

    media_lead_uz = models.TextField(blank=True, default="")
    media_lead_ru = models.TextField(blank=True, default="")
    media_lead_en = models.TextField(blank=True, default="")

    media_tagline_uz = models.TextField(blank=True, default="")
    media_tagline_ru = models.TextField(blank=True, default="")
    media_tagline_en = models.TextField(blank=True, default="")

    media_summary_uz = models.TextField(blank=True, default="")
    media_summary_ru = models.TextField(blank=True, default="")
    media_summary_en = models.TextField(blank=True, default="")

    partners_title_uz = models.CharField(max_length=200, blank=True, default="")
    partners_title_ru = models.CharField(max_length=200, blank=True, default="")
    partners_title_en = models.CharField(max_length=200, blank=True, default="")

    partners_lead_uz = models.TextField(blank=True, default="")
    partners_lead_ru = models.TextField(blank=True, default="")
    partners_lead_en = models.TextField(blank=True, default="")

    value_title_uz = models.CharField(max_length=250, blank=True, default="")
    value_title_ru = models.CharField(max_length=250, blank=True, default="")
    value_title_en = models.CharField(max_length=250, blank=True, default="")

    value_lead_uz = models.TextField(blank=True, default="")
    value_lead_ru = models.TextField(blank=True, default="")
    value_lead_en = models.TextField(blank=True, default="")

    roadmap_title_uz = models.CharField(max_length=200, blank=True, default="")
    roadmap_title_ru = models.CharField(max_length=200, blank=True, default="")
    roadmap_title_en = models.CharField(max_length=200, blank=True, default="")

    roadmap_lead_uz = models.TextField(blank=True, default="")
    roadmap_lead_ru = models.TextField(blank=True, default="")
    roadmap_lead_en = models.TextField(blank=True, default="")

    kpi_title_uz = models.CharField(max_length=200, blank=True, default="")
    kpi_title_ru = models.CharField(max_length=200, blank=True, default="")
    kpi_title_en = models.CharField(max_length=200, blank=True, default="")

    results_title_uz = models.CharField(max_length=200, blank=True, default="")
    results_title_ru = models.CharField(max_length=200, blank=True, default="")
    results_title_en = models.CharField(max_length=200, blank=True, default="")

    motto_uz = models.CharField(max_length=250, blank=True, default="")
    motto_ru = models.CharField(max_length=250, blank=True, default="")
    motto_en = models.CharField(max_length=250, blank=True, default="")

    slogan_uz = models.CharField(max_length=250, blank=True, default="")
    slogan_ru = models.CharField(max_length=250, blank=True, default="")
    slogan_en = models.CharField(max_length=250, blank=True, default="")

    class Meta:
        verbose_name = _("About page content")
        verbose_name_plural = _("About page content")


class Highlight(OrderedModel):
    """The 50+ / 20 / FR-BR-PR-GR / AI MediaNet tiles beside the intro."""

    value = models.CharField(max_length=40)

    label_uz = models.CharField(max_length=100, blank=True, default="")
    label_ru = models.CharField(max_length=100, blank=True, default="")
    label_en = models.CharField(max_length=100, blank=True, default="")

    class Meta(OrderedModel.Meta):
        verbose_name = _("Highlight")
        verbose_name_plural = _("Highlights")

    def __str__(self) -> str:
        return self.value


class StrategicRole(OrderedModel):
    """One bullet in the "Strategic role" list."""

    text_uz = models.CharField(max_length=250, blank=True, default="")
    text_ru = models.CharField(max_length=250, blank=True, default="")
    text_en = models.CharField(max_length=250, blank=True, default="")

    class Meta(OrderedModel.Meta):
        verbose_name = _("Strategic role")
        verbose_name_plural = _("Strategic roles")

    def __str__(self) -> str:
        return self.text_uz or self.text_en


class Value(OrderedModel):
    """Birlashuv — kuch, Innovatsiya — rivojlanish, and so on."""

    title_uz = models.CharField(max_length=100, blank=True, default="")
    title_ru = models.CharField(max_length=100, blank=True, default="")
    title_en = models.CharField(max_length=100, blank=True, default="")

    sub_uz = models.CharField(max_length=100, blank=True, default="")
    sub_ru = models.CharField(max_length=100, blank=True, default="")
    sub_en = models.CharField(max_length=100, blank=True, default="")

    class Meta(OrderedModel.Meta):
        verbose_name = _("Value")
        verbose_name_plural = _("Values")

    def __str__(self) -> str:
        return self.title_uz or self.title_en


class Direction(OrderedModel):
    """A priority direction chip (Education, Innovation, Investment, ...)."""

    name_uz = models.CharField(max_length=100, blank=True, default="")
    name_ru = models.CharField(max_length=100, blank=True, default="")
    name_en = models.CharField(max_length=100, blank=True, default="")

    class Meta(OrderedModel.Meta):
        verbose_name = _("Direction")
        verbose_name_plural = _("Directions")

    def __str__(self) -> str:
        return self.name_uz or self.name_en


class ArchitectureNode(OrderedModel):
    """A node in the GPPP architecture diagram."""

    title_uz = models.CharField(max_length=100, blank=True, default="")
    title_ru = models.CharField(max_length=100, blank=True, default="")
    title_en = models.CharField(max_length=100, blank=True, default="")

    desc_uz = models.CharField(max_length=200, blank=True, default="")
    desc_ru = models.CharField(max_length=200, blank=True, default="")
    desc_en = models.CharField(max_length=200, blank=True, default="")

    class Meta(OrderedModel.Meta):
        verbose_name = _("Architecture node")
        verbose_name_plural = _("Architecture nodes")

    def __str__(self) -> str:
        return self.title_uz or self.title_en


class MechanismStep(OrderedModel):
    """One of the six steps in the working mechanism."""

    title_uz = models.CharField(max_length=100, blank=True, default="")
    title_ru = models.CharField(max_length=100, blank=True, default="")
    title_en = models.CharField(max_length=100, blank=True, default="")

    desc_uz = models.CharField(max_length=250, blank=True, default="")
    desc_ru = models.CharField(max_length=250, blank=True, default="")
    desc_en = models.CharField(max_length=250, blank=True, default="")

    class Meta(OrderedModel.Meta):
        verbose_name = _("Mechanism step")
        verbose_name_plural = _("Mechanism steps")

    def __str__(self) -> str:
        return f"{self.order + 1}. {self.title_uz or self.title_en}"


class FunctionalBlock(OrderedModel):
    """One of the FR / BR / PR / GR wings."""

    code = models.CharField(max_length=4, unique=True, help_text="FR, BR, PR or GR")
    title = models.CharField(max_length=100, help_text="e.g. Foreign Relations")

    desc_uz = models.TextField(blank=True, default="")
    desc_ru = models.TextField(blank=True, default="")
    desc_en = models.TextField(blank=True, default="")

    class Meta(OrderedModel.Meta):
        verbose_name = _("Functional block")
        verbose_name_plural = _("Functional blocks")

    def __str__(self) -> str:
        return f"{self.code} — {self.title}"


class MediaFeature(OrderedModel):
    """A capability card under AI MediaNet."""

    title_uz = models.CharField(max_length=150, blank=True, default="")
    title_ru = models.CharField(max_length=150, blank=True, default="")
    title_en = models.CharField(max_length=150, blank=True, default="")

    desc_uz = models.CharField(max_length=250, blank=True, default="")
    desc_ru = models.CharField(max_length=250, blank=True, default="")
    desc_en = models.CharField(max_length=250, blank=True, default="")

    class Meta(OrderedModel.Meta):
        verbose_name = _("Media feature")
        verbose_name_plural = _("Media features")

    def __str__(self) -> str:
        return self.title_uz or self.title_en


class StakeholderValue(OrderedModel):
    """Value delivered to government / entrepreneurs / investors / society."""

    title_uz = models.CharField(max_length=150, blank=True, default="")
    title_ru = models.CharField(max_length=150, blank=True, default="")
    title_en = models.CharField(max_length=150, blank=True, default="")

    desc_uz = models.TextField(blank=True, default="")
    desc_ru = models.TextField(blank=True, default="")
    desc_en = models.TextField(blank=True, default="")

    class Meta(OrderedModel.Meta):
        verbose_name = _("Stakeholder value")
        verbose_name_plural = _("Stakeholder values")

    def __str__(self) -> str:
        return self.title_uz or self.title_en


class RoadmapStage(OrderedModel):
    """A 0-90 day / 6 month / 12 month stage."""

    period_uz = models.CharField(max_length=60, blank=True, default="")
    period_ru = models.CharField(max_length=60, blank=True, default="")
    period_en = models.CharField(max_length=60, blank=True, default="")

    title_uz = models.CharField(max_length=150, blank=True, default="")
    title_ru = models.CharField(max_length=150, blank=True, default="")
    title_en = models.CharField(max_length=150, blank=True, default="")

    desc_uz = models.TextField(blank=True, default="")
    desc_ru = models.TextField(blank=True, default="")
    desc_en = models.TextField(blank=True, default="")

    class Meta(OrderedModel.Meta):
        verbose_name = _("Roadmap stage")
        verbose_name_plural = _("Roadmap stages")

    def __str__(self) -> str:
        return self.period_uz or self.period_en


class Kpi(OrderedModel):
    """A key-indicator tile under the roadmap."""

    value_uz = models.CharField(max_length=40, blank=True, default="")
    value_ru = models.CharField(max_length=40, blank=True, default="")
    value_en = models.CharField(max_length=40, blank=True, default="")

    label_uz = models.CharField(max_length=100, blank=True, default="")
    label_ru = models.CharField(max_length=100, blank=True, default="")
    label_en = models.CharField(max_length=100, blank=True, default="")

    class Meta(OrderedModel.Meta):
        verbose_name = _("KPI")
        verbose_name_plural = _("KPIs")

    def __str__(self) -> str:
        return f"{self.value_uz} {self.label_uz}".strip()


class Result(OrderedModel):
    """A closing "Our result" card."""

    title_uz = models.CharField(max_length=150, blank=True, default="")
    title_ru = models.CharField(max_length=150, blank=True, default="")
    title_en = models.CharField(max_length=150, blank=True, default="")

    desc_uz = models.TextField(blank=True, default="")
    desc_ru = models.TextField(blank=True, default="")
    desc_en = models.TextField(blank=True, default="")

    class Meta(OrderedModel.Meta):
        verbose_name = _("Result")
        verbose_name_plural = _("Results")

    def __str__(self) -> str:
        return self.title_uz or self.title_en
