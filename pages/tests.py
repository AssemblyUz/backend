"""Tests for home and about page content endpoints."""

from django.test import TestCase
from django.urls import reverse

from .models import AboutContent, Direction, FunctionalBlock, HomeContent, Stat, Value


class HomeContentAPITests(TestCase):
    def setUp(self):
        home = HomeContent.load()
        home.hero_title_uz = "Assambleya"
        home.hero_title_en = "Assembly"
        home.save()
        Stat.objects.create(value="20", label_uz="Loyiha", label_en="Projects", order=0)
        Stat.objects.create(value="46", label_uz="Uyushma", label_en="Associations", order=1)

    def test_serves_requested_locale(self):
        response = self.client.get(reverse("v1:home-content"), {"locale": "en"})
        self.assertEqual(response.json()["hero_title"], "Assembly")

    def test_embeds_stats_in_order(self):
        data = self.client.get(reverse("v1:home-content"), {"locale": "uz"}).json()
        self.assertEqual([s["value"] for s in data["stats"]], ["20", "46"])
        self.assertEqual(data["stats"][0]["label"], "Loyiha")

    def test_missing_row_is_created_on_first_request(self):
        HomeContent.objects.all().delete()
        self.assertEqual(self.client.get(reverse("v1:home-content")).status_code, 200)


class AboutContentAPITests(TestCase):
    def setUp(self):
        about = AboutContent.load()
        about.mission_uz = "Missiya matni"
        about.mission_en = "Mission text"
        about.save()
        Value.objects.create(title_uz="Birlashuv", sub_uz="kuch", title_en="Unity", sub_en="strength")
        Direction.objects.create(name_uz="Ta'lim", name_en="Education")
        FunctionalBlock.objects.create(code="FR", title="Foreign Relations", desc_uz="desc")

    def test_serves_requested_locale(self):
        response = self.client.get(reverse("v1:about-content"), {"locale": "en"})
        self.assertEqual(response.json()["mission"], "Mission text")

    def test_directions_serialize_as_flat_strings(self):
        data = self.client.get(reverse("v1:about-content"), {"locale": "uz"}).json()
        self.assertEqual(data["directions"], ["Ta'lim"])

    def test_values_serialize_as_objects(self):
        data = self.client.get(reverse("v1:about-content"), {"locale": "en"}).json()
        self.assertEqual(data["values"], [{"title": "Unity", "sub": "strength"}])

    def test_functional_block_code_and_title_are_untranslated(self):
        data = self.client.get(reverse("v1:about-content"), {"locale": "ru"}).json()
        self.assertEqual(data["blocks"][0]["code"], "FR")
        self.assertEqual(data["blocks"][0]["title"], "Foreign Relations")

    def test_blank_translation_falls_back_to_uzbek(self):
        # mission_ru was never set, so the Uzbek text is served instead of "".
        data = self.client.get(reverse("v1:about-content"), {"locale": "ru"}).json()
        self.assertEqual(data["mission"], "Missiya matni")

    def test_unknown_locale_does_not_error(self):
        response = self.client.get(reverse("v1:about-content"), {"locale": "../etc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mission"], "Missiya matni")

    def test_payload_exposes_every_expected_list(self):
        data = self.client.get(reverse("v1:about-content")).json()
        for key in (
            "highlights", "role", "values", "directions", "architecture",
            "mechanism", "blocks", "media", "value_items", "roadmap",
            "kpi", "results",
        ):
            self.assertIn(key, data)
