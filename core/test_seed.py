"""
Tests for the `seed_content` migration command.

This command moves the site's entire existing content into the database. A
silent failure here loses content, so it is tested against a fixture with the
same shape as the real messages/*.json export.
"""

import json
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase

from catalog.models import Association, Partner, PartnerGroup, Project, Service
from core.models import LOCALES, SiteSettings, SocialLink
from news.models import Article
from pages.models import (
    AboutContent,
    ArchitectureNode,
    Direction,
    FunctionalBlock,
    Highlight,
    HomeContent,
    Kpi,
    MechanismStep,
    MediaFeature,
    Result,
    RoadmapStage,
    StakeholderValue,
    Stat,
    StrategicRole,
    Value,
)


def _per_locale(value: str) -> dict:
    return {loc: f"{value}-{loc}" for loc in LOCALES}


def _messages_for(locale: str) -> dict:
    """One locale's slice of the message file, with every list the command reads."""
    suffix = f"-{locale}"

    def obj(*keys):
        return {key: f"{key}{suffix}" for key in keys}

    return {
        "site": obj("name", "short", "tagline", "description"),
        "footer": {
            "address": f"address{suffix}",
            "email": "info@assembly.uz",
            "phone": "+998 71 200 00 00",
        },
        "home": {
            "heroBadge": f"heroBadge{suffix}",
            "heroTitle": f"heroTitle{suffix}",
            "heroLead": f"heroLead{suffix}",
            "stats": {
                "projects": f"Projects{suffix}",
                "associations": f"Associations{suffix}",
                "members": f"Members{suffix}",
                "years": f"Years{suffix}",
            },
        },
        "about": {
            "mission": f"mission{suffix}",
            "motto": f"motto{suffix}",
            "highlights": [{"value": "50+", "label": f"network{suffix}"}],
            "role": [f"role-one{suffix}", f"role-two{suffix}"],
            "values": [{"title": f"Unity{suffix}", "sub": f"strength{suffix}"}],
            "directions": [f"Education{suffix}", f"Innovation{suffix}"],
            "architecture": [{"title": f"State{suffix}", "desc": f"strategy{suffix}"}],
            "mechanism": [{"title": f"Step{suffix}", "desc": f"desc{suffix}"}],
            "blocks": [
                {"code": "FR", "title": "Foreign Relations", "desc": f"fr{suffix}"},
                {"code": "BR", "title": "Business Relations", "desc": f"br{suffix}"},
            ],
            "media": [{"title": f"Coverage{suffix}", "desc": f"stream{suffix}"}],
            "valueItems": [{"title": f"Gov{suffix}", "desc": f"value{suffix}"}],
            "roadmap": [
                {"period": f"90d{suffix}", "title": f"CRM{suffix}", "desc": f"d{suffix}"}
            ],
            "kpi": [{"value": "50+", "label": f"Associations{suffix}"}],
            "results": [{"title": f"Economy{suffix}", "desc": f"desc{suffix}"}],
            "partners": [{"title": f"Banks{suffix}", "items": ["EBRD"]}],
        },
        "services": {
            "items": [
                {"icon": "⚖️", "name": f"Legal{suffix}", "desc": f"advice{suffix}"}
            ]
        },
        "projects": {
            "items": [
                {"icon": "🎓", "name": "EDU-JOB", "desc": f"edu{suffix}"},
                {"icon": "📈", "name": "INVEST HUB", "desc": f"invest{suffix}"},
            ]
        },
    }


FIXTURE = {
    "messages": {loc: _messages_for(loc) for loc in LOCALES},
    "associations": [
        {
            "name": {"uz": "Uyushma", "ru": "Ассоциация", "en": "Agribusiness Association"},
            "chairman": "Someone",
            "phone": "+998 71 000 00 00",
            "activity": _per_locale("activity"),
        }
    ],
    "news": [
        {
            "slug": "first-post",
            "date": "2026-01-15",
            "icon": "🚀",
            "tag": _per_locale("tag"),
            "title": _per_locale("title"),
            "excerpt": _per_locale("excerpt"),
            "body": [_per_locale("para-one"), _per_locale("para-two")],
        }
    ],
    "socials": [{"id": "telegram", "name": "Telegram", "href": "https://t.me/x"}],
    "projectLinks": {"EDU-JOB": "https://edujob.uz"},
}


