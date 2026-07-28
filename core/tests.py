"""Tests for locale resolution, translation fallback and singletons."""

import shutil
import tempfile
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import DEFAULT_LOCALE, SiteSettings, SocialLink, resolve_locale, translated


class ResolveLocaleTests(TestCase):
    def test_returns_supported_locale_unchanged(self):
        for locale in ("uz", "ru", "en"):
            self.assertEqual(resolve_locale(locale), locale)

    def test_falls_back_for_unknown_locale(self):
        self.assertEqual(resolve_locale("zz"), DEFAULT_LOCALE)

    def test_falls_back_for_none(self):
        self.assertEqual(resolve_locale(None), DEFAULT_LOCALE)

    def test_falls_back_for_injection_attempt(self):
        self.assertEqual(resolve_locale("../../etc/passwd"), DEFAULT_LOCALE)


class TranslatedTests(TestCase):
    def setUp(self):
        self.site = SiteSettings(name_uz="Assambleya", name_ru="Ассамблея", name_en="")

    def test_reads_requested_locale(self):
        self.assertEqual(translated(self.site, "name", "ru"), "Ассамблея")

    def test_blank_translation_falls_back_to_default_locale(self):
        # name_en is empty, so the Uzbek text is served rather than "".
        self.assertEqual(translated(self.site, "name", "en"), "Assambleya")

    def test_unknown_locale_falls_back_to_default_locale(self):
        self.assertEqual(translated(self.site, "name", "zz"), "Assambleya")


class SingletonTests(TestCase):
    def test_load_creates_exactly_one_row(self):
        SiteSettings.load()
        SiteSettings.load()
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_save_always_targets_pk_1(self):
        site = SiteSettings.load()
        self.assertEqual(site.pk, 1)

    def test_delete_is_refused(self):
        site = SiteSettings.load()
        with self.assertRaises(ValidationError):
            site.delete()
        self.assertEqual(SiteSettings.objects.count(), 1)


class SiteSettingsAPITests(TestCase):
    def setUp(self):
        site = SiteSettings.load()
        site.name_uz = "Assambleya"
        site.name_en = "Assembly"
        site.email = "info@assembly.uz"
        site.save()
        SocialLink.objects.create(platform="telegram", name="Telegram", url="https://t.me/x")

    def test_serves_requested_locale(self):
        response = self.client.get(reverse("v1:site-settings"), {"locale": "en"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Assembly")

    def test_never_leaks_per_locale_columns(self):
        response = self.client.get(reverse("v1:site-settings"), {"locale": "uz"})
        keys = response.json().keys()
        self.assertNotIn("name_uz", keys)
        self.assertNotIn("name_en", keys)

    def test_includes_social_links(self):
        response = self.client.get(reverse("v1:site-settings"))
        socials = response.json()["socials"]
        self.assertEqual(len(socials), 1)
        self.assertEqual(socials[0]["platform"], "telegram")


class HealthzTests(TestCase):
    """
    MEDIA_ROOT is redirected, or the writability probe creates the real media
    directory in the checkout every time the suite runs.
    """

    def setUp(self):
        self.media = tempfile.mkdtemp(prefix="assembly-healthz-")
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=self.media)
        override.enable()
        self.addCleanup(override.disable)

    def test_reports_ok_when_database_is_reachable(self):
        response = self.client.get(reverse("healthz"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "media": "ok"})

    def test_reports_media_as_unwritable_when_the_volume_cannot_be_written(self):
        """
        Uploads land on a mounted volume, which the database check cannot see.
        A volume the worker cannot write to breaks every photo upload while the
        rest of the site stays perfectly healthy, so it is reported separately.
        """
        with mock.patch(
            "core.views.NamedTemporaryFile",
            side_effect=PermissionError(13, "Permission denied"),
        ):
            response = self.client.get(reverse("healthz"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["media"], "unwritable")

    def test_stays_ok_overall_when_only_media_is_broken(self):
        """
        Deploys gate on this endpoint. Failing it for a broken volume would
        block the very deploy that carries the fix.
        """
        with mock.patch(
            "core.views.NamedTemporaryFile",
            side_effect=PermissionError(13, "Permission denied"),
        ):
            response = self.client.get(reverse("healthz"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
