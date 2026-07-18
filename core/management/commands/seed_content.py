"""
Import the frontend's static content into the database.

    python manage.py seed_content

Reads backend/seed/content.json, produced by:
    node --experimental-strip-types backend/seed/export_frontend_data.mjs

Idempotent: every object is matched on a natural key and updated in place, so
running it twice does not duplicate rows. Existing edits made in the admin ARE
overwritten — this is a migration tool, not a merge. Pass --dry-run to see the
counts without touching the database.
"""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

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

SEED_FILE = Path(settings.BASE_DIR) / "seed" / "content.json"


def tr(messages: dict, namespace: str, key: str) -> dict:
    """Collect one message key across all locales into {'<key>_uz': ..., ...}."""
    return {
        f"{key}_{loc}": messages[loc][namespace].get(key, "") for loc in LOCALES
    }


def tr_from(messages: dict, namespace: str, mapping: dict[str, str]) -> dict:
    """Map {model_field: message_key} across all locales."""
    fields = {}
    for model_field, message_key in mapping.items():
        for loc in LOCALES:
            fields[f"{model_field}_{loc}"] = messages[loc][namespace].get(message_key, "")
    return fields


def tr_item(items: dict, index: int, key: str) -> dict:
    """Collect `key` from the `index`-th entry of a per-locale list."""
    return {f"{key}_{loc}": items[loc][index].get(key, "") for loc in LOCALES}


