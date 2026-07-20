"""
URL configuration.

Public API lives under /api/v1/. The editor control panel is Django admin at
the path given by ADMIN_URL (defaults to admin/) so it can be moved off the
well-known location in production.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.utils.translation import gettext_lazy as _
from django.views.static import serve
from rest_framework.routers import DefaultRouter

from catalog.views import (
    AssociationViewSet,
    PartnerGroupViewSet,
    ProjectViewSet,
    ServiceViewSet,
)
from contact.views import ContactCreateView
from core.views import SiteSettingsView, healthz
from news.views import ArticleViewSet
from pages.views import AboutContentView, HomeContentView

admin.site.site_header = _("Assembly control panel")
admin.site.site_title = _("Assembly")
admin.site.index_title = _("Website content")

router = DefaultRouter()
router.register("associations", AssociationViewSet, basename="association")
router.register("services", ServiceViewSet, basename="service")
router.register("projects", ProjectViewSet, basename="project")
router.register("partners", PartnerGroupViewSet, basename="partner")
router.register("news", ArticleViewSet, basename="article")

api_v1 = [
    path("site/", SiteSettingsView.as_view(), name="site-settings"),
    path("home/", HomeContentView.as_view(), name="home-content"),
    path("about/", AboutContentView.as_view(), name="about-content"),
    path("contact/", ContactCreateView.as_view(), name="contact-create"),
    path("", include(router.urls)),
]

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path(settings.ADMIN_URL, admin.site.urls),
    # Backs the language switcher in the admin header (django.views.i18n.set_language).
    path("i18n/", include("django.conf.urls.i18n")),
    path("api/v1/", include((api_v1, "api"), namespace="v1")),
    # Authenticated editor panel. Separate from /api/v1/ so the public API
    # stays anonymous and cacheable.
    path("api/admin/", include(("adminapi.urls", "adminapi"), namespace="panel")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.SERVE_MEDIA:
    # Fallback only. In production the reverse proxy should serve /media/
    # straight off the shared volume, which is faster and keeps uploads out of
    # the worker pool -- gunicorn runs a single worker (see Dockerfile), so a
    # few large images streamed through Django would stall the whole API.
    #
    # This exists because a misconfigured proxy otherwise fails silently: every
    # uploaded photo 404s while the site itself keeps returning 200. Set
    # SERVE_MEDIA=False once the proxy is confirmed to handle it.
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        )
    ]
