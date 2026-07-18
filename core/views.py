"""Shared view behaviour: locale resolution and cache headers."""

from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SiteSettings, resolve_locale
from .serializers import SiteSettingsSerializer


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