class Command(BaseCommand):
    help = "Import messages/*.json and src/data/*.ts content into the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be written, then roll back.",
        )

    def handle(self, *args, **options):
        if not SEED_FILE.exists():
            raise CommandError(
                f"{SEED_FILE} not found. Generate it first:\n"
                "  node --experimental-strip-types backend/seed/export_frontend_data.mjs"
            )

        data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
        messages = data["messages"]

        missing = [loc for loc in LOCALES if loc not in messages]
        if missing:
            raise CommandError(f"content.json is missing locales: {missing}")

        try:
            with transaction.atomic():
                counts = {
                    "site settings": self._site(messages, data["socials"]),
                    "home content": self._home(messages),
                    "about content": self._about(messages),
                    "associations": self._associations(data["associations"]),
                    "services": self._services(messages),
                    "projects": self._projects(messages, data["projectLinks"]),
                    "partners": self._partners(messages),
                    "news": self._news(data["news"]),
                }

                if options["dry_run"]:
                    raise _DryRun()
        except _DryRun:
            self.stdout.write(self.style.WARNING("Dry run — rolled back."))

        for label, count in counts.items():
            self.stdout.write(f"  {label:<16} {count}")
        self.stdout.write(self.style.SUCCESS("Seed complete."))

    # -- site -------------------------------------------------------------

    def _site(self, messages: dict, socials: list) -> int:
        site = SiteSettings.load()
        for key in ("name", "short", "tagline", "description"):
            for field, value in tr(messages, "site", key).items():
                setattr(site, field, value)
        for field, value in tr(messages, "footer", "address").items():
            setattr(site, field.replace("address", "address"), value)
        site.email = messages["uz"]["footer"]["email"]
        site.phone = messages["uz"]["footer"]["phone"]
        site.save()

        for order, social in enumerate(socials):
            SocialLink.objects.update_or_create(
                platform=social["id"],
                defaults={"name": social["name"], "url": social["href"], "order": order},
            )
        return 1 + len(socials)

    # -- home -------------------------------------------------------------

    def _home(self, messages: dict) -> int:
        home = HomeContent.load()
        mapping = {
            "hero_badge": "heroBadge",
            "hero_title": "heroTitle",
            "hero_lead": "heroLead",
            "cta_primary": "ctaPrimary",
            "cta_secondary": "ctaSecondary",
            "about_title": "aboutTitle",
            "about_lead": "aboutLead",
            "assoc_title": "assocTitle",
            "assoc_lead": "assocLead",
            "services_title": "servicesTitle",
            "services_lead": "servicesLead",
            "projects_title": "projectsTitle",
            "projects_lead": "projectsLead",
            "news_title": "newsTitle",
            "news_lead": "newsLead",
            "cta_banner_title": "ctaBannerTitle",
            "cta_banner_lead": "ctaBannerLead",
            "cta_banner_btn": "ctaBannerBtn",
        }
        for field, value in tr_from(messages, "home", mapping).items():
            setattr(home, field, value)
        home.save()

        # Values mirror the current STATS constant in src/app/[locale]/page.tsx.
        stats = [
            ("20", "projects"),
            ("46", "associations"),
            ("15 000+", "members"),
            ("12", "years"),
        ]
        for order, (value, stat_key) in enumerate(stats):
            labels = {
                f"label_{loc}": messages[loc]["home"]["stats"][stat_key]
                for loc in LOCALES
            }
            Stat.objects.update_or_create(
                value=value, defaults={**labels, "order": order}
            )
        return 1 + len(stats)

    # -- about ------------------------------------------------------------

    def _about(self, messages: dict) -> int:
        about = AboutContent.load()
        mapping = {
            "title": "title",
            "lead": "lead",
            "intro_title": "introTitle",
            "intro": "intro",
            "principle": "principle",
            "intro_note": "introNote",
            "role_title": "roleTitle",
            "mission_section_title": "missionSectionTitle",
            "mission_section_lead": "missionSectionLead",
            "mission_title": "missionTitle",
            "mission": "mission",
            "goal_title": "goalTitle",
            "goal": "goal",
            "goal_note": "goalNote",
            "values_title": "valuesTitle",
            "values_lead": "valuesLead",
            "directions_title": "directionsTitle",
            "directions_lead": "directionsLead",
            "architecture_title": "architectureTitle",
            "architecture_lead": "architectureLead",
            "core_title": "coreTitle",
            "core_sub": "coreSub",
            "architecture_note": "architectureNote",
            "mechanism_title": "mechanismTitle",
            "mechanism_lead": "mechanismLead",
            "formula_title": "formulaTitle",
            "formula": "formula",
            "blocks_title": "blocksTitle",
            "blocks_lead": "blocksLead",
            "media_title": "mediaTitle",
            "media_lead": "mediaLead",
            "media_tagline": "mediaTagline",
            "media_summary": "mediaSummary",
            "partners_title": "partnersTitle",
            "partners_lead": "partnersLead",
            "value_title": "valueTitle",
            "value_lead": "valueLead",
            "roadmap_title": "roadmapTitle",
            "roadmap_lead": "roadmapLead",
            "kpi_title": "kpiTitle",
            "results_title": "resultsTitle",
            "motto": "motto",
            "slogan": "slogan",
        }
        for field, value in tr_from(messages, "about", mapping).items():
            setattr(about, field, value)
        about.save()

        written = 1
        written += self._list(messages, "highlights", Highlight, "value", ("label",))
        written += self._plain_list(messages, "role", StrategicRole, "text")
        written += self._simple_list(messages, "values", Value, ("title", "sub"))
        written += self._plain_list(messages, "directions", Direction, "name")
        written += self._simple_list(messages, "architecture", ArchitectureNode, ("title", "desc"))
        written += self._simple_list(messages, "mechanism", MechanismStep, ("title", "desc"))
        written += self._blocks(messages)
        written += self._simple_list(messages, "media", MediaFeature, ("title", "desc"))
        written += self._simple_list(messages, "valueItems", StakeholderValue, ("title", "desc"))
        written += self._simple_list(messages, "roadmap", RoadmapStage, ("period", "title", "desc"))
        written += self._simple_list(messages, "kpi", Kpi, ("value", "label"))
        written += self._simple_list(messages, "results", Result, ("title", "desc"))
        return written

    def _items(self, messages: dict, key: str, namespace: str = "about") -> dict:
        return {loc: messages[loc][namespace][key] for loc in LOCALES}

    def _simple_list(self, messages, key, model, fields) -> int:
        """Rebuild an ordered block list from a per-locale array of objects."""
        items = self._items(messages, key)
        model.objects.all().delete()
        for index in range(len(items["uz"])):
            values = {}
            for field in fields:
                values.update(tr_item(items, index, field))
            model.objects.create(order=index, **values)
        return len(items["uz"])

    def _plain_list(self, messages, key, model, field) -> int:
        """Rebuild an ordered block list from a per-locale array of strings."""
        items = self._items(messages, key)
        model.objects.all().delete()
        for index in range(len(items["uz"])):
            values = {f"{field}_{loc}": items[loc][index] for loc in LOCALES}
            model.objects.create(order=index, **values)
        return len(items["uz"])

    def _list(self, messages, key, model, plain_field, translated_fields) -> int:
        """Ordered blocks that mix one untranslated field with translated ones."""
        items = self._items(messages, key)
        model.objects.all().delete()
        for index in range(len(items["uz"])):
            values = {plain_field: items["uz"][index][plain_field]}
            for field in translated_fields:
                values.update(tr_item(items, index, field))
            model.objects.create(order=index, **values)
        return len(items["uz"])

    def _blocks(self, messages) -> int:
        items = self._items(messages, "blocks")
        for index in range(len(items["uz"])):
            entry = items["uz"][index]
            FunctionalBlock.objects.update_or_create(
                code=entry["code"],
                defaults={
                    "title": entry["title"],
                    "order": index,
                    **tr_item(items, index, "desc"),
                },
            )
        return len(items["uz"])

    # -- catalog ----------------------------------------------------------

    def _associations(self, associations: list) -> int:
        from catalog.models import slugify_name

        for order, entry in enumerate(associations):
            names = entry["name"]
            activity = entry.get("activity") or {}
            Association.objects.update_or_create(
                slug=slugify_name(names["en"]),
                defaults={
                    **{f"name_{loc}": names[loc] for loc in LOCALES},
                    **{f"activity_{loc}": activity.get(loc, "") for loc in LOCALES},
                    "chairman": entry.get("chairman") or "",
                    "phone": entry.get("phone") or "",
                    "order": order,
                    "is_published": True,
                },
            )
        return len(associations)

    def _services(self, messages: dict) -> int:
        items = self._items(messages, "items", namespace="services")
        for index in range(len(items["uz"])):
            Service.objects.update_or_create(
                icon=items["uz"][index]["icon"],
                name_uz=items["uz"][index]["name"],
                defaults={
                    **tr_item(items, index, "name"),
                    **tr_item(items, index, "desc"),
                    "order": index,
                },
            )
        return len(items["uz"])

    def _projects(self, messages: dict, project_links: dict) -> int:
        items = self._items(messages, "items", namespace="projects")
        for index in range(len(items["uz"])):
            name = items["uz"][index]["name"]
            Project.objects.update_or_create(
                name=name,
                defaults={
                    "icon": items["uz"][index]["icon"],
                    **tr_item(items, index, "desc"),
                    "url": project_links.get(name, ""),
                    "order": index,
                },
            )
        return len(items["uz"])

    def _partners(self, messages: dict) -> int:
        groups = self._items(messages, "partners")
        written = 0
        for index in range(len(groups["uz"])):
            group, _ = PartnerGroup.objects.update_or_create(
                title_uz=groups["uz"][index]["title"],
                defaults={
                    **tr_item(groups, index, "title"),
                    "order": index,
                },
            )
            group.partners.all().delete()
            for pos, name in enumerate(groups["uz"][index]["items"]):
                # Partner names differ per locale for ministries, agencies etc.
                overrides = {
                    f"name_{loc}": groups[loc][index]["items"][pos] for loc in LOCALES
                }
                Partner.objects.create(
                    group=group, name=name, order=pos, **overrides
                )
                written += 1
        return len(groups["uz"]) + written

    # -- news -------------------------------------------------------------

    def _news(self, articles: list) -> int:
        for entry in articles:
            Article.objects.update_or_create(
                slug=entry["slug"],
                defaults={
                    "published_on": entry["date"],
                    "icon": entry["icon"],
                    **{f"tag_{loc}": entry["tag"][loc] for loc in LOCALES},
                    **{f"title_{loc}": entry["title"][loc] for loc in LOCALES},
                    **{f"excerpt_{loc}": entry["excerpt"][loc] for loc in LOCALES},
                    **{
                        f"body_{loc}": "\n\n".join(p[loc] for p in entry["body"])
                        for loc in LOCALES
                    },
                    "is_published": True,
                },
            )
        return len(articles)


class _DryRun(Exception):
    """Signals the atomic block to roll back after a dry run."""
