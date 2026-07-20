"""
Tests for the editor control panel API.

Weighted towards what must NOT be possible: the panel is the one authenticated
write surface on an otherwise read-only public API, so its failure modes are
unauthorised writes rather than wrong output.
"""

import datetime
import io

from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from news.models import Article, ArticleImage

PASSWORD = "panel-password-for-tests"


def photo_file(name: str = "p.jpg") -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", (60, 40), (90, 140, 200)).save(buf, format="JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


def make_article(slug: str = "post", **kwargs) -> Article:
    return Article.objects.create(
        slug=slug,
        title_uz=f"{slug} uz",
        published_on=datetime.date(2026, 1, 1),
        **kwargs,
    )


class PanelTestCase(TestCase):
    """Shared users. `editor` is the realistic account: staff, never superuser."""

    def setUp(self):
        # ScopedRateThrottle counts through the cache, which is process-wide and
        # survives between tests. Without this the login limiter -- correctly --
        # locks out every test after the tenth sign-in. Cleared rather than
        # raised so the limit stays exercised by ThrottleTests below.
        cache.clear()

        self.editor = User.objects.create_user("editor", password=PASSWORD, is_staff=True)
        self.editor.groups.add(Group.objects.get(name="Editor"))

        self.outsider = User.objects.create_user("outsider", password=PASSWORD)

        self.session_url = reverse("panel:panel-session")
        self.list_url = reverse("panel:panel-article-list")

    def sign_in(self, username: str = "editor") -> None:
        response = self.client.post(
            self.session_url,
            {"username": username, "password": PASSWORD},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)


