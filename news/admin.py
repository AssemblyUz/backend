"""Admin for news articles."""

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from core.admin import LocalizedLabelsMixin

from .models import Article, ArticleImage
from .translation import fill_missing_translations


class ArticleImageFormSet(BaseInlineFormSet):
    """Enforces the photo cap in the admin; the API enforces it separately."""

    def clean(self):
        super().clean()
        kept = sum(
            1
            for form in self.forms
            if form.cleaned_data
            and not form.cleaned_data.get("DELETE")
            and form.cleaned_data.get("image")
        )
        if kept > ArticleImage.MAX_PER_ARTICLE:
            raise ValidationError(
                _("An article can have at most %(limit)d photos; this has %(count)d."),
                params={"limit": ArticleImage.MAX_PER_ARTICLE, "count": kept},
            )


class ArticleImageInline(admin.TabularInline):
    model = ArticleImage
    formset = ArticleImageFormSet
    extra = 1
    fields = ("preview", "image", "size", "order", "alt_uz", "alt_ru", "alt_en")
    readonly_fields = ("preview",)
    ordering = ("order", "pk")

    @admin.display(description=_("Preview"))
    def preview(self, obj: ArticleImage) -> str:
        if not obj.pk or not obj.image:
            return "—"
        return format_html(
            '<img src="{}" style="height:56px;width:auto;border-radius:6px;'
            'object-fit:cover;border:1px solid var(--border-color,#ddd)" alt="" />',
            obj.image.url,
        )


@admin.register(Article)
class ArticleAdmin(LocalizedLabelsMixin, admin.ModelAdmin):
    inlines = [ArticleImageInline]
    list_display = ("title_uz", "published_on", "is_published", "translation_gaps")
    list_filter = ("is_published", "published_on")
    search_fields = ("slug", "title_uz", "title_ru", "title_en")
    prepopulated_fields = {"slug": ("title_en",)}
    date_hierarchy = "published_on"
    readonly_fields = ("created_at", "updated_at")
    actions = ["publish", "unpublish"]

    fieldsets = (
        (_("Publishing"), {"fields": ("slug", "published_on", "icon", "is_published")}),
        (_("Tag"), {"fields": ("tag_uz", "tag_ru", "tag_en")}),
        (_("Title"), {"fields": ("title_uz", "title_ru", "title_en")}),
        (_("Excerpt"), {"fields": ("excerpt_uz", "excerpt_ru", "excerpt_en")}),
        (
            _("Body"),
            {
                "fields": ("body_uz", "body_ru", "body_en"),
                "description": _("Separate paragraphs with a blank line."),
            },
        ),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def save_model(self, request, obj, form, change):
        """
        Fill the empty locales after saving, as the editor panel does.

        Both admins write the same articles, so a piece of text that appears in
        three languages when saved from one and in one language when saved from
        the other would be a trap. Reported rather than silent: whoever saved it
        should know their Russian and English were written by a machine.
        """
        super().save_model(request, obj, form, change)
        filled = fill_missing_translations(obj)
        if filled:
            locales = sorted({name.rsplit("_", 1)[1] for name in filled})
            self.message_user(
                request,
                _("Machine-translated the empty fields into: %(locales)s. Please review.")
                % {"locales": ", ".join(locale.upper() for locale in locales)},
            )

    @admin.display(description=_("Missing translations"))
    def translation_gaps(self, obj: Article) -> str:
        missing = obj.missing_translations()
        return ", ".join(missing).upper() if missing else "—"

    def _set_published(self, request, queryset, *, published: bool, message):
        """
        Bulk publish/unpublish.

        Uses `.update()` for the flag but stamps `updated_at` alongside it —
        `.update()` bypasses `save()`, so `auto_now` never fires and the
        timestamp would otherwise still show the last manual edit.
        """
        updated = queryset.update(is_published=published, updated_at=timezone.now())
        self.message_user(request, message % {"count": updated})

    @admin.action(description=_("Publish selected articles"))
    def publish(self, request, queryset):
        self._set_published(
            request,
            queryset,
            published=True,
            message=_("%(count)d article(s) published."),
        )

    @admin.action(description=_("Unpublish selected articles"))
    def unpublish(self, request, queryset):
        self._set_published(
            request,
            queryset,
            published=False,
            message=_("%(count)d article(s) unpublished."),
        )
