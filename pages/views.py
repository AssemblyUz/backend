"""Read-only endpoints for home and about page content."""

from core.views import SingletonContentView

from .models import AboutContent, HomeContent
from .serializers import AboutContentSerializer, HomeContentSerializer


class HomeContentView(SingletonContentView):
    model = HomeContent
    serializer_class = HomeContentSerializer


class AboutContentView(SingletonContentView):
    model = AboutContent
    serializer_class = AboutContentSerializer
