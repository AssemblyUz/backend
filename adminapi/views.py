"""
API behind the editor control panel at /admin.

Session-based, not token-based. Caddy serves the site and the API from the same
origin (`assembly.uz/api/*` -> Django, `assembly.uz/*` -> Next.js), so Django's
own session cookie is first-party for the panel: no token to store in the
browser, no CORS, no refresh rotation, and logging out is a real server-side
invalidation rather than dropping a token client-side.

CSRF is enforced by DRF's SessionAuthentication on every unsafe method.
"""

from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.middleware.csrf import get_token
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from news.models import Article, ArticleImage

from .permissions import CanUploadPhotos, IsEditor
from .serializers import (
    PanelArticleListSerializer,
    PanelArticleSerializer,
    PanelImageSerializer,
)


def describe(user) -> dict:
    """What the panel needs to know about who is signed in."""
    return {
        "username": user.get_username(),
        "name": user.get_full_name() or user.get_username(),
        "email": user.email,
        "isSuperuser": user.is_superuser,
        "canPublish": user.has_perm("news.change_article"),
        "canDelete": user.has_perm("news.delete_article"),
        "canUploadPhotos": user.has_perm("news.add_articleimage"),
    }


class SessionView(APIView):
    """
    GET  — who is signed in, and a CSRF token for subsequent writes.
    POST — sign in.
    DELETE — sign out.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "admin_login"

    def get_throttles(self):
        # Only the sign-in attempt is rate limited; polling the session is not.
        return super().get_throttles() if self.request.method == "POST" else []

    def get(self, request):
        # Setting the CSRF cookie here is what lets the panel issue its first
        # write without a separate bootstrap request.
        csrf = get_token(request)
        if not (request.user.is_authenticated and request.user.is_staff):
            return Response({"user": None, "csrfToken": csrf})
        return Response({"user": describe(request.user), "csrfToken": csrf})

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        if not username or not password:
            return Response(
                {"detail": "Enter your username and password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=username, password=password)

        # One message for every failure. Distinguishing "no such user" from
        # "wrong password" would let an attacker enumerate accounts, and
        # naming the staff requirement would confirm a valid login.
        if user is None or not user.is_staff or not user.is_active:
            return Response(
                {"detail": "Incorrect username or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request, user)
        return Response({"user": describe(user), "csrfToken": get_token(request)})

    def delete(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PanelArticleViewSet(viewsets.ModelViewSet):
    """Full CRUD over articles for signed-in editors."""

    permission_classes = [IsEditor]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    lookup_field = "slug"

    def get_queryset(self):
        # Every article, drafts included — this is the editing surface, not the
        # public one. Prefetched because the list renders a thumbnail per row.
        return Article.objects.prefetch_related("images").order_by(
            "-published_on", "-pk"
        )

    def get_serializer_class(self):
        return (
            PanelArticleListSerializer
            if self.action == "list"
            else PanelArticleSerializer
        )

    @action(detail=True, methods=["post"], permission_classes=[CanUploadPhotos])
    def photos(self, request, slug=None):
        """
        Attach photos to an article.

        The 10 cap is counted against what is already stored plus what is being
        added, so it cannot be bypassed by uploading in several batches — the
        form's own client-side check only covers a single submission.
        """
        article = self.get_object()
        files = request.FILES.getlist("images")
        if not files:
            return Response(
                {"detail": "No photos were attached."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing = article.images.count()
        room = ArticleImage.MAX_PER_ARTICLE - existing
        if len(files) > room:
            return Response(
                {
                    "detail": (
                        f"This article already has {existing} of "
                        f"{ArticleImage.MAX_PER_ARTICLE} photos. "
                        f"You can add {max(room, 0)} more."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        sizes = request.POST.getlist("sizes")
        created = []
        try:
            with transaction.atomic():
                for offset, upload in enumerate(files):
                    photo = ArticleImage(
                        article=article,
                        image=upload,
                        size=(
                            sizes[offset]
                            if offset < len(sizes)
                            else ArticleImage.Size.FULL
                        ),
                        order=existing + offset,
                    )
                    # Runs the upload validators. Without this the file is
                    # stored first and rejected never — ModelViewSet does not
                    # call full_clean() on its own.
                    photo.full_clean()
                    photo.save()
                    created.append(photo)
        except Exception as exc:  # noqa: BLE001 — surfaced to the editor verbatim
            from django.core.exceptions import ValidationError

            if isinstance(exc, ValidationError):
                return Response(
                    {"detail": "; ".join(exc.messages)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            raise

        return Response(
            PanelImageSerializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class PanelPhotoViewSet(viewsets.ModelViewSet):
    """Reorder, re-size, caption or remove an individual photo."""

    permission_classes = [CanUploadPhotos]
    serializer_class = PanelImageSerializer
    queryset = ArticleImage.objects.all()
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def perform_destroy(self, instance: ArticleImage):
        # Drop the file too, or deleted photos accumulate on the volume forever.
        stored = instance.image
        super().perform_destroy(instance)
        stored.delete(save=False)
