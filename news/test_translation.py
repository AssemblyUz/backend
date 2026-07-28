"""
Tests for filling an article's missing translations.

The provider is always stubbed at the single function that performs HTTP, so the
suite never reaches the network: it must pass offline, in CI, and without anyone
holding an API key.
"""

import datetime
from unittest import mock

from django.test import TestCase

from .models import Article
from .translation import (
    TranslationUnavailable,
    _chunks,
    fill_missing_translations,
    pending_fields,
    source_locale,
    translate,
)


def fake_translation(text: str, source: str, target: str) -> str:
    """Marks the text so tests can prove which field went where."""
    return f"[{target}] {text}"


class SourceLocaleTests(TestCase):
    def test_prefers_uzbek(self):
        article = Article(title_uz="Sarlavha", title_ru="Заголовок")
        self.assertEqual(source_locale(article), "uz")

    def test_falls_back_to_whichever_locale_has_a_title(self):
        article = Article(title_ru="Заголовок")
        self.assertEqual(source_locale(article), "ru")

    def test_returns_none_when_there_is_nothing_to_translate_from(self):
        self.assertIsNone(source_locale(Article()))

    def test_ignores_a_title_of_only_spaces(self):
        self.assertIsNone(source_locale(Article(title_uz="   ")))


class ChunkTests(TestCase):
    def test_short_prose_is_one_piece_per_paragraph(self):
        self.assertEqual(_chunks("Bir gap."), ["Bir gap."])

    def test_a_long_paragraph_is_split_at_sentence_ends(self):
        sentence = "Bu juda uzun gap boʻlib, matnni boʻlish uchun ishlatiladi. "
        pieces = _chunks(sentence * 40)

        self.assertGreater(len(pieces), 1)
        for piece in pieces:
            self.assertLessEqual(len(piece), 1200)
        # No sentence may be cut in half, or the translation is nonsense.
        for piece in pieces:
            self.assertTrue(piece.endswith(".") or piece.endswith("!") or piece.endswith("?"))


class TranslateTests(TestCase):
    def test_paragraph_breaks_survive(self):
        with mock.patch("news.translation._translate_free", side_effect=fake_translation):
            result = translate("Birinchi.\n\nIkkinchi.", "uz", "en")

        self.assertEqual(result, "[en] Birinchi.\n\n[en] Ikkinchi.")

    def test_empty_text_needs_no_request(self):
        with mock.patch("news.translation._translate_free") as provider:
            self.assertEqual(translate("   ", "uz", "en"), "")
        provider.assert_not_called()

    def test_uses_the_official_api_when_a_key_is_configured(self):
        with self.settings(TRANSLATE_API_KEY="a-key"):
            with mock.patch(
                "news.translation._translate_official", side_effect=fake_translation
            ) as official:
                with mock.patch("news.translation._translate_free") as free:
                    translate("Salom.", "uz", "ru")

        official.assert_called_once()
        free.assert_not_called()


class FillMissingTranslationsTests(TestCase):
    def setUp(self):
        self.article = Article.objects.create(
            slug="uchrashuv",
            published_on=datetime.date(2026, 7, 28),
            title_uz="Xalqaro hamkorlik",
            tag_uz="Hamkorlik",
            excerpt_uz="Qisqa mazmun.",
            body_uz="Birinchi xat boshi.\n\nIkkinchi xat boshi.",
        )

    def fill(self, side_effect=fake_translation):
        with mock.patch("news.translation._translate_free", side_effect=side_effect):
            return fill_missing_translations(self.article)

    def test_fills_both_other_languages_from_uzbek(self):
        filled = self.fill()
        self.article.refresh_from_db()

        self.assertEqual(self.article.title_ru, "[ru] Xalqaro hamkorlik")
        self.assertEqual(self.article.title_en, "[en] Xalqaro hamkorlik")
        self.assertEqual(self.article.excerpt_ru, "[ru] Qisqa mazmun.")
        self.assertEqual(
            self.article.body_en,
            "[en] Birinchi xat boshi.\n\n[en] Ikkinchi xat boshi.",
        )
        self.assertEqual(len(filled), 8)  # four fields, two languages

    def test_never_overwrites_what_a_person_wrote(self):
        self.article.title_ru = "Мой собственный заголовок"
        self.article.save(update_fields=["title_ru"])

        self.fill()
        self.article.refresh_from_db()

        self.assertEqual(self.article.title_ru, "Мой собственный заголовок")
        self.assertEqual(self.article.title_en, "[en] Xalqaro hamkorlik")

    def test_leaves_the_source_language_alone(self):
        self.fill()
        self.article.refresh_from_db()
        self.assertEqual(self.article.title_uz, "Xalqaro hamkorlik")

    def test_skips_fields_the_editor_left_empty_in_the_source(self):
        self.article.tag_uz = ""
        self.article.save(update_fields=["tag_uz"])

        self.fill()
        self.article.refresh_from_db()

        self.assertEqual(self.article.tag_ru, "")
        self.assertEqual(self.article.tag_en, "")

    def test_a_provider_outage_does_not_break_the_save(self):
        """
        The editor's work is already stored by this point. A translation service
        that is down must cost them a translation, never the article.
        """
        filled = self.fill(side_effect=TranslationUnavailable("blocked"))
        self.article.refresh_from_db()

        self.assertEqual(filled, [])
        self.assertEqual(self.article.title_uz, "Xalqaro hamkorlik")
        self.assertEqual(self.article.title_ru, "")

    def test_a_network_error_does_not_break_the_save(self):
        filled = self.fill(side_effect=OSError("connection reset"))
        self.assertEqual(filled, [])

    def test_an_article_with_no_text_at_all_is_left_alone(self):
        empty = Article.objects.create(slug="bosh", published_on=datetime.date(2026, 7, 28))
        with mock.patch("news.translation._translate_free") as provider:
            self.assertEqual(fill_missing_translations(empty), [])
        provider.assert_not_called()

    def test_translating_twice_does_not_replace_the_first_result(self):
        """Re-saving an article must not re-translate what is already there."""
        self.fill()
        with mock.patch("news.translation._translate_free") as provider:
            self.assertEqual(fill_missing_translations(self.article), [])
        provider.assert_not_called()


class PendingFieldsTests(TestCase):
    def test_sees_a_gap_in_one_field_even_when_the_title_is_present(self):
        """
        `Article.missing_translations` only looks at titles, so a Russian title
        with no Russian body used to count as fully translated.
        """
        article = Article(
            title_uz="Sarlavha",
            title_ru="Заголовок",
            body_uz="Matn.",
        )
        self.assertIn(("body", "uz", "ru"), pending_fields(article))
        self.assertNotIn(("title", "uz", "ru"), pending_fields(article))

    def test_reports_nothing_for_an_article_with_no_source_text(self):
        self.assertEqual(pending_fields(Article()), [])
