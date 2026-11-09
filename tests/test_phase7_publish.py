"""Phase 7 acceptance tests: publish (specs/phase-7-publish.md, AC7.1-AC7.2).

AC7.2 (links) runs offline on docs/. AC7.1 (live URL) needs the network, so it runs only
with CHECK_LIVE=1 (e.g. `CHECK_LIVE=1 pytest tests/test_phase7_publish.py`); it uses curl,
as the spec asks. Pages not built yet (timeline, tokens) are skipped, not failed.
Extra tests (marked "extra" in the docstring) cover the landing page.
"""
import functools
import http.server
import json
import os
import re
import subprocess
import threading
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
LIVE_URL = "https://adityapawarr7.github.io/GenAiP2/"
PAGES = ["index.html", "findings.html", "validation.html", "timeline.html", "tokens.html"]
HTML_FILES = sorted(DOCS.glob("*.html"))


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in ("href", "src") and v:
                self.links.append(v)


def relative_links(path):
    p = _Links()
    p.feed(path.read_text(encoding="utf-8"))
    return [l for l in p.links if not urlsplit(l).scheme and not l.startswith(("#", "//"))]


# ---------- AC7.2: every relative link resolves ----------

@pytest.mark.parametrize("page", HTML_FILES, ids=[p.name for p in HTML_FILES])
def test_AC7_2_every_relative_link_in_page_resolves_to_a_file(page):
    """AC7.2: each relative href/src in a docs/ page points to an existing file in docs/."""
    links = relative_links(page)
    assert links, f"{page.name} has no relative links"
    missing = [l for l in links if not (page.parent / urlsplit(l).path).is_file()]
    assert missing == [], f"{page.name}: broken links {missing}"


def test_AC7_2_every_data_file_fetched_by_page_scripts_exists():
    """AC7.2: each data/*.json path fetched by docs/assets/*.js exists in docs/data/."""
    paths = {m for js in (DOCS / "assets").glob("*.js") for m in re.findall(r'"(data/[\w./-]+\.json)"', js.read_text(encoding="utf-8"))}
    assert paths
    assert sorted(p for p in paths if not (DOCS / p).is_file()) == []


def test_AC7_2_link_checker_catches_a_broken_link(tmp_path):
    """AC7.2: the link parser reports a relative link to a missing file and ignores external and anchor links."""
    page = tmp_path / "x.html"
    page.write_text('<a href="nope.html">a</a><a href="https://example.com/">b</a><a href="#top">c</a><img src="img.png">')
    (tmp_path / "img.png").write_bytes(b"")
    links = relative_links(page)
    assert links == ["nope.html", "img.png"]
    assert [l for l in links if not (tmp_path / l).is_file()] == ["nope.html"]


def test_AC7_2_coming_soon_dashboards_are_not_linked_until_built():
    """AC7.2: the landing page does not link to timeline.html or tokens.html while they do not exist."""
    links = relative_links(DOCS / "index.html")
    for name in ("timeline.html", "tokens.html"):
        assert (name in links) == (DOCS / name).is_file()


def test_AC7_2_github_pages_serves_docs_without_jekyll():
    """AC7.2: docs/.nojekyll exists so GitHub Pages serves every file as is."""
    assert (DOCS / ".nojekyll").is_file()


# ---------- AC7.1: live URL returns 200 ----------

@pytest.mark.parametrize("page", PAGES)
def test_AC7_1_live_page_returns_http_200(page):
    """AC7.1: curl gets HTTP 200 for each page on the live GitHub Pages site (CHECK_LIVE=1 only; unbuilt pages skip)."""
    if os.environ.get("CHECK_LIVE") != "1":
        pytest.skip("live check runs only with CHECK_LIVE=1 (needs network)")
    if not (DOCS / page).is_file():
        pytest.skip(f"{page} not built yet")
    out = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-L", LIVE_URL + page],
                         capture_output=True, text=True, timeout=60)
    assert out.stdout == "200", f"{LIVE_URL + page} returned {out.stdout}"


# ---------- landing page (extra) ----------

def test_readme_links_the_live_site_and_every_built_dashboard():
    """extra: README.md links the landing page and each built dashboard page."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for page in ("findings.html", "validation.html", "index.html"):
        assert f"docs/{page}" in readme


sync_api = pytest.importorskip("playwright.sync_api")


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def base_url():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_QuietHandler, directory=str(DOCS)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}/"
    srv.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def open_page(browser, url, width=1280, scheme="light"):
    page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=scheme)
    page.errors = []
    page.on("console", lambda m: page.errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(url)
    page.wait_for_selector("body[data-ready]")
    return page


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_landing_page_loads_without_errors_and_fills_headline_numbers(browser, base_url, scheme):
    """extra: index.html loads with no console errors and its card figures equal findings.json and tests.json."""
    pg = open_page(browser, base_url + "index.html", scheme=scheme)
    try:
        assert pg.errors == []
        f = json.loads((DOCS / "data" / "findings.json").read_text(encoding="utf-8"))
        run = json.loads((DOCS / "data" / "tests.json").read_text(encoding="utf-8"))["run"]
        assert pg.text_content("#findings-figure") == f"{f['dept_statement_finding']['count']} of {f['n']}"
        failing = run["failed"] + run["errors"]
        want = f"{failing} of {run['total']} tests fail" if failing else f"{run['passed']} of {run['passed']} tests pass"
        assert pg.text_content("#validation-figure") == want
    finally:
        pg.close()


def test_landing_page_cards_link_live_dashboards_and_mark_the_rest_coming_soon(browser, base_url):
    """extra: Findings and Validation cards are links; Timeline and Tokens show "Coming soon" with no link."""
    pg = open_page(browser, base_url + "index.html")
    try:
        cards = pg.eval_on_selector_all(".card", "els => els.map(e => [e.dataset.page, e.tagName, e.getAttribute('href'), e.textContent])")
        by = {c[0]: c for c in cards}
        assert by["findings"][1:3] == ["A", "findings.html"]
        assert by["validation"][1:3] == ["A", "validation.html"]
        for k in ("timeline", "tokens"):
            assert by[k][1] == "DIV" and by[k][2] is None and "Coming soon" in by[k][3]
    finally:
        pg.close()


def test_landing_page_has_no_horizontal_scroll_at_375px(browser, base_url):
    """extra: at 375px the landing page never scrolls sideways."""
    pg = open_page(browser, base_url + "index.html", width=375)
    try:
        assert pg.evaluate("document.documentElement.scrollWidth") <= 375
    finally:
        pg.close()
