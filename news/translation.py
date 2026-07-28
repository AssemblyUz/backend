"""
Machine translation for article text, so an editor writes once and the site
reads in all three languages.

Without this, a Russian or English reader gets the Uzbek text: the public
serializers fall back to the default locale rather than showing an empty page.
That fallback stays as the safety net — this only ever *fills* empty fields, and
never touches anything a person typed.

Translation happens when an article is saved, not when a page is rendered. The
result is stored, so the site never depends on a translation service being up,
and a single article costs a handful of requests once instead of on every visit.

Provider
--------
`google-free` (the default) needs no credentials, which is why it is the default:
it is the endpoint Google's own web translator calls. That also makes it
unofficial — no guarantees, and a server IP can be rate-limited or blocked. It is
used here because Uzbek rules out the alternatives: LibreTranslate does not
support the language at all (51 languages, `uz` is not among them), and DeepL
does not either.

Setting TRANSLATE_API_KEY switches to Google's supported Cloud Translation API,
which is the same call with a key, a contract, and a bill. Nothing else changes.

A browser User-Agent is required on the keyless endpoint. Measured: without one
it answers 200 with an empty body, so every field silently stays untranslated.
"""

from __future__ import annotations

import html
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)

LOCALES = ("uz", "ru", "en")

#: Article fields that hold prose, in the order an editor reads them.
FIELDS = ("title", "tag", "excerpt", "body")

_TIMEOUT_SECONDS = 8

#: The keyless endpoint truncates very long input, so prose is sent in pieces.
#: Paragraphs are the natural seam: they are already separated in the stored
#: text, and translating one at a time keeps the blank lines exactly where the
#: editor put them.
_MAX_CHARS = 1200

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)

#: Enough concurrency to keep a save quick, few enough to look nothing like
#: abuse: a long article is a dozen or so short requests.
_MAX_WORKERS = 4


class TranslationUnavailable(RuntimeError):
    """The provider could not be reached, or answered with nothing usable."""


def _get(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "*/*"})
    with urlopen(request, timeout=_TIMEOUT_SECONDS) as response:  # noqa: S310 — fixed host
        return response.read()


def _translate_free(text: str, source: str, target: str) -> str:
    """One request to the endpoint Google's web translator uses."""
    query = urlencode(
        {"client": "gtx", "sl": source, "tl": target, "dt": "t", "q": text}
    )
    raw = _get(f"https://translate.googleapis.com/translate_a/single?{query}")
    if not raw:
        raise TranslationUnavailable("empty response (missing or rejected User-Agent?)")

    try:
        payload = json.loads(raw)
        # [[[translated, original, ...], [translated, original, ...], ...], ...]
        pieces = [piece[0] for piece in payload[0] if piece and piece[0]]
    except (ValueError, IndexError, TypeError) as exc:
        raise TranslationUnavailable(f"unexpected response shape: {exc}") from exc

    if not pieces:
        raise TranslationUnavailable("no translated text in response")
    return "".join(pieces)


def _translate_official(text: str, source: str, target: str) -> str:
    """The supported Cloud Translation API, used when a key is configured."""
    body = urlencode(
        {
            "key": settings.TRANSLATE_API_KEY,
            "q": text,
            "source": source,
            "target": target,
            "format": "text",
        }
    ).encode()
    request = Request(
        "https://translation.googleapis.com/language/translate/v2",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urlopen(request, timeout=_TIMEOUT_SECONDS) as response:  # noqa: S310
        payload = json.loads(response.read())

    try:
        # Returns HTML entities even with format=text, so &#39; must be decoded
        # or apostrophes reach the page as mojibake.
        return html.unescape(payload["data"]["translations"][0]["translatedText"])
    except (KeyError, IndexError, TypeError) as exc:
        raise TranslationUnavailable(f"unexpected response shape: {exc}") from exc


def _chunks(text: str) -> list[str]:
    """
    Split prose into pieces the provider will accept whole.

    Paragraphs first, and any single paragraph longer than the limit is split
    again at sentence ends, so no sentence is ever cut in half.
    """
    pieces: list[str] = []
    for paragraph in text.split("\n\n"):
        if len(paragraph) <= _MAX_CHARS:
            pieces.append(paragraph)
            continue

        current = ""
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
            if current and len(current) + len(sentence) + 1 > _MAX_CHARS:
                pieces.append(current)
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            pieces.append(current)
    return pieces


def translate(text: str, source: str, target: str) -> str:
    """
    `text` in `source`, rendered into `target`, with its paragraphs intact.

    Raises TranslationUnavailable rather than returning something partial: a
    half-translated article is worse than an untranslated one, because the
    fallback that would have shown the original no longer applies.
    """
    if not text.strip():
        return ""

    provider = _translate_official if settings.TRANSLATE_API_KEY else _translate_free
    paragraphs = text.split("\n\n")

    def render(paragraph: str) -> str:
        if not paragraph.strip():
            return paragraph
        return " ".join(provider(chunk, source, target) for chunk in _chunks(paragraph))

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        return "\n\n".join(pool.map(render, paragraphs))


def source_locale(article) -> str | None:
    """
    The language the article was actually written in.

    Whichever locale has a title, preferring Uzbek: an editor here writes Uzbek
    first, and the other two exist to be filled.
    """
    for locale in LOCALES:
        if getattr(article, f"title_{locale}").strip():
            return locale
    return None


def pending_fields(article) -> list[tuple[str, str, str]]:
    """
    The (field, source, target) triples this article still needs, in order.

    Separate from the filling itself so that reporting what *would* happen —
    `translate_articles --dry-run`, chiefly — cannot drift from what does. Note
    a gap is per field, not per locale: an article can have a Russian title and
    no Russian excerpt, which `Article.missing_translations` does not see because
    it only looks at titles.
    """
    source = source_locale(article)
    if source is None:
        return []

    pending = []
    for target in LOCALES:
        if target == source:
            continue
        for field in FIELDS:
            if not getattr(article, f"{field}_{source}").strip():
                continue
            # Anything already written stays written — this is a gap-filler, not
            # an overwriter. An editor's own wording always wins.
            if getattr(article, f"{field}_{target}").strip():
                continue
            pending.append((field, source, target))
    return pending


def fill_missing_translations(article) -> list[str]:
    """
    Fill this article's empty locale fields from the one it was written in.

    Returns the names of the fields that were written, so a caller can log or
    report what happened. Never raises: a translation service that is down or
    blocking must not stop an editor saving their work. Fields left empty simply
    fall back to the source language on the public site, as they did before.
    """
    filled: list[str] = []
    for field, source, target in pending_fields(article):
        try:
            setattr(article, f"{field}_{target}", translate(
                getattr(article, f"{field}_{source}"), source, target
            ))
        except (TranslationUnavailable, OSError) as exc:
            logger.warning(
                "Could not translate %s of %s from %s to %s: %s",
                field,
                article.slug,
                source,
                target,
                exc,
            )
            continue
        filled.append(f"{field}_{target}")

    if filled:
        article.save(update_fields=filled)
    return filled
