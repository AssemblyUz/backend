"""
Upload rules for article photos.

Enforced on the model rather than in a form, so they hold no matter which admin
is doing the writing — Django admin today, the custom panel later, or a shell.
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

MAX_UPLOAD_BYTES = 5 * 1024 * 1024

# Extensions Pillow can open and browsers can render. Checked alongside the
# real decoded format, because an extension is trivially renamed.
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "AVIF", "GIF"}


def validate_image_upload(f) -> None:
    """
    Reject oversized files and anything that is not really an image.

    The format check decodes the file rather than trusting the extension or the
    client's content type, both of which are trivially forged. It is done here
    and not left to the form layer: `forms.ImageField` verifies content, but
    `models.ImageField` does not, so a write that never passes through a form --
    the API, a management command, a shell -- would otherwise store arbitrary
    bytes under an image filename.
    """
    if f.size > MAX_UPLOAD_BYTES:
        raise ValidationError(
            _("Image is %(actual).1f MB. The limit is %(limit)d MB."),
            params={"actual": f.size / 1024 / 1024, "limit": MAX_UPLOAD_BYTES // 1024 // 1024},
        )

    from PIL import Image, UnidentifiedImageError

    position = f.tell() if hasattr(f, "tell") else None
    try:
        f.seek(0)
        with Image.open(f) as img:
            # verify() reads the whole file and catches truncated or malformed
            # data that Image.open() alone accepts lazily.
            img.verify()
            fmt = (img.format or "").upper()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError(_("This file is not a readable image.")) from exc
    finally:
        # Leave the handle where it was found; the storage backend reads it next.
        if position is not None:
            f.seek(position)

    if fmt not in ALLOWED_FORMATS:
        raise ValidationError(
            _("%(format)s images are not supported. Use JPEG, PNG, WebP or AVIF."),
            params={"format": fmt or "Unknown"},
        )
