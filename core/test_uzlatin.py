"""The reformed Uzbek alphabet: the converter, the save hook, the backfill."""

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from catalog.models import Association, Project
from core.uzlatin import to_legacy, to_new
from news.models import Article


class ToNewTests(SimpleTestCase):
    def test_replaces_the_four_digraphs(self):
        self.assertEqual(to_new("O'zbekiston"), "Õzbekiston")
        self.assertEqual(to_new("g'oya"), "ğoya")
        self.assertEqual(to_new("shahar"), "şahar")
        self.assertEqual(to_new("uchun"), "uçun")

    def test_accepts_every_apostrophe_people_type(self):
        for mark in "ʻʼ‘’'`´":
            with self.subTest(mark=mark):
                self.assertEqual(to_new(f"o{mark}zgarish"), "õzgariş")
                self.assertEqual(to_new(f"tog{mark}"), "toğ")

    def test_preserves_case(self):
        self.assertEqual(to_new("Shahar"), "Şahar")
        self.assertEqual(to_new("TOSHKENT"), "TOŞKENT")
        self.assertEqual(to_new("Chiqish"), "Çiqiş")
        self.assertEqual(to_new("YO'LI"), "YÕLI")
        self.assertEqual(to_new("G'oya"), "Ğoya")

    def test_is_idempotent(self):
        once = to_new("Bog'lanish uchun shu yerga o'ting. Is'hoq ta'lim oldi.")
        self.assertEqual(to_new(once), once)

    def test_tutuq_belgisi_is_not_a_letter_modifier(self):
        self.assertEqual(to_new("ta'lim"), "ta'lim")
        self.assertEqual(to_new("e'lon qilindi"), "e'lon qilindi")

    def test_separate_s_and_h_keep_their_apostrophe(self):
        # Dropping it would let the next save read the pair as "sh".
        self.assertEqual(to_new("Is'hoq"), "Is'hoq")

    def test_a_quoted_word_is_not_read_as_ending_in_g_modifier(self):
        self.assertEqual(to_new("'blog' sahifasi"), "'blog' sahifasi")
        self.assertEqual(to_new("tog' yo'li"), "toğ yõli")

    def test_morpheme_boundaries_are_still_converted(self):
        self.assertEqual(to_new("jamoatchilik"), "jamoatçilik")
        self.assertEqual(to_new("transchegaraviy"), "transçegaraviy")

    def test_foreign_words_keep_their_spelling(self):
        self.assertEqual(to_new("Hi China alyansi"), "Hi China alyansi")
        self.assertEqual(to_new("Public Partnership asosida"), "Public Partnership asosida")
        self.assertEqual(to_new("Network Commerce"), "Network Commerce")

    def test_links_addresses_and_handles_are_untouched(self):
        text = "Sayt: https://shahar.uz/yangiliklar/chop, pochta: shohruh@choyxona.uz, @toshkent_shahri"
        self.assertEqual(
            to_new(text),
            "Sayt: https://shahar.uz/yangiliklar/chop, poçta: shohruh@choyxona.uz, @toshkent_shahri",
        )

    def test_message_placeholders_are_untouched(self):
        self.assertEqual(to_new("{search} bo'yicha"), "{search} bõyiça")
        self.assertEqual(to_new("%(choice)s — o'zgartirish"), "%(choice)s — õzgartiriş")
        self.assertEqual(to_new("<chip>Bosh</chip>"), "<chip>Boş</chip>")

    def test_other_scripts_and_empty_input_pass_through(self):
        self.assertEqual(to_new("Ассоциация шахтёров"), "Ассоциация шахтёров")
        self.assertEqual(to_new(""), "")


class ToLegacyTests(SimpleTestCase):
    def test_restores_the_digraphs(self):
        self.assertEqual(to_legacy("Õzbekiston şahar uçun ğoya"), "Oʻzbekiston shahar uchun gʻoya")

    def test_capitalises_by_context(self):
        self.assertEqual(to_legacy("Şahar"), "Shahar")
        self.assertEqual(to_legacy("TOŞKENT"), "TOSHKENT")
        self.assertEqual(to_legacy("KENGAŞ"), "KENGASH")
        self.assertEqual(to_legacy("Çiqiş"), "Chiqish")

    def test_round_trips_through_to_new(self):
        text = "Yõnalişlar bõyiça Õzbekiston yoşlari uçun ğoyalar"
        self.assertEqual(to_new(to_legacy(text)), text)


