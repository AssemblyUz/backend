"""
Serializers for the editor control panel.

These differ from the public ones in `news.serializers`: the panel edits raw
per-locale columns, so nothing is flattened by `?locale=`. An editor sees and
sets `title_uz`, `title_ru` and `title_en` individually.
"""

from rest_framework import serializers

from core.models import LOCALES
from news.models import Article, ArticleImage

TRANSLATED = ("tag", "title", "excerpt", "body")


class PanelImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ArticleImage
        fields = ("id", "url", "size", "order", "alt_uz", "alt_ru", "alt_en")
        read_only_fields = ("id", "url")

    def get_url(self, obj: ArticleImage) -> str:
        from news.serializers import image_url

        return image_url(obj.image) if obj.image else ""


class PanelArticleSerializer(serializers.ModelSerializer):
    images = PanelImageSerializer(many=True, read_only=True)
    missing_translations = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            "id", "slug", "published_on", "icon", "is_published",
            *[f"{f}_{loc}" for f in TRANSLATED for loc in LOCALES],
            "images", "missing_translations", "created_at", "updated_at",
        )
        read_only_fields = ("id", "images", "missing_translations", "created_at", "updated_at")

    def get_missing_translations(self, obj: Article) -> list[str]:
        return obj.missing_translations()

    # Slug uniqueness is left to the UniqueValidator that DRF derives from the
    # column's unique=True. Its message is already translated into Uzbek and
    # Russian; a hand-written one here would only ever be English.

    def validate(self, attrs: dict) -> dict:
        """A published article must at least be readable in the default locale."""
        is_published = attrs.get(
            "is_published", getattr(self.instance, "is_published", False)
        )
        title_uz = attrs.get("title_uz", getattr(self.instance, "title_uz", ""))
        if is_published and not title_uz.strip():
            raise serializers.ValidationError(
                {"title_uz": "An Uzbek title is required before publishing."}
            )
        return attrs


class PanelArticleListSerializer(serializers.ModelSerializer):
    """Row shape for the dashboard table — no bodies, one thumbnail."""

    cover = serializers.SerializerMethodField()
    photo_count = serializers.IntegerField(source="images.count", read_only=True)
    missing_translations = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            "id", "slug", "title_uz", "title_ru", "title_en",
            "published_on", "is_published", "cover", "photo_count",
            "missing_translations", "updated_at",
        )

    def get_cover(self, obj: Article) -> str | None:
        from news.serializers import image_url

        first = obj.images.first()
        return image_url(first.image) if first and first.image else None

    def get_missing_translations(self, obj: Article) -> list[str]:
        return obj.missing_translations()
