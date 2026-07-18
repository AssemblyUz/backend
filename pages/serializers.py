"""Serializers for home and about page content."""

from core.serializers import TranslatedSerializer

from .models import (
    AboutContent,
    ArchitectureNode,
    Direction,
    FunctionalBlock,
    Highlight,
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


class StatSerializer(TranslatedSerializer):
    translated_fields = ("label",)
    plain_fields = ("value",)


class HighlightSerializer(TranslatedSerializer):
    translated_fields = ("label",)
    plain_fields = ("value",)


class ValueSerializer(TranslatedSerializer):
    translated_fields = ("title", "sub")


class ArchitectureNodeSerializer(TranslatedSerializer):
    translated_fields = ("title", "desc")


class MechanismStepSerializer(TranslatedSerializer):
    translated_fields = ("title", "desc")


class FunctionalBlockSerializer(TranslatedSerializer):
    translated_fields = ("desc",)
    plain_fields = ("code", "title")


class MediaFeatureSerializer(TranslatedSerializer):
    translated_fields = ("title", "desc")


class StakeholderValueSerializer(TranslatedSerializer):
    translated_fields = ("title", "desc")


class RoadmapStageSerializer(TranslatedSerializer):
    translated_fields = ("period", "title", "desc")


class KpiSerializer(TranslatedSerializer):
    translated_fields = ("value", "label")


class ResultSerializer(TranslatedSerializer):
    translated_fields = ("title", "desc")


class HomeContentSerializer(TranslatedSerializer):
    translated_fields = (
        "hero_badge",
        "hero_title",
        "hero_lead",
        "cta_primary",
        "cta_secondary",
        "about_title",
        "about_lead",
        "assoc_title",
        "assoc_lead",
        "services_title",
        "services_lead",
        "projects_title",
        "projects_lead",
        "news_title",
        "news_lead",
        "cta_banner_title",
        "cta_banner_lead",
        "cta_banner_btn",
    )

    def to_representation(self, instance) -> dict:
        data = super().to_representation(instance)
        data["stats"] = StatSerializer(
            Stat.objects.all(), many=True, context=self.context
        ).data
        return data


class AboutContentSerializer(TranslatedSerializer):
    translated_fields = (
        "title",
        "lead",
        "intro_title",
        "intro",
        "principle",
        "intro_note",
        "role_title",
        "mission_section_title",
        "mission_section_lead",
        "mission_title",
        "mission",
        "goal_title",
        "goal",
        "goal_note",
        "values_title",
        "values_lead",
        "directions_title",
        "directions_lead",
        "architecture_title",
        "architecture_lead",
        "core_title",
        "core_sub",
        "architecture_note",
        "mechanism_title",
        "mechanism_lead",
        "formula_title",
        "formula",
        "blocks_title",
        "blocks_lead",
        "media_title",
        "media_lead",
        "media_tagline",
        "media_summary",
        "partners_title",
        "partners_lead",
        "value_title",
        "value_lead",
        "roadmap_title",
        "roadmap_lead",
        "kpi_title",
        "results_title",
        "motto",
        "slogan",
    )

    def to_representation(self, instance: AboutContent) -> dict:
        data = super().to_representation(instance)
        ctx = self.context

        data["highlights"] = HighlightSerializer(
            Highlight.objects.all(), many=True, context=ctx
        ).data
        data["role"] = [
            item["text"]
            for item in _RoleSerializer(
                StrategicRole.objects.all(), many=True, context=ctx
            ).data
        ]
        data["values"] = ValueSerializer(
            Value.objects.all(), many=True, context=ctx
        ).data
        data["directions"] = [
            item["name"]
            for item in _DirectionSerializer(
                Direction.objects.all(), many=True, context=ctx
            ).data
        ]
        data["architecture"] = ArchitectureNodeSerializer(
            ArchitectureNode.objects.all(), many=True, context=ctx
        ).data
        data["mechanism"] = MechanismStepSerializer(
            MechanismStep.objects.all(), many=True, context=ctx
        ).data
        data["blocks"] = FunctionalBlockSerializer(
            FunctionalBlock.objects.all(), many=True, context=ctx
        ).data
        data["media"] = MediaFeatureSerializer(
            MediaFeature.objects.all(), many=True, context=ctx
        ).data
        data["value_items"] = StakeholderValueSerializer(
            StakeholderValue.objects.all(), many=True, context=ctx
        ).data
        data["roadmap"] = RoadmapStageSerializer(
            RoadmapStage.objects.all(), many=True, context=ctx
        ).data
        data["kpi"] = KpiSerializer(Kpi.objects.all(), many=True, context=ctx).data
        data["results"] = ResultSerializer(
            Result.objects.all(), many=True, context=ctx
        ).data
        return data


class _RoleSerializer(TranslatedSerializer):
    """Internal: `role` is a flat list of strings in the API."""

    translated_fields = ("text",)


class _DirectionSerializer(TranslatedSerializer):
    """Internal: `directions` is a flat list of strings in the API."""

    translated_fields = ("name",)
