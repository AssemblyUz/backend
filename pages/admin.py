"""Admin for home and about page content."""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from core.admin import LocalizedLabelsMixin, SingletonAdmin, locale_fieldsets

from .models import (
    AboutContent,
    ArchitectureNode,
    Direction,
    FunctionalBlock,
    Highlight,
    HomeContent,
    Kpi,
    MechanismStep,
    MediaFeature,
    Result,
    RoadmapStage,
    StakeholderValue,
    Stat,
    StrategicRole,
    Value,
)


@admin.register(HomeContent)
class HomeContentAdmin(SingletonAdmin):
    fieldsets = locale_fieldsets(
        (_("Hero"), ("hero_badge", "hero_title", "hero_lead", "cta_primary", "cta_secondary")),
        (_("About band"), ("about_title", "about_lead")),
        (_("Section headings"), (
            "assoc_title", "assoc_lead",
            "services_title", "services_lead",
            "projects_title", "projects_lead",
            "news_title", "news_lead",
        )),
        (_("Closing banner"), ("cta_banner_title", "cta_banner_lead", "cta_banner_btn")),
    )


@admin.register(AboutContent)
class AboutContentAdmin(SingletonAdmin):
    fieldsets = locale_fieldsets(
        (_("Page header"), ("title", "lead")),
        (_("Introduction"), ("intro_title", "intro", "principle", "intro_note", "role_title")),
        (_("Mission & goal"), (
            "mission_section_title", "mission_section_lead",
            "mission_title", "mission",
            "goal_title", "goal", "goal_note",
        )),
        (_("Values"), ("values_title", "values_lead")),
        (_("Directions"), ("directions_title", "directions_lead")),
        (_("Architecture"), (
            "architecture_title", "architecture_lead",
            "core_title", "core_sub", "architecture_note",
        )),
        (_("Mechanism"), ("mechanism_title", "mechanism_lead", "formula_title", "formula")),
        (_("FR/BR/PR/GR"), ("blocks_title", "blocks_lead")),
        (_("AI MediaNet"), ("media_title", "media_lead", "media_tagline", "media_summary")),
        (_("Partners"), ("partners_title", "partners_lead")),
        (_("Stakeholder value"), ("value_title", "value_lead")),
        (_("Roadmap & KPI"), ("roadmap_title", "roadmap_lead", "kpi_title")),
        (_("Results & slogan"), ("results_title", "motto", "slogan")),
    )


class OrderedBlockAdmin(LocalizedLabelsMixin, admin.ModelAdmin):
    """Shared list config for the small repeating about-page blocks."""

    ordering = ("order", "pk")
    list_editable = ("order",)


@admin.register(Stat)
class StatAdmin(OrderedBlockAdmin):
    list_display = ("value", "label_uz", "label_ru", "label_en", "order")


@admin.register(Highlight)
class HighlightAdmin(OrderedBlockAdmin):
    list_display = ("value", "label_uz", "label_en", "order")


@admin.register(StrategicRole)
class StrategicRoleAdmin(OrderedBlockAdmin):
    list_display = ("text_uz", "text_en", "order")


@admin.register(Value)
class ValueAdmin(OrderedBlockAdmin):
    list_display = ("title_uz", "sub_uz", "title_en", "order")


@admin.register(Direction)
class DirectionAdmin(OrderedBlockAdmin):
    list_display = ("name_uz", "name_ru", "name_en", "order")


@admin.register(ArchitectureNode)
class ArchitectureNodeAdmin(OrderedBlockAdmin):
    list_display = ("title_uz", "desc_uz", "title_en", "order")


@admin.register(MechanismStep)
class MechanismStepAdmin(OrderedBlockAdmin):
    list_display = ("title_uz", "desc_uz", "title_en", "order")


@admin.register(FunctionalBlock)
class FunctionalBlockAdmin(OrderedBlockAdmin):
    list_display = ("code", "title", "order")


@admin.register(MediaFeature)
class MediaFeatureAdmin(OrderedBlockAdmin):
    list_display = ("title_uz", "title_en", "order")


@admin.register(StakeholderValue)
class StakeholderValueAdmin(OrderedBlockAdmin):
    list_display = ("title_uz", "title_en", "order")


@admin.register(RoadmapStage)
class RoadmapStageAdmin(OrderedBlockAdmin):
    list_display = ("period_uz", "title_uz", "title_en", "order")


@admin.register(Kpi)
class KpiAdmin(OrderedBlockAdmin):
    list_display = ("value_uz", "label_uz", "label_en", "order")


@admin.register(Result)
class ResultAdmin(OrderedBlockAdmin):
    list_display = ("title_uz", "title_en", "order")
