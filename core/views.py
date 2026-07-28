"""Shared view behaviour: locale resolution and cache headers."""

import errno
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SiteSettings, resolve_locale
from .serializers import SiteSettingsSerializer


def media_status() -> str:
    """
    Whether uploaded photos can actually be written.

    MEDIA_ROOT is a mounted volume, so it can be broken independently of
    everything else here: a bind mount owned by the wrong user leaves the site
    entirely healthy while every photo upload fails. Nothing else notices —
    the database check cannot see the filesystem, and the container's own
    healthcheck only runs `migrate --check`.

    The write is real, because the failure being looked for is a permission
    one: `os.access` answers from the mode bits and is wrong for exactly the
    cases that matter.
    """
    try:
        Path(settings.MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=settings.MEDIA_ROOT, prefix=".healthz-"):
            pass
    except OSError as exc:
        if exc.errno in (errno.EACCES, errno.EPERM):
            return "unwritable"
        if exc.errno in (errno.ENOSPC, errno.EDQUOT):
            return "full"
        return "error"
    return "ok"


@require_GET
def healthz(request):
    """Readiness check used by Docker, Caddy, and GitHub Actions deploys."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unhealthy"}, status=503)

    # Reported, deliberately not fatal: deploys gate on this endpoint, and
    # failing it over a broken volume would block the deploy carrying the fix.
    return JsonResponse({"status": "ok", "media": media_status()})


class LocaleMixin:
    """
    Reads `?locale=` once, validates it, and hands it to serializers via context.

    An unknown or missing locale falls back to the default rather than 400 — a
    bad query string should never take a public page down.
    """

    def get_locale(self) -> str:
        return resolve_locale(self.request.query_params.get("locale"))

    def get_serializer_context(self) -> dict:
        context = super().get_serializer_context()
        context["locale"] = self.get_locale()
        return context


class SingletonContentView(LocaleMixin, APIView):
    """Serves a one-row content model. Subclasses set `model` and `serializer_class`."""

    model = None
    serializer_class = None

    def get(self, request):
        instance = self.model.load()
        serializer = self.serializer_class(instance, context={"locale": self.get_locale()})
        return Response(serializer.data)


class SiteSettingsView(SingletonContentView):
    model = SiteSettings
    serializer_class = SiteSettingsSerializer
