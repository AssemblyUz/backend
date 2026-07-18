"""
Serialization primitives.

The API never exposes the per-locale columns. A caller asks for one locale and
receives flat strings, so the frontend does no locale bookkeeping of its own.
"""

from rest_framework import serializers

from .models import DEFAULT_LOCALE, SiteSettings, SocialLink, translated


class TranslatedSerializer(serializers.Serializer):
    """
    Base for any model with `<field>_uz` / `<field>_ru` / `<field>_en` columns.

    Subclasses declare the *base* field names; `to_representation` resolves each
    to the locale in serializer context (set by the view from `?locale=`).

        class ValueSerializer(TranslatedSerializer):
            translated_fields = ("title", "sub")

        -> {"title": "Birlashuv", "sub": "kuch"}
    """

    #: Base names of translated columns, emitted as flat keys.
    translated_fields: tuple[str, ...] = ()

    #: Non-translated columns copied through as-is.
    plain_fields: tuple[str, ...] = ()

    @property
    def locale(self) -> str:
        return self.context.get("locale", DEFAULT_LOCALE)

    def to_representation(self, instance) -> dict:
        data = {
            name: translated(instance, name, self.locale)
            for name in self.translated_fields
        }
        for name in self.plain_fields:
            data[name] = getattr(instance, name)
        return data


class SocialLinkSerializer(TranslatedSerializer):
    plain_fields = ("platform", "name", "url")


class SiteSettingsSerializer(TranslatedSerializer):
    translated_fields = ("name", "short", "tagline", "description", "address")
    plain_fields = ("email", "phone")

    def to_representation(self, instance: SiteSettings) -> dict:
        data = super().to_representation(instance)
        socials = SocialLink.objects.all()
        data["socials"] = SocialLinkSerializer(
            socials, many=True, context=self.context
        ).data
        return data
