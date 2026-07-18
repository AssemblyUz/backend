"""The contact form endpoint — the only place the public API accepts writes."""

import logging

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response

from .models import Submission
from .serializers import SubmissionSerializer

logger = logging.getLogger(__name__)


def client_ip(request) -> str | None:
    """
    Best-effort client IP for abuse investigation.

    X-Forwarded-For is client-controlled unless a trusted proxy overwrites it,
    so this value is a hint, never an authorisation input.
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class ContactCreateView(CreateAPIView):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    throttle_scope = "contact"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Honeypot: humans never see this field, so a value means a bot. Answer
        # 201 so the bot cannot distinguish acceptance from rejection and retry.
        if serializer.validated_data.pop("website", ""):
            logger.warning("Contact honeypot tripped from %s", client_ip(request))
            return Response(
                {"detail": "Received."}, status=status.HTTP_201_CREATED
            )

        submission = serializer.save(
            ip_address=client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
        )

        self._notify(submission)

        return Response({"detail": "Received."}, status=status.HTTP_201_CREATED)

    def _notify(self, submission: Submission) -> None:
        """
        Email the team. The submission is already persisted, so a mail outage
        loses a notification, never the message itself — hence log-and-continue
        rather than failing the request the visitor sees.
        """
        recipients = settings.CONTACT_NOTIFY_EMAILS
        if not recipients:
            logger.info("CONTACT_NOTIFY_EMAILS is empty; skipping notification.")
            return

        try:
            send_mail(
                subject=f"Assembly — new message from {submission.name}",
                message=(
                    f"From: {submission.name} <{submission.email}>\n"
                    f"Locale: {submission.locale or 'unknown'}\n\n"
                    f"{submission.message}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=False,
            )
        except Exception:
            logger.exception(
                "Failed to email contact submission %s; it is saved in the admin.",
                submission.pk,
            )
