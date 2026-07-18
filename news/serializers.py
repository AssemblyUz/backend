"""Serializers for news articles."""

from core.models import resolve_locale
from core.serializers import TranslatedSerializer

from .models import Article


class ArticleListSerializer(TranslatedSerializer):
    """Card shape: everything needed for a listing, without the body."""

    translated_fields = ("tag", "title", "excerpt")
    plain_fields = ("slug", "icon")

    def to_representation(self, instance: Article) -> dict:
        data = super().to_representation(instance)
        data["date"] = instance.published_on.isoformat()
        return data


class ArticleDetailSerializer(ArticleListSerializer):
    """Card shape plus the body, split into paragraphs."""

    def to_representation(self, instance: Article) -> dict:
        data = super().to_representation(instance)
        data["body"] = instance.body_paragraphs(resolve_locale(self.locale))
        return data
