"""News articles published from the admin, replacing the static src/data/news.ts."""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import LOCALES

from .validators import validate_image_upload


class PublishedArticleManager(models.Manager):
    """Only articles an editor has published, and not dated in the future."""

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(is_published=True, published_on__lte=timezone.localdate())
        )


class Article(models.Model):
    """
    A news post.

    Bodies are stored as plain text with paragraphs separated by a blank line —
    the same way an editor naturally types. `body_paragraphs()` splits them for
    the API, so the frontend keeps receiving `body: string[]`.
    """

    slug = models.SlugField(
        max_length=200,
        unique=True,
        help_text="URL segment. Changing it after publishing breaks existing links.",
    )
    published_on = models.DateField(
        default=timezone.localdate,
        help_text="Drives ordering. A future date keeps the post hidden.",
    )
    icon = models.CharField(max_length=8, default="📰", help_text="A single emoji.")

    tag_uz = models.CharField(max_length=60, blank=True, default="")
    tag_ru = models.CharField(max_length=60, blank=True, default="")
    tag_en = models.CharField(max_length=60, blank=True, default="")

    title_uz = models.CharField(max_length=250, blank=True, default="")
    title_ru = models.CharField(max_length=250, blank=True, default="")
    title_en = models.CharField(max_length=250, blank=True, default="")

    excerpt_uz = models.TextField(blank=True, default="")
    excerpt_ru = models.TextField(blank=True, default="")
    excerpt_en = models.TextField(blank=True, default="")

    body_uz = models.TextField(blank=True, default="", help_text="Blank line = new paragraph.")
    body_ru = models.TextField(blank=True, default="", help_text="Blank line = new paragraph.")
    body_en = models.TextField(blank=True, default="", help_text="Blank line = new paragraph.")

    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    published = PublishedArticleManager()

    class Meta:
        verbose_name = _("Article")
        verbose_name_plural = _("Articles")
        ordering = ["-published_on", "-pk"]
        indexes = [models.Index(fields=["-published_on"])]

    def body_paragraphs(self, locale: str) -> list[str]:
        """Split the body for `locale` into paragraphs, dropping empty ones."""
        raw = getattr(self, f"body_{locale}", "") or self.body_uz
        return [p.strip() for p in raw.split("\n\n") if p.strip()]

    def missing_translations(self) -> list[str]:
        """Locales with no title — surfaced in the admin so gaps are visible."""
        return [loc for loc in LOCALES if not getattr(self, f"title_{loc}")]

    def __str__(self) -> str:
        return self.title_uz or self.title_en or self.slug


class ArticleImage(models.Model):
    """
    A photo attached to an article.

    The first image doubles as the article's cover — there is no separate cover
    field, so an editor reorders rather than re-uploading. `size` is the layout
    the editor picked, not a stored resolution: the file is kept at its original
    dimensions and the frontend renders it at the chosen width.
    """

    MAX_PER_ARTICLE = 10

    class Size(models.TextChoices):
        FULL = "full", _("Full width")
        HALF = "half", _("Half width")
        THUMB = "thumb", _("Thumbnail")

    article = models.ForeignKey(Article, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(
        upload_to="news/%Y/%m/",
        validators=[validate_image_upload],
        help_text="JPEG, PNG, WebP or AVIF, up to 5 MB.",
    )
    size = models.CharField(
        max_length=8,
        choices=Size.choices,
        default=Size.FULL,
        help_text="How wide this photo renders in the article.",
    )
    alt_uz = models.CharField(max_length=200, blank=True, default="")
    alt_ru = models.CharField(max_length=200, blank=True, default="")
    alt_en = models.CharField(max_length=200, blank=True, default="")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _("Photo")
        verbose_name_plural = _("Photos")
        ordering = ["order", "pk"]

    def __str__(self) -> str:
        return f"{self.article.slug} #{self.order}"
