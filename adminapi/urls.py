"""
Routes for the editor control panel API.

Mounted under /api/admin/, deliberately separate from /api/v1/: the public API
is anonymous and cacheable, this one is authenticated and must never be cached.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PanelArticleViewSet, PanelPhotoViewSet, SessionView

router = DefaultRouter()
router.register("articles", PanelArticleViewSet, basename="panel-article")
router.register("photos", PanelPhotoViewSet, basename="panel-photo")

urlpatterns = [
    path("session/", SessionView.as_view(), name="panel-session"),
    path("", include(router.urls)),
]
