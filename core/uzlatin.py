"""
Uzbek Latin spelling: the 1995 digraph alphabet and the reformed one.

The site publishes Uzbek in the reformed alphabet, where the four sounds the
1995 alphabet wrote with two characters each get a letter of their own:

    oʻ -> õ      gʻ -> ğ      sh -> ş      ch -> ç

`to_new()` is applied to every `*_uz` field as it is saved (see
`core.signals`), so an editor can keep typing "O'zbekiston" and "shahar" and the
site still reads "Õzbekiston" and "şahar". It is idempotent — text that is
already converted passes through unchanged — which is what makes running it on
every save safe.

`to_legacy()` goes the other way. Machine translation needs it: translation
services were trained on the 1995 spelling and read "şahar" poorly.

What is deliberately left alone
-------------------------------
* URLs (with or without a scheme), e-mail addresses, @handles, #hashtags, and
  message placeholders such as `{count}`,
  `%(name)s` and `<link>` — rewriting those breaks links and templates.
* Foreign words. Uzbek has no bare "c" and no "w", so a word containing either
  ("Commerce", "Network") is not Uzbek and keeps its spelling. Names that slip
  past that test ("Shell", "Chamber") are listed in `PROTECTED_WORDS`.
* "sʼh", where s and h are two separate sounds (Isʼhoq). The apostrophe stays,
  because dropping it would make the next pass read the pair as "sh".

The frontend does not convert anything; frontend/src/lib/uzLatin.ts only folds
both spellings together for search, so "shahar" still finds "şahar".
"""

from __future__ import annotations

import re

#: Every character people type for the oʻ/gʻ modifier or the tutuq belgisi.
APOSTROPHES = "ʻʼ‘’'`´"

#: Foreign names and terms that contain "sh"/"ch" but are not Uzbek words, so
#: must keep their spelling. Compared case-insensitively against whole words.
PROTECTED_WORDS = frozenset(
    {
        "bosch",
        "chamber",
        "channel",
        "charitable",
        "charity",
        "chat",
        "chevron",
        "china",
        "chrome",
        "dashboard",
        "deutsche",
        "fintech",
        "launch",
        "marshall",
        "research",
        "school",
        "share",
        "shell",
        "shop",
        "show",
        "tech",
        "technology",
        "technologies",
        "telegraph",
        "touch",
        "watch",
        "washington",
        "youtube",
        "shanghai",
        "french",
        "switch",
        "search",
        "church",
        "michigan",
        "chicago",
        "manchester",
        "cambridge",
        "leadership",
        "partnership",
        "membership",
        "fellowship",
        "scholarship",
        "shift",
        "shield",
        "cash",
        "push",
        "flash",
        "fresh",
        "fashion",
        "english",
        "british",
        "turkish",
        "polish",
        "publishing",
        "shipping",
        "shopping",
        "exchange",
        "merchant",
        "machine",
        "architect",
        "architecture",
        "scheme",
        "schneider",
        "chain",
        "challenge",
        "champion",
        "change",
        "charge",
        "chart",
        "check",
        "chief",
        "child",
        "choice",
        "coach",
        "each",
        "much",
        "rich",
        "such",
        "teach",
        "which",
        "shanxi",
        "hitachi",
        "toshiba",
        "mitsubishi",
        "porsche",
        "roche",
        "tashkent",
    }
)

# Spans that are never prose: links, addresses, handles, template placeholders.
_SKIP = re.compile(
    r"https?://\S+"
    r"|www\.\S+"
    r"|[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
    r"|(?<!\w)[@#]\w+"
    # Scheme-less links: t.me/chorsu, toshkent.uz. The last label must be
    # lower-case ASCII, which keeps initials ("U.Shodiyev") out of this.
    r"|(?<![\w@.])(?:[A-Za-z0-9-]+\.)+[a-z]{2,}(?!\w)(?:/\S*)?"
    r"|\{[^{}]*\}"
    r"|</?[A-Za-z][^<>]*>"
    r"|%\([^)]*\)[a-z]"
    r"|%[sd]"
    r"|&#?\w+;"
)

