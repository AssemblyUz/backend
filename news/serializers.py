"""Serializers for news articles."""

from django.conf import settings

from core.models import resolve_locale, translated
from core.serializers import TranslatedSerializer

from .models import Article, ArticleImage


def image_url(image_field) -> str:
    """
    Absolute URL for an uploaded photo.

    Relative paths cannot be used here: the frontend fetches server-side from an
    internal address, so a browser resolving "/media/x.jpg" would aim it at the
    Next.js origin rather than at wherever media is actually served. MEDIA_BASE_URL
    is the public origin; falling back to the storage URL keeps local dev working.
    """
    base = settings.MEDIA_BASE_URL
    return f"{base.rstrip('/')}{image_field.url}" if base else image_field.url


def serialize_images(article: Article, locale: str) -> list[dict]:
    """Photos in editor order. The first one doubles as the article's cover."""
    return [
        {
            "url": image_url(img.image),
            "size": img.size,
            "alt": translated(img, "alt", locale),
        }
        for img in article.images.all()
        if img.image
    ]


class ArticleListSerializer(TranslatedSerializer):
    """Card shape: everything needed for a listing, without the body."""

    translated_fields = ("tag", "title", "excerpt")
    plain_fields = ("slug", "icon")

    def to_representation(self, instance: Article) -> dict:
        data = super().to_representation(instance)
        data["date"] = instance.published_on.isoformat()
        images = serialize_images(instance, resolve_locale(self.locale))
        # Cards only ever show the cover, so send that rather than the gallery.
        data["cover"] = images[0] if images else None
        return data


class ArticleDetailSerializer(ArticleListSerializer):
    """Card shape plus the body and the full photo gallery."""

    def to_representation(self, instance: Article) -> dict:
        data = super().to_representation(instance)
        locale = resolve_locale(self.locale)
        data["body"] = instance.body_paragraphs(locale)
        data["images"] = serialize_images(instance, locale)
        return data
