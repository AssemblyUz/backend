"""Tests for catalog models, slug parity with the frontend, and the API."""

from django.test import TestCase
from django.urls import reverse

from .models import Association, Partner, PartnerGroup, Project, Service, slugify_name


class SlugifyParityTests(TestCase):
    """
    These expectations come from the frontend `slugify()` in
    src/data/associations.ts. If this drifts, existing URLs 404.
    """

    def test_lowercases_and_hyphenates(self):
        self.assertEqual(slugify_name("Agribusiness Association"), "agribusiness-association")

    def test_expands_ampersand(self):
        self.assertEqual(slugify_name("Oil & Gas"), "oil-and-gas")

    def test_strips_quotes_and_parentheses(self):
        self.assertEqual(slugify_name('Chamber "Uz" (main)'), "chamber-uz-main")

    def test_trims_leading_and_trailing_hyphens(self):
        self.assertEqual(slugify_name("  Hello!  "), "hello")


class AssociationTests(TestCase):
    def test_slug_generated_from_english_name(self):
        assoc = Association.objects.create(name_en="Chamber of Auditors")
        self.assertEqual(assoc.slug, "chamber-of-auditors")

    def test_explicit_slug_is_preserved(self):
        assoc = Association.objects.create(name_en="Whatever", slug="legacy-url")
        self.assertEqual(assoc.slug, "legacy-url")

    def test_unpublished_is_hidden_from_api(self):
        Association.objects.create(name_en="Hidden", is_published=False)
        response = self.client.get(reverse("v1:association-list"))
        self.assertEqual(response.json(), [])

    def test_detail_lookup_is_by_slug(self):
        Association.objects.create(name_en="Visible One", name_uz="Ko'rinadigan")
        url = reverse("v1:association-detail", kwargs={"slug": "visible-one"})
        response = self.client.get(url, {"locale": "uz"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Ko'rinadigan")


class ProjectTests(TestCase):
    def test_blank_url_is_serialized_as_empty_string(self):
        Project.objects.create(icon="🎓", name="EDU-JOB", desc_uz="x")
        response = self.client.get(reverse("v1:project-list"), {"locale": "uz"})
        self.assertEqual(response.json()[0]["url"], "")

    def test_ordering_follows_order_field(self):
        Project.objects.create(icon="a", name="Second", order=2)
        Project.objects.create(icon="b", name="First", order=1)
        response = self.client.get(reverse("v1:project-list"))
        self.assertEqual([p["name"] for p in response.json()], ["First", "Second"])


class ServiceTests(TestCase):
    def test_unpublished_hidden(self):
        Service.objects.create(icon="⚖️", name_uz="Hidden", is_published=False)
        self.assertEqual(self.client.get(reverse("v1:service-list")).json(), [])


class PartnerGroupTests(TestCase):
    def setUp(self):
        self.group = PartnerGroup.objects.create(title_uz="Banklar", title_en="Banks")

    def test_partner_falls_back_to_untranslated_name(self):
        Partner.objects.create(group=self.group, name="EBRD")
        response = self.client.get(reverse("v1:partner-list"), {"locale": "ru"})
        self.assertEqual(response.json()[0]["items"][0]["name"], "EBRD")

    def test_partner_uses_locale_override_when_present(self):
        Partner.objects.create(
            group=self.group, name="Ministries", name_ru="Министерства"
        )
        response = self.client.get(reverse("v1:partner-list"), {"locale": "ru"})
        self.assertEqual(response.json()[0]["items"][0]["name"], "Министерства")

    def test_group_title_is_localized(self):
        response = self.client.get(reverse("v1:partner-list"), {"locale": "en"})
        self.assertEqual(response.json()[0]["title"], "Banks")

    def test_partners_are_fetched_without_n_plus_one(self):
        for i in range(5):
            Partner.objects.create(group=self.group, name=f"P{i}", order=i)
        # One query for groups, one prefetch for partners.
        with self.assertNumQueries(2):
            self.client.get(reverse("v1:partner-list"))
