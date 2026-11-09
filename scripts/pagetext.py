"""Fetch a web page and return its visible text, whitespace-normalised.

Used both to read sources during collection (so excerpts are copied from the
real page text, not a model summary) and by check_quotes.py to verify them.

    .venv/bin/python scripts/pagetext.py <url> [out_file]
"""
import re
import sys
import unicodedata

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


class FetchError(Exception):
    pass


def fetch_text(url, timeout=30):
    """Return (status, text). Raises FetchError for non-HTML or failed requests."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
    except requests.RequestException as exc:
        raise FetchError(f"request failed: {exc}")
    if resp.status_code >= 400:
        raise FetchError(f"HTTP {resp.status_code}")
    ctype = resp.headers.get("Content-Type", "")
    if "html" not in ctype and "text" not in ctype:
        raise FetchError(f"unsupported content type: {ctype}")
    # requests falls back to ISO-8859-1 when the header has no charset, which
    # garbles UTF-8 curly quotes; pass bytes so bs4 can use the <meta> charset.
    if "charset" in ctype.lower():
        soup = BeautifulSoup(resp.text, "html.parser")
    else:
        soup = BeautifulSoup(resp.content, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [re.sub(r"[ \t\xa0]+", " ", ln).strip() for ln in text.splitlines()]
    return resp.status_code, "\n".join(ln for ln in lines if ln)


def normalise(text):
    """Canonical form for quote matching: unify quotes/dashes, collapse whitespace, lowercase."""
    text = unicodedata.normalize("NFKC", text)
    for a, b in (("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'),
                 ("–", "-"), ("—", "-"), ("…", "...")):
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip().lower()


if __name__ == "__main__":
    status, text = fetch_text(sys.argv[1])
    if len(sys.argv) > 2:
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(text)
        print(f"HTTP {status}, {len(text)} chars -> {sys.argv[2]}")
    else:
        print(text)
