"""Admin for associations, services, projects and partners."""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from core.admin import LocalizedLabelsMixin

from .models import Association, Partner, PartnerGroup, Project, Service


@admin.register(Association)
class AssociationAdmin(LocalizedLabelsMixin, admin.ModelAdmin):
    list_display = ("name_uz", "name_en", "chairman", "is_published", "order")
    list_editable = ("is_published", "order")
    list_filter = ("is_published",)
    search_fields = ("name_uz", "name_ru", "name_en", "chairman")
    prepopulated_fields = {"slug": ("name_en",)}
    ordering = ("order", "pk")
    fieldsets = (
        (_("Identity"), {"fields": ("slug", "name_uz", "name_ru", "name_en")}),
        (_("Field of activity"), {"fields": ("activity_uz", "activity_ru", "activity_en")}),
        (_("Contact"), {"fields": ("chairman", "phone")}),
        (_("Publishing"), {"fields": ("is_published", "order")}),
    )


@admin.register(Service)
class ServiceAdmin(LocalizedLabelsMixin, admin.ModelAdmin):
    list_display = ("icon", "name_uz", "name_en", "is_published", "order")
    list_editable = ("is_published", "order")
    list_filter = ("is_published",)
    search_fields = ("name_uz", "name_ru", "name_en")
    ordering = ("order", "pk")


@admin.register(Project)
class ProjectAdmin(LocalizedLabelsMixin, admin.ModelAdmin):
    list_display = ("icon", "name", "has_site", "is_published", "order")
    list_editable = ("is_published", "order")
    list_filter = ("is_published",)
    search_fields = ("name",)
    ordering = ("order", "pk")

    @admin.display(boolean=True, description=_("Site live"))
    def has_site(self, obj: Project) -> bool:
        return bool(obj.url)


class PartnerInline(admin.TabularInline):
    model = Partner
    extra = 1
    fields = ("name", "name_uz", "name_ru", "name_en", "url", "order")


@admin.register(PartnerGroup)
class PartnerGroupAdmin(LocalizedLabelsMixin, admin.ModelAdmin):
    list_display = ("title_uz", "title_en", "partner_count", "order")
    list_editable = ("order",)
    ordering = ("order", "pk")
    inlines = [PartnerInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("partners")

    @admin.display(description=_("Partners"))
    def partner_count(self, obj: PartnerGroup) -> int:
        return obj.partners.count()