class SaveHookTests(TestCase):
    def test_uzbek_fields_are_converted_on_save(self):
        article = Article.objects.create(
            slug="yangi-ozgarishlar",
            title_uz="Yangi o'zgarishlar",
            body_uz="Birinchi xatboshi.\n\nShu yerda ikkinchisi.",
        )
        article.refresh_from_db()
        self.assertEqual(article.title_uz, "Yangi õzgarişlar")
        self.assertEqual(article.body_uz, "Birinçi xatboşi.\n\nŞu yerda ikkinçisi.")

    def test_other_languages_and_shared_fields_are_left_alone(self):
        article = Article.objects.create(
            slug="chop-etish",
            title_uz="Chop etish",
            title_en="Publishing a chart",
            title_ru="Публикация",
        )
        article.refresh_from_db()
        self.assertEqual(article.slug, "chop-etish")
        self.assertEqual(article.title_en, "Publishing a chart")
        self.assertEqual(article.title_ru, "Публикация")

        project = Project.objects.create(icon="🎓", name="YOSHLAR KAPITALI 2030")
        project.refresh_from_db()
        self.assertEqual(project.name, "YOSHLAR KAPITALI 2030")

    def test_conversion_applies_on_update_too(self):
        association = Association.objects.create(name_en="Builders", name_uz="Quruvçilar")
        association.name_uz = "Quruvchilar uyushmasi"
        association.save()
        association.refresh_from_db()
        self.assertEqual(association.name_uz, "Quruvçilar uyuşmasi")


class AdminSearchTests(TestCase):
    """Editors type oʻ/sh; the stored text says õ/ş. Search must bridge that."""

    def setUp(self):
        user = User.objects.create_superuser("boss", "boss@assembly.uz", "pw-for-tests")
        self.client.force_login(user)
        Article.objects.create(slug="yoshlar", title_uz="O'zbekiston yoshlari", title_en="Youth")
        Article.objects.create(slug="other", title_uz="Boşqa maqola", title_en="Fish market")
        self.url = reverse("admin:news_article_changelist")

    def _slugs(self, query: str) -> set[str]:
        response = self.client.get(self.url, {"q": query})
        return {article.slug for article in response.context["cl"].result_list}

    def test_old_spelling_finds_stored_text(self):
        # Case is matched exactly here on purpose: the test database is SQLite,
        # whose LIKE only folds case for ASCII, so "õ" would not find "Õ".
        # PostgreSQL, which production runs on, folds both.
        self.assertEqual(self._slugs("O'zbekiston"), {"yoshlar"})
        self.assertEqual(self._slugs("yoshlari"), {"yoshlar"})

    def test_new_spelling_still_works(self):
        self.assertEqual(self._slugs("Õzbekiston"), {"yoshlar"})

    def test_other_languages_are_searched_as_typed(self):
        # "fish" converts to "fiş"; the English title must still be found.
        self.assertEqual(self._slugs("fish"), {"other"})


class ConvertCommandTests(TestCase):
    def _legacy_article(self) -> Article:
        article = Article.objects.create(slug="eski", title_en="Old")
        # update() bypasses the save hook, as rows written before it did.
        Article.objects.filter(pk=article.pk).update(
            title_uz="O'zbekiston yoshlari", excerpt_uz="Qisqacha"
        )
        return article

    def test_converts_existing_rows(self):
        article = self._legacy_article()
        out = StringIO()
        call_command("convert_uz_alphabet", stdout=out)
        article.refresh_from_db()
        self.assertEqual(article.title_uz, "Õzbekiston yoşlari")
        self.assertEqual(article.excerpt_uz, "Qisqaça")
        self.assertIn("1 rows, 2 fields", out.getvalue())

    def test_dry_run_writes_nothing(self):
        article = self._legacy_article()
        out = StringIO()
        call_command("convert_uz_alphabet", "--dry-run", stdout=out)
        article.refresh_from_db()
        self.assertEqual(article.title_uz, "O'zbekiston yoshlari")
        self.assertIn("Dry run", out.getvalue())

    def test_does_not_bump_updated_at(self):
        article = self._legacy_article()
        before = Article.objects.get(pk=article.pk).updated_at
        call_command("convert_uz_alphabet", stdout=StringIO())
        self.assertEqual(Article.objects.get(pk=article.pk).updated_at, before)

    def test_second_run_has_nothing_to_do(self):
        self._legacy_article()
        call_command("convert_uz_alphabet", stdout=StringIO())
        out = StringIO()
        call_command("convert_uz_alphabet", stdout=out)
        self.assertIn("Nothing to convert", out.getvalue())
