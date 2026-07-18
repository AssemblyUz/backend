"""
Smoke tests for the admin control panel.

`manage.py check` catches admin misconfiguration (admin.E###), but not a
changelist that raises at render time. These walk every registered model.
"""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Association, PartnerGroup, Project, Service
from contact.models import Submission
from core.models import SiteSettings
from news.models import Article
from pages.models import AboutContent, HomeContent

EXPECTED_MODELS = {
    SiteSettings, HomeContent, AboutContent,
    Association, Service, Project, PartnerGroup,
    Article, Submission,
}


class AdminSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username="editor", email="editor@assembly.uz", password="not-a-real-password"
        )

    def setUp(self):
        self.client.force_login(self.admin_user)

    def test_expected_models_are_registered(self):
        registered = set(admin.site._registry)
        missing = EXPECTED_MODELS - registered
        self.assertFalse(missing, f"Not registered in admin: {missing}")

    def test_index_renders(self):
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)

    def test_every_changelist_renders(self):
        for model in admin.site._registry:
            meta = model._meta
            url = reverse(f"admin:{meta.app_label}_{meta.model_name}_changelist")
            with self.subTest(model=meta.label):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_singleton_changelists_render_after_autocreate(self):
        # SingletonAdmin.changelist_view calls load(); make sure that does not
        # explode on a database with no rows yet.
        for model in (SiteSettings, HomeContent, AboutContent):
            model.objects.all().delete()
            meta = model._meta
            url = reverse(f"admin:{meta.app_label}_{meta.model_name}_changelist")
            with self.subTest(model=meta.label):
                self.assertEqual(self.client.get(url).status_code, 200)
                self.assertEqual(model.objects.count(), 1)

    def test_submissions_cannot_be_added_by_hand(self):
        url = reverse("admin:contact_submission_add")
        # has_add_permission is False, so Django answers 403.
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_singletons_cannot_be_deleted(self):
        SiteSettings.load()
        url = reverse("admin:core_sitesettings_delete", args=[1])
        self.assertEqual(self.client.get(url).status_code, 403)


class AdminThemeTests(TestCase):
    """The control panel must keep the website's branding and palette."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username="themer", email="t@assembly.uz", password="not-a-real-password"
        )

    def test_login_page_loads_the_theme(self):
        html = self.client.get(reverse("admin:login")).content.decode()
        self.assertIn("admin/css/assembly-admin.css", html)

    def test_login_page_shows_assembly_branding(self):
        html = self.client.get(reverse("admin:login")).content.decode()
        self.assertIn("assembly-brand", html)
        self.assertIn("admin/img/logo.png", html)
        self.assertIn("admin/img/logo-white.png", html)

    def test_dashboard_loads_the_theme(self):
        self.client.force_login(self.admin_user)
        html = self.client.get(reverse("admin:index")).content.decode()
        self.assertIn("admin/css/assembly-admin.css", html)

    def test_theme_assets_are_findable_by_staticfiles(self):
        from django.contrib.staticfiles import finders

        for asset in (
            "admin/css/assembly-admin.css",
            "admin/img/logo.png",
            "admin/img/logo-white.png",
        ):
            with self.subTest(asset=asset):
                self.assertIsNotNone(finders.find(asset), f"{asset} not found")

    def test_stylesheet_carries_the_site_palette(self):
        from django.contrib.staticfiles import finders
        from pathlib import Path

        css = Path(finders.find("admin/css/assembly-admin.css")).read_text("utf-8")
        # Tokens copied from src/app/globals.css. If the site rebrands, these
        # must be updated together.
        for token in ("#4f46e5", "#0f172a", "#f8fafc", "#070b16", "#818cf8"):
            with self.subTest(token=token):
                self.assertIn(token, css)

    def test_stylesheet_supports_both_themes(self):
        from django.contrib.staticfiles import finders
        from pathlib import Path

        css = Path(finders.find("admin/css/assembly-admin.css")).read_text("utf-8")
        self.assertIn('html[data-theme="dark"]', css)
        self.assertIn('html[data-theme="light"]', css)
        self.assertIn("prefers-color-scheme: dark", css)


class AdminAuthTests(TestCase):
    def test_admin_requires_login(self):
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])

    def test_non_staff_cannot_reach_admin(self):
        get_user_model().objects.create_user(
            username="visitor", password="not-a-real-password"
        )
        self.client.login(username="visitor", password="not-a-real-password")
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 302)
