"""Re-fetch every source URL in data/raw/ and check each > quote appears verbatim.

Matching ignores case, whitespace and curly-vs-straight quotes/dashes. A quote
may contain "..." to mark an elision; each fragment must appear, in order.
The evidence string of a page-kind `source_date:` line is checked the same way.

    .venv/bin/python scripts/check_quotes.py [slug ...]
"""
import sys

from pagetext import FetchError, fetch_text, normalise
from raw_format import RAW_DIR, SOURCE_SECTIONS, parse_raw, parse_source_date


def quote_in_text(quote, text):
    pos = 0
    for frag in [f.strip() for f in normalise(quote).split("...") if f.strip()]:
        idx = text.find(frag, pos)
        if idx < 0:
            return False
        pos = idx + len(frag)
    return True


def main(slugs):
    paths = [RAW_DIR / f"{s}.md" for s in slugs] if slugs else sorted(RAW_DIR.glob("*.md"))
    cache, ok, bad, skipped = {}, 0, 0, 0
    for path in paths:
        parsed = parse_raw(path)
        for section in SOURCE_SECTIONS:
            for src in parsed.get(section, []):
                url = src["url"]
                if not url.startswith("http"):
                    continue
                if url not in cache:
                    try:
                        cache[url] = normalise(fetch_text(url)[1])
                    except FetchError as exc:
                        cache[url] = exc
                page = cache[url]
                quotes = list(src["quotes"])
                date = parse_source_date(src.get("source_date"))
                if date and date[1] == "page":
                    quotes.append(date[2])  # date evidence must be verbatim page text too
                for q in quotes:
                    label = f"{path.stem}/{section}"
                    if isinstance(page, FetchError):
                        skipped += 1
                        print(f"SKIP  {label}: {page} ({url})")
                    elif quote_in_text(q, page):
                        ok += 1
                    else:
                        bad += 1
                        print(f"MISS  {label}: {q[:80]!r} ({url})")
    print(f"\n{ok} matched, {bad} missing, {skipped} unverifiable")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
