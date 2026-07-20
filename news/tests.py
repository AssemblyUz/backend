"""Tests for article publishing rules, ordering, body splitting and photos."""

import datetime
import io
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Article, ArticleImage


def make_image_file(name: str = "photo.jpg", fmt: str = "JPEG", size=(40, 30)) -> SimpleUploadedFile:
    """A real encoded image — ImageField runs Pillow, so bytes must be genuine."""
    buf = io.BytesIO()
    Image.new("RGB", size, (120, 160, 200)).save(buf, format=fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type=f"image/{fmt.lower()}")


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


@override_settings(MEDIA_ROOT="/tmp/assembly-test-media")
class ArticlePhotoTests(TestCase):
    """Photos: the 10 cap, upload validation, ordering, and API exposure."""

    def setUp(self):
        self.article = make_article("with-photos")

    def add_photo(self, **kwargs) -> ArticleImage:
        defaults = {"article": self.article, "image": make_image_file()}
        return ArticleImage.objects.create(**{**defaults, **kwargs})

    def test_photo_defaults_to_full_width(self):
        self.assertEqual(self.add_photo().size, ArticleImage.Size.FULL)

    def test_editor_can_choose_a_display_size(self):
        photo = self.add_photo(size=ArticleImage.Size.HALF)
        self.assertEqual(photo.size, "half")

    def test_photos_come_back_in_editor_order(self):
        self.add_photo(order=2, alt_uz="second")
        self.add_photo(order=1, alt_uz="first")
        self.assertEqual(
            [p.alt_uz for p in self.article.images.all()], ["first", "second"]
        )

    def test_rejects_a_file_that_is_not_an_image(self):
        bogus = SimpleUploadedFile("evil.jpg", b"this is not an image", content_type="image/jpeg")
        photo = ArticleImage(article=self.article, image=bogus)
        with self.assertRaises(ValidationError):
            photo.full_clean()

    def test_rejects_an_oversized_upload(self):
        big = make_image_file(size=(40, 30))
        big.size = 6 * 1024 * 1024  # over the 5 MB limit
        photo = ArticleImage(article=self.article, image=big)
        with self.assertRaises(ValidationError) as ctx:
            photo.full_clean()
        self.assertIn("limit", str(ctx.exception).lower())

    def test_detail_api_returns_the_gallery(self):
        self.add_photo(order=1, alt_en="first photo")
        self.add_photo(order=2, size=ArticleImage.Size.THUMB)
        url = reverse("v1:article-detail", kwargs={"slug": "with-photos"})
        images = self.client.get(url, {"locale": "en"}).json()["images"]

        self.assertEqual(len(images), 2)
        self.assertEqual(images[0]["alt"], "first photo")
        self.assertEqual(images[1]["size"], "thumb")
        self.assertTrue(images[0]["url"].endswith((".jpg", ".jpeg")))

    def test_list_api_returns_only_the_cover(self):
        self.add_photo(order=1, alt_en="cover")
        self.add_photo(order=2, alt_en="not the cover")
        items = self.client.get(reverse("v1:article-list"), {"locale": "en"}).json()
        card = next(i for i in items if i["slug"] == "with-photos")

        self.assertEqual(card["cover"]["alt"], "cover")
        self.assertNotIn("images", card)

    def test_article_without_photos_has_a_null_cover(self):
        items = self.client.get(reverse("v1:article-list")).json()
        card = next(i for i in items if i["slug"] == "with-photos")
        self.assertIsNone(card["cover"])

    @override_settings(MEDIA_BASE_URL="https://assembly.uz")
    def test_media_urls_are_absolute_when_a_public_origin_is_set(self):
        self.add_photo()
        url = reverse("v1:article-detail", kwargs={"slug": "with-photos"})
        images = self.client.get(url).json()["images"]
        self.assertTrue(images[0]["url"].startswith("https://assembly.uz/media/"))

    def test_admin_rejects_more_than_ten_photos(self):
        """The cap the editor was promised. Exercised through the real admin form."""
        from django.contrib.auth.models import User

        admin_user = User.objects.create_superuser("boss", "b@assembly.uz", "pw-for-tests")
        self.client.force_login(admin_user)

        over = ArticleImage.MAX_PER_ARTICLE + 1
        payload = {
            "slug": self.article.slug,
            "published_on": "2026-01-01",
            "icon": "📰",
            "title_uz": "t", "title_ru": "", "title_en": "",
            "tag_uz": "", "tag_ru": "", "tag_en": "",
            "excerpt_uz": "", "excerpt_ru": "", "excerpt_en": "",
            "body_uz": "", "body_ru": "", "body_en": "",
            "images-TOTAL_FORMS": str(over),
            "images-INITIAL_FORMS": "0",
            "images-MIN_NUM_FORMS": "0",
            "images-MAX_NUM_FORMS": "1000",
        }
        files = {}
        for i in range(over):
            payload[f"images-{i}-size"] = "full"
            payload[f"images-{i}-order"] = str(i)
            payload[f"images-{i}-alt_uz"] = ""
            payload[f"images-{i}-alt_ru"] = ""
            payload[f"images-{i}-alt_en"] = ""
            files[f"images-{i}-image"] = make_image_file(f"p{i}.jpg")

        response = self.client.post(
            reverse("admin:news_article_change", args=[self.article.pk]),
            {**payload, **files},
            SERVER_NAME="127.0.0.1",
        )

        # Re-rendered form (200), not a redirect (302) — and nothing was stored.
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(self.article.images.count(), ArticleImage.MAX_PER_ARTICLE)
        self.assertEqual(self.article.images.count(), 0)

    def test_admin_accepts_exactly_ten_photos(self):
        """The boundary must be inclusive — 10 is allowed, 11 is not."""
        from django.contrib.auth.models import User

        admin_user = User.objects.create_superuser("boss2", "b2@assembly.uz", "pw-for-tests")
        self.client.force_login(admin_user)

        limit = ArticleImage.MAX_PER_ARTICLE
        payload = {
            "slug": self.article.slug,
            "published_on": "2026-01-01",
            "icon": "📰",
            "title_uz": "t", "title_ru": "", "title_en": "",
            "tag_uz": "", "tag_ru": "", "tag_en": "",
            "excerpt_uz": "", "excerpt_ru": "", "excerpt_en": "",
            "body_uz": "", "body_ru": "", "body_en": "",
            "images-TOTAL_FORMS": str(limit),
            "images-INITIAL_FORMS": "0",
            "images-MIN_NUM_FORMS": "0",
            "images-MAX_NUM_FORMS": "1000",
        }
        files = {}
        for i in range(limit):
            payload[f"images-{i}-size"] = "full"
            payload[f"images-{i}-order"] = str(i)
            payload[f"images-{i}-alt_uz"] = ""
            payload[f"images-{i}-alt_ru"] = ""
            payload[f"images-{i}-alt_en"] = ""
            files[f"images-{i}-image"] = make_image_file(f"q{i}.jpg")

        response = self.client.post(
            reverse("admin:news_article_change", args=[self.article.pk]),
            {**payload, **files},
            SERVER_NAME="127.0.0.1",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.article.images.count(), limit)

    def test_deleting_an_article_removes_its_photos(self):
        self.add_photo()
        self.assertEqual(ArticleImage.objects.count(), 1)
        self.article.delete()
        self.assertEqual(ArticleImage.objects.count(), 0)


