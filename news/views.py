"""Read-only endpoints for news articles."""

from rest_framework import viewsets

from core.views import LocaleMixin

from .models import Article
from .serializers import ArticleDetailSerializer, ArticleListSerializer


class ArticleViewSet(LocaleMixin, viewsets.ReadOnlyModelViewSet):
    """
    Published articles, newest first.

    Unpublished and future-dated posts are excluded by the manager, so a draft
    is never reachable by guessing its slug.
    """

    lookup_field = "slug"
    pagination_class = None

    def get_queryset(self):
        """
        Rebuilt per request on purpose.

        As a class attribute the queryset is evaluated once at import, freezing
        `timezone.localdate()` into the WHERE clause for the life of the worker.
        A post scheduled for tomorrow would then stay invisible until a redeploy.
        """
        return Article.published.all()

    def get_serializer_class(self):
        return ArticleListSerializer if self.action == "list" else ArticleDetailSerializer
