"""Contact form submissions, replacing the frontend's mailto: hand-off."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Submission(models.Model):
    """
    A message sent through the contact form.

    Stored so nothing is lost if email delivery fails, and emailed to
    CONTACT_NOTIFY_EMAILS on arrival. Never rendered back into a page as HTML.
    """

    name = models.CharField(max_length=150)
    email = models.EmailField()
    message = models.TextField()

    locale = models.CharField(max_length=2, blank=True, default="")
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, help_text="Recorded for abuse investigation only."
    )
    user_agent = models.CharField(max_length=300, blank=True, default="")

    is_handled = models.BooleanField(
        default=False, help_text="Tick once someone has replied."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Submission")
        verbose_name_plural = _("Submissions")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["-created_at"])]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"
