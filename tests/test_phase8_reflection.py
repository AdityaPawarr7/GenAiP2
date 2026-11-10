"""Phase 8 tests: the reflection page (docs/reflection.html).

specs/phase-8-evaluation.md has no acceptance criteria (Adi writes the reflection), so every
test here is an "extra": the page loads cleanly, carries Adi's text, its side-note numbers equal
the data files, every outside source is one that was checked by hand, and every page links it.
"""
import functools
import http.server
import json
import re
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
PAGE = DOCS / "reflection.html"
HTML = PAGE.read_text(encoding="utf-8")

# Outside sources, each opened and its quoted sentence found in the page text on 2026-11-10.
VERIFIED_SOURCES = {
    "https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/",
    "https://code.claude.com/docs/en/best-practices",
    "https://claude.com/blog/improving-frontend-design-through-skills",
    "https://knowledge.wharton.upenn.edu/article/without-guardrails-generative-ai-can-harm-education/",
    "https://arxiv.org/abs/2405.17739",
    "https://www.media.mit.edu/publications/your-brain-on-chatgpt/",
}

# Distinctive phrases from each of Adi's five paragraphs and the closing line.
ADI_PHRASES = [
    "easy 2 hour sprint where I gather data",
    "detailed criteria resulted in Claude writing 700+ tests",
    "Claude does struggle a lot with browser use at times",
    "my UI ended up being pretty 'AI- like'",
    "either we need rethink the entire system of education or have guard rails in place",
    "With great power comes great responsibility",
]


def test_reflection_page_contains_all_of_adis_paragraphs_and_closing_line():
    """extra: each of Adi's five reflection paragraphs and the closing line appear on the page."""
    for phrase in ADI_PHRASES:
        assert phrase in HTML, phrase
    assert len(re.findall(r'data-para="\d"', HTML)) == 5


def test_reflection_external_links_are_only_hand_verified_sources():
    """extra: every outside link on the reflection page is in the hand-verified source list (no invented URLs)."""
    links = set(re.findall(r'href="(https?://[^"]+)"', HTML))
    assert links == VERIFIED_SOURCES


def test_every_dashboard_nav_links_to_the_reflection():
    """extra: index, findings, validation, timeline, tokens and reflection all have a Reflection link in the nav."""
    for name in ("index", "findings", "validation", "timeline", "tokens", "reflection"):
        html = (DOCS / f"{name}.html").read_text(encoding="utf-8")
        nav = html.split('<nav class="pages"')[1].split("</nav>")[0]
        assert 'href="reflection.html"' in nav, name


def test_readme_links_the_reflection_page():
    """extra: README.md lists the reflection page in its dashboard table."""
    assert "docs/reflection.html" in (ROOT / "README.md").read_text(encoding="utf-8")


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
    page.requests = []
    page.on("console", lambda m: page.errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.on("request", lambda r: page.requests.append(r.url))
    page.goto(url)
    page.wait_for_selector("body[data-ready]")
    return page


@pytest.mark.parametrize("scheme,width", [("light", 1280), ("dark", 1280), ("light", 375), ("dark", 375)])
def test_reflection_page_loads_without_errors_or_sideways_scroll(browser, base_url, scheme, width):
    """extra: reflection.html loads with no console errors in light and dark mode, and has no horizontal scroll at 375px."""
    pg = open_page(browser, base_url + "reflection.html", width=width, scheme=scheme)
    try:
        assert pg.errors == []
        assert pg.evaluate("document.documentElement.scrollWidth") <= width
        assert all(u.startswith(base_url) for u in pg.requests), "page fetched something off the local server"
    finally:
        pg.close()


def test_reflection_side_note_numbers_equal_the_data_files(browser, base_url):
    """extra: the side-note figures (tokens, tests, prompts, findings) equal values computed from docs/data/*.json."""
    K = json.loads((DOCS / "data/tokens.json").read_text())
    T = json.loads((DOCS / "data/tests.json").read_text())
    D = json.loads((DOCS / "data/timeline.json").read_text())
    F = json.loads((DOCS / "data/findings.json").read_text())
    tot = K["totals"]["total"]
    want = {
        "f-tokens": f"{round(tot / 1e6)}M",
        "f-p1": f"{round(100 * K['by_phase']['phase-1']['total'] / tot)}%",
        "f-val": f"{round(100 * K['by_activity']['running_validation']['total'] / tot)}%",
        "f-clears": str(K["counts"]["clears"]),
        "f-tests": str(T["run"]["total"]),
        "f-passed": str(T["run"]["passed"]),
        "f-extra": str(sum(1 for t in T["tests"] if not t["acceptance_criterion"])),
        "f-prompts": str(sum(1 for e in D["entries"] if e["actor"] == "Adi" and e["type"] == "prompt")),
        "f-dept": f"{F['dept_statement_finding']['count']} of {F['n']}",
        "f-instr": f"{F['distributions']['default_rule']['instructor_discretion']} of {F['n']}",
    }
    pg = open_page(browser, base_url + "reflection.html")
    try:
        got = {k: pg.text_content(f"#{k}") for k in want}
        assert got == want
    finally:
        pg.close()


def test_landing_page_has_a_reflection_card(browser, base_url):
    """extra: index.html has a Reflection card linking reflection.html, and still loads without errors."""
    pg = open_page(browser, base_url + "index.html")
    try:
        assert pg.get_attribute('.card[data-page="reflection"]', "href") == "reflection.html"
        assert pg.errors == []
    finally:
        pg.close()