class ScheduledPublishTests(TestCase):
    """
    A post dated in the future must go live on its own, without a redeploy.

    Regression test for the viewset holding `Article.published.all()` as a class
    attribute: that evaluates `timezone.localdate()` once at import, baking the
    boot date into the WHERE clause for the whole life of the worker. Because
    gunicorn runs without `--max-requests`, the worker is never recycled, so a
    scheduled post stayed invisible indefinitely.
    """

    def setUp(self):
        self.today = datetime.date(2026, 6, 1)
        self.tomorrow = self.today + datetime.timedelta(days=1)
        make_article("scheduled", published_on=self.tomorrow)

    def _slugs_on(self, date: datetime.date) -> list[str]:
        with patch("news.models.timezone.localdate", return_value=date):
            response = self.client.get(reverse("v1:article-list"))
            return [item["slug"] for item in response.json()]

    def test_hidden_before_its_publish_date(self):
        self.assertNotIn("scheduled", self._slugs_on(self.today))

    def test_appears_once_the_date_arrives_without_a_restart(self):
        self.assertNotIn("scheduled", self._slugs_on(self.today))
        self.assertIn("scheduled", self._slugs_on(self.tomorrow))

    def test_detail_is_404_before_its_publish_date(self):
        url = reverse("v1:article-detail", kwargs={"slug": "scheduled"})
        with patch("news.models.timezone.localdate", return_value=self.today):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_detail_resolves_once_the_date_arrives(self):
        url = reverse("v1:article-detail", kwargs={"slug": "scheduled"})
        with patch("news.models.timezone.localdate", return_value=self.tomorrow):
            self.assertEqual(self.client.get(url).status_code, 200)
