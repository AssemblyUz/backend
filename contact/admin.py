"""Admin for contact submissions — read-mostly: an inbox, not an editor."""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from core.admin import LocalizedLabelsMixin

from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(LocalizedLabelsMixin, admin.ModelAdmin):
    list_display = ("name", "email", "created_at", "locale", "is_handled")
    list_filter = ("is_handled", "locale", "created_at")
    search_fields = ("name", "email", "message")
    date_hierarchy = "created_at"
    actions = ["mark_handled"]

    # Submissions are visitor-authored evidence. Editing them would destroy the
    # record; only the triage flag is writable.
    readonly_fields = (
        "name", "email", "message", "locale", "ip_address", "user_agent", "created_at",
    )

    def has_add_permission(self, request):
        return False

    @admin.action(description=_("Mark selected as handled"))
    def mark_handled(self, request, queryset):
        updated = queryset.update(is_handled=True)
        self.message_user(request, f"{updated} submission(s) marked handled.")