_LATIN = "A-Za-zÀ-ÖØ-öø-ɏ"
_WORD = re.compile(rf"[{_LATIN}{APOSTROPHES}]+")

# A bare "c" (not part of "ch") or a "w" marks a word as not Uzbek.
_FOREIGN = re.compile(r"c(?!h)|w", re.IGNORECASE)

_O_MOD = re.compile(rf"([oO])[{APOSTROPHES}](?=[{_LATIN}])")
_G_MOD = re.compile(rf"([gG])[{APOSTROPHES}]")
_S_H = re.compile(rf"[sS][{APOSTROPHES}][hH]")
_DIGRAPH = re.compile(r"[sScC][hH]")

_NEW_LETTER = {"o": "õ", "O": "Õ", "g": "ğ", "G": "Ğ"}
_DIGRAPH_LETTER = {"s": "ş", "S": "Ş", "c": "ç", "C": "Ç"}


def _is_foreign(word: str) -> bool:
    bare = word.strip(APOSTROPHES).lower()
    return bare in PROTECTED_WORDS or bool(_FOREIGN.search(bare))


def _split_quotes(word: str) -> tuple[str, str, str]:
    """
    Peel wrapping quote marks off a word: 'bog' is the word "bog" in quotes,
    not "boğ". Only a word quoted on *both* sides is treated this way, so a
    bare trailing mark (tog', bog') still reads as gʻ.
    """
    if len(word) > 2 and word[0] in APOSTROPHES and word[-1] in APOSTROPHES:
        return word[0], word[1:-1], word[-1]
    return "", word, ""


def _convert_word(word: str) -> str:
    if _is_foreign(word):
        return word

    opening, core, closing = _split_quotes(word)

    # Shield sʼh before the digraph pass; the private-use character cannot
    # occur in real text, and restoring it keeps the apostrophe in place.
    shielded: list[str] = []

    def shield(match: re.Match[str]) -> str:
        shielded.append(match.group(0))
        return ""

    core = _S_H.sub(shield, core)
    core = _O_MOD.sub(lambda m: _NEW_LETTER[m.group(1)], core)
    core = _G_MOD.sub(lambda m: _NEW_LETTER[m.group(1)], core)
    core = _DIGRAPH.sub(lambda m: _DIGRAPH_LETTER[m.group(0)[0]], core)

    restored = iter(shielded)
    core = re.sub("", lambda _m: next(restored), core)
    return f"{opening}{core}{closing}"


def to_new(text: str) -> str:
    """Rewrite 1995-alphabet Uzbek (oʻ gʻ sh ch) as reformed (õ ğ ş ç)."""
    if not text:
        return text

    out: list[str] = []
    position = 0
    for skip in _SKIP.finditer(text):
        out.append(_WORD.sub(lambda m: _convert_word(m.group(0)), text[position : skip.start()]))
        out.append(skip.group(0))
        position = skip.end()
    out.append(_WORD.sub(lambda m: _convert_word(m.group(0)), text[position:]))
    return "".join(out)


_LEGACY_LOWER = {"õ": "oʻ", "ğ": "gʻ", "ş": "sh", "ç": "ch"}
_LEGACY_UPPER = {"Õ": "Oʻ", "Ğ": "Gʻ", "Ş": "Sh", "Ç": "Ch"}
_NEW_LETTERS = re.compile("[õğşçÕĞŞÇ]")


def to_legacy(text: str) -> str:
    """
    Rewrite reformed Uzbek back into the 1995 alphabet.

    An upper-case letter becomes "SH" inside an all-caps word and "Sh"
    otherwise, judged by its neighbour: TOŞKENT -> TOSHKENT, Şahar -> Shahar.
    """
    if not text:
        return text

    def replace(match: re.Match[str]) -> str:
        letter = match.group(0)
        if letter in _LEGACY_LOWER:
            return _LEGACY_LOWER[letter]
        expanded = _LEGACY_UPPER[letter]
        following = text[match.end() : match.end() + 1]
        preceding = text[match.start() - 1 : match.start()] if match.start() else ""
        neighbour = following if following.isalpha() else preceding
        return expanded.upper() if neighbour.isalpha() and neighbour.isupper() else expanded

    return _NEW_LETTERS.sub(replace, text)
