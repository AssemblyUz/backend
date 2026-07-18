"""
Compile locale/*/LC_MESSAGES/django.po into the .mo files Django reads.

    python scripts/compile_messages.py

This exists because `manage.py compilemessages` shells out to GNU gettext's
`msgfmt`, which is not installed on Windows by default. polib is pure Python, so
this works everywhere. If you do have gettext, `manage.py compilemessages` is
equivalent and you can use it instead.

The .mo files are committed, so a deployment never needs gettext either.
Run this after editing any .po file.
"""

import pathlib
import sys

try:
    import polib
except ImportError:  # pragma: no cover - developer setup problem, not runtime
    sys.exit("polib is required: pip install polib")

LOCALE_DIR = pathlib.Path(__file__).resolve().parent.parent / "locale"


def main() -> int:
    po_files = sorted(LOCALE_DIR.glob("*/LC_MESSAGES/*.po"))
    if not po_files:
        print(f"No .po files under {LOCALE_DIR}")
        return 1

    for po_path in po_files:
        po = polib.pofile(str(po_path))
        mo_path = po_path.with_suffix(".mo")
        po.save_as_mofile(str(mo_path))

        untranslated = len(po.untranslated_entries())
        note = f"  ({untranslated} untranslated)" if untranslated else ""
        rel = po_path.relative_to(LOCALE_DIR.parent)
        print(f"  {rel} -> {mo_path.name}  {len(po)} entries{note}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
