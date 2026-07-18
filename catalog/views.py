"""Read-only endpoints for associations, services, projects and partners."""

from rest_framework import viewsets

from core.views import LocaleMixin

from .models import Association, PartnerGroup, Project, Service
from .serializers import (
    AssociationSerializer,
    PartnerGroupSerializer,
    ProjectSerializer,
    ServiceSerializer,
)


class AssociationViewSet(LocaleMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Association.objects.filter(is_published=True)
    serializer_class = AssociationSerializer
    lookup_field = "slug"
    pagination_class = None


class ServiceViewSet(LocaleMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Service.objects.filter(is_published=True)
    serializer_class = ServiceSerializer
    pagination_class = None


class ProjectViewSet(LocaleMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Project.objects.filter(is_published=True)
    serializer_class = ProjectSerializer
    pagination_class = None


class PartnerGroupViewSet(LocaleMixin, viewsets.ReadOnlyModelViewSet):
    # prefetch_related keeps this at two queries regardless of group count.
    queryset = PartnerGroup.objects.prefetch_related("partners")
    serializer_class = PartnerGroupSerializer
    pagination_class = None
