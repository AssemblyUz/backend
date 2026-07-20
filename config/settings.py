"""
Django settings for the Assembly backend.

Everything environment-specific is read from the environment (see .env.example).
Nothing in this file may contain a credential — `SECRET_KEY` has no default, so
the process refuses to start rather than fall back to a well-known value.
"""

from pathlib import Path

import environ
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
    CONTACT_NOTIFY_EMAILS=(list, []),
)

# Read backend/.env when present. Real environment variables always win.
env_file = BASE_DIR / ".env"
if env_file.exists():
    env.read_env(env_file)

SECRET_KEY = env("SECRET_KEY")

DEBUG = env("DEBUG")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# The control panel path. Move it off /admin/ in production to cut drive-by
# credential stuffing. Must end with a slash.
ADMIN_URL = env("ADMIN_URL", default="admin/")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "core",
    "pages",
    "catalog",
    "news",
    "contact",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # Must sit after SessionMiddleware (it reads the language from the session)
    # and before CommonMiddleware.
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if not DEBUG:
    MIDDLEWARE.insert(2, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# SQLite locally, Postgres in production — both selected via DATABASE_URL.
DATABASES = {
    "default": env.db_url(
        "DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    ),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalisation --------------------------------------------------
# The control panel is used by Uzbek-speaking editors, so Uzbek is the default.
# LocaleMiddleware resolves the active language per request from the session
# cookie (set by the header switcher), then Accept-Language, then this default.

LANGUAGE_CODE = env("LANGUAGE_CODE", default="uz")

LANGUAGES = [
    ("uz", _("O'zbekcha")),
    ("ru", _("Русский")),
    ("en", _("English")),
]

# Project catalogues take precedence over the ones shipped by Django and its
# apps. That is what lets locale/uz fill the gaps in Django's own partial
# Uzbek admin translation.
LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = env("TIME_ZONE", default="Asia/Tashkent")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# backend/static holds the admin theme that matches the public website.
STATICFILES_DIRS = [BASE_DIR / "static"]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

if not DEBUG:
    STORAGES["staticfiles"] = {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    }

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Whether Django itself serves uploaded files in production. Left on so a
# proxy that is not yet routing /media/ does not silently 404 every photo;
# turn it off once the proxy is confirmed, so uploads never touch the worker.
SERVE_MEDIA = env.bool("SERVE_MEDIA", default=True)

# Public origin for uploaded photos, e.g. https://assembly.uz. The API returns
# absolute media URLs because the frontend fetches server-side over an internal
# address that a browser cannot resolve. Blank keeps the relative path, which
# is what local development wants.
MEDIA_BASE_URL = env("MEDIA_BASE_URL", default="")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Django REST Framework -------------------------------------------------

REST_FRAMEWORK = {
    # Public content is read-only for anonymous callers. The single write
    # endpoint (contact) is throttled by scope.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        # Generous for a human, useless for a spam script.
        "contact": env("CONTACT_THROTTLE_RATE", default="5/hour"),
    },
}

if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ]

# --- CORS ------------------------------------------------------------------
# The Next.js app is the only browser client. Never enable CORS_ALLOW_ALL_ORIGINS.

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = False

CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

# --- Email -----------------------------------------------------------------

EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@assembly.uz")

# Recipients notified when a contact submission arrives.
CONTACT_NOTIFY_EMAILS = env("CONTACT_NOTIFY_EMAILS")

# --- Security --------------------------------------------------------------
# Transport hardening is skipped under DEBUG so local http:// dev works.

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
