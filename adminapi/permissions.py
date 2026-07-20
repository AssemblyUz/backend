"""Access control for the editor control panel API."""

from rest_framework.permissions import BasePermission

# Model permissions the panel needs, by HTTP method. Mirrors DRF's
# DjangoModelPermissions but is spelled out so the mapping is auditable.
REQUIRED = {
    "GET": [],
    "HEAD": [],
    "OPTIONS": [],
    "POST": ["news.add_article"],
    "PUT": ["news.change_article"],
    "PATCH": ["news.change_article"],
    "DELETE": ["news.delete_article"],
}


class IsEditor(BasePermission):
    """
    Signed in, marked as staff, and holding the right model permission.

    `is_staff` alone is not enough: it only means "may open Django admin". The
    per-model check is what makes the Editor group meaningful here — otherwise
    the panel would be a way around the permissions that group deliberately
    withholds, and any staff account could publish.
    """

    message = "You do not have permission to edit content."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated and user.is_staff and user.is_active):
            return False
        return all(user.has_perm(perm) for perm in REQUIRED.get(request.method, []))


class CanUploadPhotos(BasePermission):
    """Photos live on their own model, so they carry their own permissions."""

    message = "You do not have permission to manage photos."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated and user.is_staff and user.is_active):
            return False
        if request.method == "DELETE":
            return user.has_perm("news.delete_articleimage")
        if request.method in ("POST", "PUT", "PATCH"):
            return user.has_perm("news.add_articleimage")
        return user.has_perm("news.view_articleimage")