class SeedContentTests(TestCase):
    """Runs the real command against an in-memory fixture."""

    def setUp(self):
        self._patch_fixture(FIXTURE)

    def _patch_fixture(self, fixture: dict):
        payload = json.dumps(fixture)
        path = patch("core.management.commands.seed_content.SEED_FILE")
        mock_path = path.start()
        self.addCleanup(path.stop)
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = payload

    def test_aborts_when_seed_file_is_missing(self):
        with patch("core.management.commands.seed_content.SEED_FILE") as missing:
            missing.exists.return_value = False
            with self.assertRaises(CommandError):
                call_command("seed_content")

    def test_aborts_when_a_locale_is_absent(self):
        broken = {**FIXTURE, "messages": {"uz": _messages_for("uz")}}
        self._patch_fixture(broken)
        with self.assertRaises(CommandError):
            call_command("seed_content")

    def test_dry_run_writes_nothing(self):
        call_command("seed_content", "--dry-run")
        self.assertEqual(Association.objects.count(), 0)
        self.assertEqual(Article.objects.count(), 0)
        self.assertEqual(Value.objects.count(), 0)

    def test_imports_every_content_type(self):
        call_command("seed_content")

        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(SocialLink.objects.count(), 1)
        self.assertEqual(HomeContent.objects.count(), 1)
        self.assertEqual(AboutContent.objects.count(), 1)
        self.assertEqual(Stat.objects.count(), 4)
        self.assertEqual(Association.objects.count(), 1)
        self.assertEqual(Service.objects.count(), 1)
        self.assertEqual(Project.objects.count(), 2)
        self.assertEqual(PartnerGroup.objects.count(), 1)
        self.assertEqual(Partner.objects.count(), 1)
        self.assertEqual(Article.objects.count(), 1)

    def test_imports_every_about_block(self):
        call_command("seed_content")
        self.assertEqual(Highlight.objects.count(), 1)
        self.assertEqual(StrategicRole.objects.count(), 2)
        self.assertEqual(Value.objects.count(), 1)
        self.assertEqual(Direction.objects.count(), 2)
        self.assertEqual(ArchitectureNode.objects.count(), 1)
        self.assertEqual(MechanismStep.objects.count(), 1)
        self.assertEqual(FunctionalBlock.objects.count(), 2)
        self.assertEqual(MediaFeature.objects.count(), 1)
        self.assertEqual(StakeholderValue.objects.count(), 1)
        self.assertEqual(RoadmapStage.objects.count(), 1)
        self.assertEqual(Kpi.objects.count(), 1)
        self.assertEqual(Result.objects.count(), 1)

    def test_translates_all_three_locales(self):
        call_command("seed_content")
        about = AboutContent.load()
        self.assertEqual(about.mission_uz, "mission-uz")
        self.assertEqual(about.mission_ru, "mission-ru")
        self.assertEqual(about.mission_en, "mission-en")

    def test_association_slug_matches_frontend(self):
        call_command("seed_content")
        self.assertTrue(
            Association.objects.filter(slug="agribusiness-association").exists()
        )

    def test_project_url_comes_from_project_links(self):
        call_command("seed_content")
        self.assertEqual(Project.objects.get(name="EDU-JOB").url, "https://edujob.uz")
        self.assertEqual(Project.objects.get(name="INVEST HUB").url, "")

    def test_news_body_is_joined_into_paragraphs(self):
        call_command("seed_content")
        article = Article.objects.get(slug="first-post")
        self.assertEqual(article.body_paragraphs("uz"), ["para-one-uz", "para-two-uz"])
        self.assertTrue(article.is_published)

    def test_ordering_is_preserved(self):
        call_command("seed_content")
        directions = list(Direction.objects.values_list("name_uz", flat=True))
        self.assertEqual(directions, ["Education-uz", "Innovation-uz"])

    def test_is_idempotent(self):
        call_command("seed_content")
        call_command("seed_content")

        # Re-running must update in place, never duplicate.
        self.assertEqual(Association.objects.count(), 1)
        self.assertEqual(Article.objects.count(), 1)
        self.assertEqual(Project.objects.count(), 2)
        self.assertEqual(Value.objects.count(), 1)
        self.assertEqual(FunctionalBlock.objects.count(), 2)
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(PartnerGroup.objects.count(), 1)
        self.assertEqual(Partner.objects.count(), 1)


class SeedPartnersTests(TestCase):
    """Partners are a nested group -> items structure, so they get their own case."""

    def setUp(self):
        fixture = json.loads(json.dumps(FIXTURE))
        for loc in LOCALES:
            fixture["messages"][loc]["about"]["partners"] = [
                {"title": f"Banks-{loc}", "items": [f"OTP-{loc}", "TBC"]},
                {"title": f"Tech-{loc}", "items": ["Huawei"]},
            ]
        payload = json.dumps(fixture)
        path = patch("core.management.commands.seed_content.SEED_FILE")
        mock_path = path.start()
        self.addCleanup(path.stop)
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = payload

    def test_creates_groups_and_nested_partners(self):
        call_command("seed_content")
        self.assertEqual(PartnerGroup.objects.count(), 2)
        self.assertEqual(Partner.objects.count(), 3)

    def test_partner_locale_overrides_are_stored(self):
        call_command("seed_content")
        otp = Partner.objects.get(name="OTP-uz")
        self.assertEqual(otp.display_name("ru"), "OTP-ru")
        self.assertEqual(otp.display_name("en"), "OTP-en")

    def test_rerun_does_not_duplicate_partners(self):
        call_command("seed_content")
        call_command("seed_content")
        self.assertEqual(PartnerGroup.objects.count(), 2)
        self.assertEqual(Partner.objects.count(), 3)
