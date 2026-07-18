"""Serializers for associations, services, projects and partners."""

from core.serializers import TranslatedSerializer

from .models import Partner


class AssociationSerializer(TranslatedSerializer):
    translated_fields = ("name", "activity")
    plain_fields = ("slug", "chairman", "phone")


class ServiceSerializer(TranslatedSerializer):
    translated_fields = ("name", "desc")
    plain_fields = ("icon",)


class ProjectSerializer(TranslatedSerializer):
    translated_fields = ("desc",)
    plain_fields = ("icon", "name", "url")


class PartnerGroupSerializer(TranslatedSerializer):
    translated_fields = ("title",)

    def to_representation(self, instance) -> dict:
        data = super().to_representation(instance)
        locale = self.locale
        data["items"] = [
            {"name": partner.display_name(locale), "url": partner.url}
            for partner in instance.partners.all()
        ]
        return data


class PartnerSerializer(TranslatedSerializer):
    plain_fields = ("name", "url")

    def to_representation(self, instance: Partner) -> dict:
        return {"name": instance.display_name(self.locale), "url": instance.url}