class SessionTests(PanelTestCase):
    def test_anonymous_session_reports_no_user(self):
        body = self.client.get(self.session_url).json()
        self.assertIsNone(body["user"])

    def test_session_hands_out_a_csrf_token(self):
        """The panel needs one before it can issue its first write."""
        self.assertTrue(self.client.get(self.session_url).json()["csrfToken"])

    def test_editor_can_sign_in(self):
        self.sign_in()
        body = self.client.get(self.session_url).json()
        self.assertEqual(body["user"]["username"], "editor")
        self.assertFalse(body["user"]["isSuperuser"])

    def test_capabilities_drive_the_ui(self):
        self.sign_in()
        user = self.client.get(self.session_url).json()["user"]
        self.assertTrue(user["canPublish"])
        self.assertTrue(user["canUploadPhotos"])

    def test_non_staff_cannot_sign_in(self):
        response = self.client.post(
            self.session_url,
            {"username": "outsider", "password": PASSWORD},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_wrong_password_is_rejected(self):
        response = self.client.post(
            self.session_url,
            {"username": "editor", "password": "nope"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_failure_message_does_not_reveal_whether_the_user_exists(self):
        """Different messages would let an attacker enumerate staff accounts."""
        missing = self.client.post(
            self.session_url,
            {"username": "ghost", "password": "nope"},
            content_type="application/json",
        ).json()
        wrong = self.client.post(
            self.session_url,
            {"username": "editor", "password": "nope"},
            content_type="application/json",
        ).json()
        self.assertEqual(missing["detail"], wrong["detail"])

    def test_non_staff_failure_is_indistinguishable_from_a_bad_password(self):
        """Otherwise a correct password confirms the account exists."""
        non_staff = self.client.post(
            self.session_url,
            {"username": "outsider", "password": PASSWORD},
            content_type="application/json",
        ).json()
        wrong = self.client.post(
            self.session_url,
            {"username": "editor", "password": "nope"},
            content_type="application/json",
        ).json()
        self.assertEqual(non_staff["detail"], wrong["detail"])

    def test_sign_out_ends_the_session(self):
        self.sign_in()
        self.assertEqual(self.client.delete(self.session_url).status_code, 204)
        self.assertIsNone(self.client.get(self.session_url).json()["user"])


class LoginThrottleTests(PanelTestCase):
    """Password guessing must stop long before it succeeds."""

    def attempt(self, password: str = "wrong"):
        return self.client.post(
            self.session_url,
            {"username": "editor", "password": password},
            content_type="application/json",
        )

    def test_repeated_failures_are_eventually_blocked(self):
        codes = [self.attempt().status_code for _ in range(12)]
        self.assertIn(429, codes, "login endpoint never rate limited")

    def test_the_correct_password_is_refused_once_throttled(self):
        """A lockout an attacker can outlast by guessing right is not a lockout."""
        for _ in range(12):
            self.attempt()
        self.assertEqual(self.attempt(PASSWORD).status_code, 429)

    def test_reading_the_session_is_not_throttled(self):
        """The panel polls this; only the sign-in attempt is limited."""
        for _ in range(12):
            self.attempt()
        self.assertEqual(self.client.get(self.session_url).status_code, 200)


class AccessControlTests(PanelTestCase):
    """The panel must not become a way around Django admin's permissions."""

    def setUp(self):
        super().setUp()
        make_article("existing")

    def test_anonymous_cannot_list_articles(self):
        self.assertIn(self.client.get(self.list_url).status_code, (401, 403))

    def test_anonymous_cannot_create_an_article(self):
        response = self.client.post(
            self.list_url, {"slug": "sneaky"}, content_type="application/json"
        )
        self.assertIn(response.status_code, (401, 403))
        self.assertFalse(Article.objects.filter(slug="sneaky").exists())

    def test_signed_in_non_staff_cannot_write(self):
        self.client.force_login(self.outsider)
        response = self.client.post(
            self.list_url, {"slug": "sneaky"}, content_type="application/json"
        )
        self.assertIn(response.status_code, (401, 403))
        self.assertFalse(Article.objects.filter(slug="sneaky").exists())

    def test_staff_without_the_editor_group_cannot_write(self):
        """is_staff only means 'may open the admin', not 'may publish'."""
        bare = User.objects.create_user("bare", password=PASSWORD, is_staff=True)
        self.client.force_login(bare)
        response = self.client.post(
            self.list_url, {"slug": "sneaky"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Article.objects.filter(slug="sneaky").exists())

    def test_anonymous_cannot_delete(self):
        url = reverse("panel:panel-article-detail", kwargs={"slug": "existing"})
        self.assertIn(self.client.delete(url).status_code, (401, 403))
        self.assertTrue(Article.objects.filter(slug="existing").exists())

    def test_drafts_are_not_exposed_by_the_public_api(self):
        """The panel sees drafts; the public endpoint must not."""
        make_article("secret-draft", is_published=False)
        self.sign_in()
        panel = [a["slug"] for a in self.client.get(self.list_url).json()]
        self.assertIn("secret-draft", panel)

        self.client.delete(self.session_url)
        public = [a["slug"] for a in self.client.get(reverse("v1:article-list")).json()]
        self.assertNotIn("secret-draft", public)


class ArticleCrudTests(PanelTestCase):
    def setUp(self):
        super().setUp()
        self.sign_in()

    def test_create_an_article(self):
        response = self.client.post(
            self.list_url,
            {
                "slug": "new-post",
                "published_on": "2026-07-20",
                "icon": "📰",
                "title_uz": "Sarlavha",
                "title_ru": "Заголовок",
                "title_en": "Headline",
                "is_published": True,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(Article.objects.filter(slug="new-post").exists())

    def test_publishing_without_an_uzbek_title_is_rejected(self):
        """uz is the fallback locale — publishing without it renders blank."""
        response = self.client.post(
            self.list_url,
            {
                "slug": "no-uz",
                "published_on": "2026-07-20",
                "title_en": "English only",
                "is_published": True,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("title_uz", response.json())

    def test_a_draft_may_omit_the_uzbek_title(self):
        response = self.client.post(
            self.list_url,
            {
                "slug": "draft-ok",
                "published_on": "2026-07-20",
                "title_en": "Work in progress",
                "is_published": False,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)

    def test_duplicate_slug_is_rejected_against_the_right_field(self):
        """
        The error must be keyed to `slug` so the form can highlight that input.
        The message itself comes from DRF and is already localised.
        """
        make_article("taken")
        response = self.client.post(
            self.list_url,
            {"slug": "taken", "published_on": "2026-07-20", "title_uz": "x"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("slug", response.json())
        self.assertEqual(Article.objects.filter(slug="taken").count(), 1)

    def test_list_reports_translation_gaps(self):
        make_article("gappy", title_ru="", title_en="")
        rows = {a["slug"]: a for a in self.client.get(self.list_url).json()}
        self.assertEqual(sorted(rows["gappy"]["missing_translations"]), ["en", "ru"])

    def test_update_an_article(self):
        make_article("editable")
        url = reverse("panel:panel-article-detail", kwargs={"slug": "editable"})
        response = self.client.patch(
            url, {"title_en": "Renamed"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Article.objects.get(slug="editable").title_en, "Renamed")

    def test_delete_an_article(self):
        make_article("doomed")
        url = reverse("panel:panel-article-detail", kwargs={"slug": "doomed"})
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(Article.objects.filter(slug="doomed").exists())


@override_settings(MEDIA_ROOT="/tmp/assembly-panel-media")
class PhotoUploadTests(PanelTestCase):
    def setUp(self):
        super().setUp()
        self.sign_in()
        self.article = make_article("gallery")
        self.upload_url = reverse(
            "panel:panel-article-photos", kwargs={"slug": "gallery"}
        )

    def test_upload_photos(self):
        response = self.client.post(
            self.upload_url,
            {"images": [photo_file("a.jpg"), photo_file("b.jpg")], "sizes": ["full", "half"]},
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.article.images.count(), 2)
        self.assertEqual([p.size for p in self.article.images.all()], ["full", "half"])

    def test_upload_rejects_a_file_that_is_not_an_image(self):
        bogus = SimpleUploadedFile("x.jpg", b"definitely not an image", content_type="image/jpeg")
        response = self.client.post(self.upload_url, {"images": [bogus]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.article.images.count(), 0)

    def test_cannot_exceed_ten_photos_in_one_upload(self):
        files = [photo_file(f"{i}.jpg") for i in range(11)]
        response = self.client.post(self.upload_url, {"images": files})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.article.images.count(), 0)

    def test_cannot_exceed_ten_photos_across_several_uploads(self):
        """The cap counts what is stored, not just what is in this request."""
        for i in range(8):
            ArticleImage.objects.create(article=self.article, image=photo_file(f"e{i}.jpg"))

        response = self.client.post(
            self.upload_url, {"images": [photo_file("x.jpg"), photo_file("y.jpg"), photo_file("z.jpg")]}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("2 more", response.json()["detail"])
        self.assertEqual(self.article.images.count(), 8)

    def test_anonymous_cannot_upload(self):
        self.client.delete(self.session_url)
        response = self.client.post(self.upload_url, {"images": [photo_file()]})
        self.assertIn(response.status_code, (401, 403))
        self.assertEqual(self.article.images.count(), 0)

    def test_deleting_a_photo_removes_the_stored_file(self):
        photo = ArticleImage.objects.create(article=self.article, image=photo_file())
        storage, name = photo.image.storage, photo.image.name
        self.assertTrue(storage.exists(name))

        url = reverse("panel:panel-photo-detail", kwargs={"pk": photo.pk})
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(storage.exists(name))

    def test_reorder_and_resize_a_photo(self):
        photo = ArticleImage.objects.create(article=self.article, image=photo_file())
        url = reverse("panel:panel-photo-detail", kwargs={"pk": photo.pk})
        response = self.client.patch(
            url, {"size": "thumb", "order": 5}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        photo.refresh_from_db()
        self.assertEqual((photo.size, photo.order), ("thumb", 5))
