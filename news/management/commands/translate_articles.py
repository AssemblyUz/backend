"""
Fill in the missing translations of articles that already exist.

New articles are translated as they are saved, so this is for the ones written
before that existed, and for retrying any field a provider outage left empty.
"""

from django.core.management.base import BaseCommand

from news.models import Article
from news.translation import fill_missing_translations, pending_fields


class Command(BaseCommand):
    help = "Machine-translate the empty Russian and English fields of stored articles."

    def add_arguments(self, parser):
        parser.add_argument(
            "--slug",
            help="Translate one article instead of every article with a gap.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be translated without contacting the provider.",
        )

    def handle(self, *args, **options):
        articles = Article.objects.all().order_by("-published_on")
        if options["slug"]:
            articles = articles.filter(slug=options["slug"])
            if not articles.exists():
                self.stderr.write(f"No article with slug {options['slug']!r}.")
                return

        touched = 0
        for article in articles:
            pending = pending_fields(article)
            if not pending:
                continue

            summary = ", ".join(
                sorted({f"{source}->{target}" for _, source, target in pending})
            )
            if options["dry_run"]:
                self.stdout.write(f"{article.slug}: {len(pending)} fields ({summary})")
                continue

            filled = fill_missing_translations(article)
            if filled:
                touched += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{article.slug}: filled {len(filled)}/{len(pending)} fields ({summary})"
                    )
                )
            else:
                # fill_missing_translations swallows provider failures so that a
                # save never fails. Here there is no save to protect, so say it.
                self.stderr.write(
                    f"{article.slug}: nothing filled — the provider is unreachable "
                    f"or blocking. See the log for the reason."
                )

        if options["dry_run"]:
            self.stdout.write("Dry run: nothing was changed.")
        else:
            self.stdout.write(f"Done. {touched} article(s) updated.")
