"""Admin for news articles."""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from core.admin import LocalizedLabelsMixin

from .models import Article


@admin.register(Article)
class ArticleAdmin(LocalizedLabelsMixin, admin.ModelAdmin):
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

    @admin.display(description=_("Missing translations"))
    def translation_gaps(self, obj: Article) -> str:
        missing = obj.missing_translations()
        return ", ".join(missing).upper() if missing else "—"

    @admin.action(description=_("Publish selected articles"))
    def publish(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"{updated} article(s) published.")

    @admin.action(description=_("Unpublish selected articles"))
    def unpublish(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"{updated} article(s) unpublished.")
