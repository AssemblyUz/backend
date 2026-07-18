"""
Tests for the control panel's interface translations.

These cover the plumbing (middleware, switcher, catalogues) and a sample of the
strings, not every msgid — a full-catalogue assertion would just restate the
.po file.
"""

import pathlib

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from core.admin import field_label
from core.models import SiteSettings
from news.models import Article
from pages.models import HomeContent


class SettingsTests(TestCase):
    def test_locale_middleware_is_installed_after_session_middleware(self):
        mw = settings.MIDDLEWARE
        session = mw.index("django.contrib.sessions.middleware.SessionMiddleware")
        locale = mw.index("django.middleware.locale.LocaleMiddleware")
        common = mw.index("django.middleware.common.CommonMiddleware")
        # LocaleMiddleware reads the language from the session, and must run
        # before CommonMiddleware.
        self.assertLess(session, locale)
        self.assertLess(locale, common)

    def test_three_languages_are_offered(self):
        self.assertEqual([code for code, _name in settings.LANGUAGES], ["uz", "ru", "en"])

    def test_uzbek_is_the_default(self):
        self.assertEqual(settings.LANGUAGE_CODE, "uz")

    def test_project_catalogues_take_precedence_over_django(self):
        self.assertIn(settings.BASE_DIR / "locale", settings.LOCALE_PATHS)


class CatalogueTests(TestCase):
    """The compiled .mo files are committed, so deployment needs no gettext."""

    def test_compiled_catalogues_exist(self):
        for loc in ("uz", "ru"):
            mo = settings.BASE_DIR / "locale" / loc / "LC_MESSAGES" / "django.mo"
            with self.subTest(locale=loc):
                self.assertTrue(mo.exists(), f"{mo} missing — run scripts/compile_messages.py")

    def test_source_catalogues_exist(self):
        for loc in ("uz", "ru"):
            po = settings.BASE_DIR / "locale" / loc / "LC_MESSAGES" / "django.po"
            with self.subTest(locale=loc):
                self.assertTrue(po.exists())

    def test_mo_is_not_older_than_po(self):
        """A stale .mo silently serves the previous translations."""
        for loc in ("uz", "ru"):
            base = pathlib.Path(settings.BASE_DIR) / "locale" / loc / "LC_MESSAGES"
            with self.subTest(locale=loc):
                self.assertGreaterEqual(
                    (base / "django.mo").stat().st_mtime,
                    (base / "django.po").stat().st_mtime,
                    f"{loc}: django.mo is older than django.po — recompile it",
                )


class ModelNameTranslationTests(TestCase):
    def test_model_verbose_names_translate(self):
        expected = {
            "uz": ("Maqola", "Uyushma", "Sayt sozlamalari"),
            "ru": ("Статья", "Ассоциация", "Настройки сайта"),
            "en": ("Article", "Association", "Site settings"),
        }
        from catalog.models import Association

        for loc, (article, assoc, site) in expected.items():
            with translation.override(loc), self.subTest(locale=loc):
                self.assertEqual(str(Article._meta.verbose_name), article)
                self.assertEqual(str(Association._meta.verbose_name), assoc)
                self.assertEqual(str(SiteSettings._meta.verbose_name), site)

    def test_app_labels_translate(self):
        from django.apps import apps

        with translation.override("uz"):
            self.assertEqual(str(apps.get_app_config("news").verbose_name), "Yangiliklar")
        with translation.override("ru"):
            self.assertEqual(str(apps.get_app_config("news").verbose_name), "Новости")

    def test_singleton_str_follows_active_language(self):
        # The admin shows this as the object subtitle.
        home = HomeContent.load()
        with translation.override("uz"):
            self.assertEqual(str(home), "Bosh sahifa kontenti")
        with translation.override("en"):
            self.assertEqual(str(home), "Home page content")


class FieldLabelTests(TestCase):
    def test_locale_suffixed_field_gets_a_badge(self):
        with translation.override("en"):
            self.assertEqual(str(field_label("hero_title_uz")), "Hero title (UZ)")
            self.assertEqual(str(field_label("hero_title_ru")), "Hero title (RU)")

    def test_locale_suffixed_field_translates_its_base(self):
        with translation.override("uz"):
            self.assertEqual(str(field_label("hero_title_uz")), "Bosh blok sarlavhasi (UZ)")
        with translation.override("ru"):
            self.assertEqual(str(field_label("hero_title_en")), "Заголовок главного блока (EN)")

    def test_plain_field_has_no_badge(self):
        with translation.override("uz"):
            self.assertEqual(str(field_label("chairman")), "Rais")

    def test_unknown_field_falls_back_to_readable_english(self):
        # No catalogue entry: degrade to humanised English, never a blank label.
        with translation.override("uz"):
            self.assertEqual(str(field_label("some_new_field")), "Some new field")

    def test_a_field_ending_in_a_non_locale_word_is_not_treated_as_translated(self):
        with translation.override("en"):
            self.assertEqual(str(field_label("published_on")), "Published on")


class LanguageSwitcherTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username="editor", email="e@assembly.uz", password="not-a-real-password"
        )

    def test_switcher_renders_on_the_login_page(self):
        # admin/login.html empties `nav-global` and `usertools`, so the switcher
        # has to live in `branding` to be reachable before logging in.
        html = self.client.get(reverse("admin:login")).content.decode()
        self.assertEqual(html.count("assembly-lang-btn"), 3)
        for code in ("uz", "ru", "en"):
            self.assertIn(f'value="{code}"', html)

    def test_switcher_renders_on_the_dashboard(self):
        self.client.force_login(self.admin_user)
        html = self.client.get(reverse("admin:index")).content.decode()
        self.assertEqual(html.count("assembly-lang-btn"), 3)

    def test_active_language_is_marked(self):
        html = self.client.get(reverse("admin:login")).content.decode()
        self.assertIn("is-active", html)
        self.assertIn('aria-current="true"', html)

    def test_set_language_endpoint_is_wired(self):
        self.assertEqual(reverse("set_language"), "/i18n/setlang/")

    def test_switching_language_changes_the_rendered_admin(self):
        for code, expected in (("ru", "Контент сайта"), ("uz", "Sayt kontenti"), ("en", "Website content")):
            with self.subTest(language=code):
                response = self.client.post(
                    reverse("set_language"), {"language": code, "next": "/admin/"}
                )
                self.assertEqual(response.status_code, 302)

                self.client.force_login(self.admin_user)
                html = self.client.get(reverse("admin:index")).content.decode()
                self.assertIn(expected, html)

    def test_language_choice_persists_across_requests(self):
        self.client.post(reverse("set_language"), {"language": "ru", "next": "/admin/login/"})
        html = self.client.get(reverse("admin:login")).content.decode()
        self.assertIn("Войти", html)

    def test_accept_language_header_is_honoured_without_a_session_choice(self):
        html = self.client.get(
            reverse("admin:login"), headers={"accept-language": "ru"}
        ).content.decode()
        self.assertIn("Войти", html)

    def test_unknown_language_is_rejected_and_default_kept(self):
        self.client.post(reverse("set_language"), {"language": "xx", "next": "/admin/login/"})
        html = self.client.get(reverse("admin:login")).content.decode()
        self.assertIn("Kirish", html)  # still Uzbek, the default


class AdminChromeTranslationTests(TestCase):
    """A sample of the panel's own strings across the three languages."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username="chrome", email="c@assembly.uz", password="not-a-real-password"
        )

    def setUp(self):
        self.client.force_login(self.admin_user)

    def get(self, url: str, language: str) -> str:
        """
        Fetch a page in `language`.

        `translation.override` cannot be used here: LocaleMiddleware re-resolves
        the active language for every request, so the override is discarded
        before the view runs. Drive it the way a browser would instead.
        """
        return self.client.get(
            url, headers={"accept-language": language}
        ).content.decode()

    def test_index_title_translates(self):
        for loc, expected in (
            ("uz", "Sayt kontenti"),
            ("ru", "Контент сайта"),
            ("en", "Website content"),
        ):
            with self.subTest(locale=loc):
                self.assertIn(expected, self.get(reverse("admin:index"), loc))

    def test_admin_action_description_translates(self):
        # The actions dropdown only renders when the changelist has rows.
        Article.objects.create(slug="a-post", title_uz="Post")

        html = self.get(reverse("admin:news_article_changelist"), "uz")
        self.assertIn("Tanlangan maqolalarni nashr qilish", html)

    def test_fieldset_legend_translates(self):
        HomeContent.load()
        html = self.get(reverse("admin:pages_homecontent_change", args=[1]), "uz")
        self.assertIn("Bosh blok", html)

    def test_field_label_translates_on_the_change_form(self):
        HomeContent.load()
        html = self.get(reverse("admin:pages_homecontent_change", args=[1]), "ru")
        self.assertIn("Заголовок главного блока (UZ)", html)

    def test_uzbek_gaps_in_djangos_own_catalogue_are_filled(self):
        # Django ships an incomplete Uzbek admin catalogue; the project
        # catalogue supplies these.
        with translation.override("uz"):
            for msgid, expected in (
                ("Log in", "Kirish"),
                ("Home", "Bosh sahifa"),
                ("History", "Tarix"),
                ("Action", "Amal"),
                ("username", "foydalanuvchi nomi"),
            ):
                with self.subTest(msgid=msgid):
                    self.assertEqual(translation.gettext(msgid), expected)

    def test_russian_uses_djangos_own_complete_catalogue(self):
        # We must not override Django's Russian, which is complete upstream.
        with translation.override("ru"):
            self.assertEqual(translation.gettext("Log in"), "Войти")
            self.assertEqual(translation.gettext("Save"), "Сохранить")
