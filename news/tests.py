"""Tests for article publishing rules, ordering and body splitting."""

import datetime

from django.test import TestCase
from django.urls import reverse

from .models import Article


def make_article(slug: str, **kwargs) -> Article:
    defaults = dict(
        title_uz=f"{slug} uz",
        title_en=f"{slug} en",
        excerpt_uz="excerpt",
        body_uz="First para.\n\nSecond para.",
        is_published=True,
        published_on=datetime.date(2026, 1, 1),
    )
    return Article.objects.create(slug=slug, **{**defaults, **kwargs})


class PublishedManagerTests(TestCase):
    def test_excludes_unpublished(self):
        make_article("draft", is_published=False)
        self.assertEqual(Article.published.count(), 0)

    def test_excludes_future_dated(self):
        make_article("future", published_on=datetime.date(2999, 1, 1))
        self.assertEqual(Article.published.count(), 0)

    def test_includes_published_and_dated_today_or_earlier(self):
        make_article("live")
        self.assertEqual(Article.published.count(), 1)


class BodyParagraphTests(TestCase):
    def test_splits_on_blank_line(self):
        article = make_article("post")
        self.assertEqual(article.body_paragraphs("uz"), ["First para.", "Second para."])

    def test_drops_empty_paragraphs(self):
        article = make_article("post", body_uz="One.\n\n\n\nTwo.\n\n")
        self.assertEqual(article.body_paragraphs("uz"), ["One.", "Two."])

    def test_falls_back_to_uzbek_when_locale_body_blank(self):
        article = make_article("post", body_en="")
        self.assertEqual(article.body_paragraphs("en"), ["First para.", "Second para."])

    def test_missing_translations_reports_blank_titles(self):
        article = make_article("post", title_ru="")
        self.assertEqual(article.missing_translations(), ["ru"])


class ArticleAPITests(TestCase):
    def setUp(self):
        make_article("older", published_on=datetime.date(2026, 1, 1))
        make_article("newer", published_on=datetime.date(2026, 6, 1))
        make_article("hidden", is_published=False)

    def test_list_is_newest_first(self):
        response = self.client.get(reverse("v1:article-list"), {"locale": "uz"})
        slugs = [item["slug"] for item in response.json()]
        self.assertEqual(slugs, ["newer", "older"])

    def test_list_excludes_drafts(self):
        response = self.client.get(reverse("v1:article-list"))
        self.assertNotIn("hidden", [item["slug"] for item in response.json()])

    def test_draft_detail_is_404_not_guessable(self):
        url = reverse("v1:article-detail", kwargs={"slug": "hidden"})
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_list_omits_body(self):
        response = self.client.get(reverse("v1:article-list"))
        self.assertNotIn("body", response.json()[0])

    def test_detail_includes_body_as_paragraph_list(self):
        url = reverse("v1:article-detail", kwargs={"slug": "newer"})
        body = self.client.get(url, {"locale": "uz"}).json()["body"]
        self.assertEqual(body, ["First para.", "Second para."])

    def test_detail_serves_iso_date(self):
        url = reverse("v1:article-detail", kwargs={"slug": "newer"})
        self.assertEqual(self.client.get(url).json()["date"], "2026-06-01")
