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

    queryset = Article.published.all()
    lookup_field = "slug"
    pagination_class = None

    def get_serializer_class(self):
        return ArticleListSerializer if self.action == "list" else ArticleDetailSerializer
