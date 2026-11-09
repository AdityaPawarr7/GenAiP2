"""Phase 3 acceptance tests: findings dashboard (specs/phase-3-findings-dashboard.md, AC3.1-AC3.4).

The browser tests serve docs/ over a local HTTP server and drive headless Chromium
with Playwright. Chart.js 4.4.1 is vendored in docs/assets/vendor/ (Adi, Phase 3 review), so the
page and these tests make no network requests outside the local server.
Extra tests (marked "extra" in the docstring) cover the data-prep script that adds
source links to docs/data/policies.json, the headline tiles, and the theme toggle.
"""
import functools
import http.server
import json
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_dashboard_data  # noqa: E402
from raw_format import RAW_DIR, SOURCE_SECTIONS, parse_raw  # noqa: E402

DOCS = ROOT / "docs"
FINDINGS = json.loads((DOCS / "data" / "findings.json").read_text(encoding="utf-8"))
DOCS_POLICIES = json.loads((DOCS / "data" / "policies.json").read_text(encoding="utf-8"))
PROCESSED = json.loads((ROOT / "data" / "processed" / "policies.json").read_text(encoding="utf-8"))
N = FINDINGS["n"]

sync_api = pytest.importorskip("playwright.sync_api")


# ---------- data prep (extra) ----------

def test_dashboard_policies_json_is_up_to_date_with_build_script():
    """extra: docs/data/policies.json equals a fresh run of scripts/build_dashboard_data.py."""
    assert DOCS_POLICIES == json.loads(json.dumps(build_dashboard_data.build(), ensure_ascii=False))


def test_dashboard_policies_keeps_every_coded_field_unchanged():
    """extra: the dashboard copy carries the same codes as data/processed/policies.json."""
    by_slug = {r["slug"]: r for r in DOCS_POLICIES["records"]}
    assert len(by_slug) == len(PROCESSED) == N
    for p in PROCESSED:
        for k, v in p.items():
            assert by_slug[p["slug"]][k] == v, f"{p['slug']}.{k} differs"


@pytest.mark.parametrize("slug", [r["slug"] for r in PROCESSED])
def test_every_evidence_quote_has_a_source_link_from_the_raw_file(slug):
    """extra: each evidence item links to the URL source in data/raw whose quote contains it (never notes)."""
    rec = next(r for r in DOCS_POLICIES["records"] if r["slug"] == slug)
    raw = parse_raw(RAW_DIR / f"{slug}.md")
    assert {e["key"] for e in rec["evidence_sources"]} == set(rec["evidence"])
    for e in rec["evidence_sources"]:
        assert e["url"] and e["url"].startswith(("http://", "https://")), f"{e['key']} has no URL"
        assert e["section"] in SOURCE_SECTIONS
        assert e["evidence"] in e["quote"]
        source = [s for s in raw[e["section"]] if s["url"] == e["url"]]
        assert source and e["quote"] in source[0]["quotes"], f"{e['key']}: quote not under {e['url']}"


def test_method_facts_include_retrieval_date_and_agreement():
    """extra: retrieval date range and both agreement comparisons are available to the Method section."""
    assert DOCS_POLICIES["retrieved"]["min"] <= DOCS_POLICIES["retrieved"]["max"]
    ag = DOCS_POLICIES["agreement"]
    assert ag["human_vs_claude"]["n_institutions"] >= 1
    assert "cohens_kappa" in ag["human_vs_claude"]["fields"]["default_rule"]
    assert ag["ai2_vs_claude"]["n_institutions"] >= 1


# ---------- browser fixtures ----------

class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def base_url():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_QuietHandler, directory=str(DOCS)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}/findings.html"
    srv.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def open_page(browser, base_url, width=1280, scheme="light"):
    page = browser.new_page(viewport={"width": width, "height": 900}, color_scheme=scheme)
    page.errors = []
    page.on("console", lambda m: page.errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.goto(base_url)
    page.wait_for_selector("body[data-ready]")
    return page


@pytest.fixture(scope="module")
def page(browser, base_url):
    pg = open_page(browser, base_url)
    yield pg
    pg.close()


def chart_data(page, chart_id):
    return page.evaluate(
        """id => { const c = Chart.getChart(document.getElementById(id));
             return { labels: c.data.labels, datasets: c.data.datasets.map(d => ({ data: d.data, keys: d.keys, counts: d.counts || null, typeKey: d.typeKey || null })) }; }""",
        chart_id,
    )


def visible_rows(page):
    return page.locator("#rows tr.row").count()


# ---------- AC3.1 ----------

@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_ac3_1_page_loads_without_console_errors(browser, base_url, scheme):
    """AC3.1: findings.html loads with no console or page errors (light and dark color scheme)."""
    pg = open_page(browser, base_url, scheme=scheme)
    try:
        assert pg.evaluate("document.body.dataset.ready") == "true"
        assert pg.errors == []
    finally:
        pg.close()


def test_ac3_1_page_reads_only_findings_and_policies_json(browser, base_url):
    """AC3.1 (spec): the page fetches only data/findings.json and data/policies.json as data."""
    pg = browser.new_page()
    fetched = []
    pg.on("request", lambda r: fetched.append(r.url) if r.url.endswith(".json") else None)
    pg.goto(base_url)
    pg.wait_for_selector("body[data-ready]")
    pg.close()
    assert sorted(u.rsplit("/", 2)[-2] + "/" + u.rsplit("/", 1)[-1] for u in fetched) == ["data/findings.json", "data/policies.json"]


def test_ac3_1_page_loads_everything_locally_without_cdn(browser, base_url):
    """AC3.1 (Adi): every request stays on the local server; Chart.js comes from the vendored copy, not cdnjs."""
    pg = browser.new_page()
    urls = []
    pg.on("request", lambda r: urls.append(r.url))
    pg.goto(base_url)
    pg.wait_for_selector("body[data-ready]")
    version = pg.evaluate("Chart.version")
    pg.close()
    assert version == "4.4.1"
    assert [u for u in urls if not u.startswith(base_url.rsplit("/", 1)[0])] == []
    assert any(u.endswith("assets/vendor/chart-4.4.1.umd.js") for u in urls)


# ---------- AC3.2 ----------

def test_ac3_2_default_rule_chart_matches_findings(page):
    """AC3.2: default-rule bars equal findings.distributions.default_rule and total the institution count."""
    d = chart_data(page, "chart-default-rule")["datasets"][0]
    dist = FINDINGS["distributions"]["default_rule"]
    assert dict(zip(d["keys"], d["data"])) == {k: v for k, v in dist.items() if k in d["keys"]}
    assert sum(d["data"]) == N


def test_ac3_2_stance_chart_matches_findings(page):
    """AC3.2: stance bars (-2..+2) equal findings.distributions.stance and total the institution count."""
    d = chart_data(page, "chart-stance")["datasets"][0]
    assert d["keys"] == ["-2", "-1", "0", "1", "2"]
    assert dict(zip(d["keys"], d["data"])) == FINDINGS["distributions"]["stance"]
    assert sum(d["data"]) == N


def test_ac3_2_stance_by_type_chart_counts_match_crosstab(page):
    """AC3.2: each type's grouped stance counts equal the crosstab and sum to that type's n; percents agree."""
    cross = FINDINGS["crosstabs_by_type"]["stance"]
    datasets = chart_data(page, "chart-stance-type")["datasets"]
    assert [d["typeKey"] for d in datasets] == ["private_r1", "public_r1", "other"]
    for d in datasets:
        t = d["typeKey"]
        assert dict(zip(d["keys"], d["counts"])) == cross[t]
        assert sum(d["counts"]) == FINDINGS["n_by_type"][t]
        for c, pct in zip(d["counts"], d["data"]):
            assert abs(pct - 100 * c / FINDINGS["n_by_type"][t]) < 0.06
    assert sum(sum(d["counts"]) for d in datasets) == N


def test_ac3_2_stance_by_type_bars_are_labelled_with_their_school_count(page):
    """AC3.2 (Adi): every non-empty bar in "Tone by institution type" carries its count of schools (n)."""
    cross = FINDINGS["crosstabs_by_type"]["stance"]
    types = ["private_r1", "public_r1", "other"]
    keys = ["-2", "-1", "0", "1", "2"]
    labels = page.evaluate("Chart.getChart(document.getElementById('chart-stance-type')).$tipLabels")
    drawn = {(types[l["dataset"]], keys[l["index"]]): l["text"] for l in labels}
    expected = {(t, k): str(cross[t][k]) for t in types for k in keys if cross[t][k] > 0}
    assert drawn == expected


def test_ac3_2_stance_by_type_notes_other_group_is_too_small(page):
    """AC3.2 (Adi): the chart notes that Other (n=3) is too small to compare."""
    n_other = FINDINGS["n_by_type"]["other"]
    assert f"Other (n={n_other}) is too small to compare" in page.inner_text("#stance-type-note")


def test_ac3_2_se_course_chart_matches_findings(page):
    """AC3.2: SE-course bars equal findings.se_course.distribution (incl. not_found) and total the institution count."""
    d = chart_data(page, "chart-se")["datasets"][0]
    assert dict(zip(d["keys"], d["data"])) == FINDINGS["se_course"]["distribution"]
    assert sum(d["data"]) == N
    found = sum(v for k, v in zip(d["keys"], d["data"]) if k != "not_found")
    assert found == FINDINGS["se_course"]["n_with_policy"]


def test_ac3_2_integrated_se_callout_lists_every_integrated_course(page):
    """AC3.2: the "integrated" callout lists exactly the schools coded integrated in findings.se_course."""
    expected = [c["slug"] for c in FINDINGS["se_course"]["courses"] if c["policy"] == "integrated"]
    shown = page.eval_on_selector_all("#integrated-list li", "els => els.map(e => e.dataset.slug)")
    assert shown == expected
    assert len(shown) == FINDINGS["se_course"]["distribution"]["integrated"]


def test_ac3_2_theme_chart_matches_findings(page):
    """AC3.2: theme bars equal findings.themes.overall, sorted from most to least frequent."""
    d = chart_data(page, "chart-themes")["datasets"][0]
    assert dict(zip(d["keys"], d["data"])) == FINDINGS["themes"]["overall"]
    assert d["data"] == sorted(d["data"], reverse=True)


def test_ac3_2_headline_unit_grid_lights_the_dept_statement_schools(page):
    """AC3.2: the hero grid has one square per school and lights exactly the dept-statement schools."""
    assert page.locator("#unit-grid .unit").count() == N
    lit = page.eval_on_selector_all("#unit-grid .unit.on", "els => els.map(e => e.dataset.slug)")
    assert sorted(lit) == sorted(FINDINGS["dept_statement_finding"]["slugs"])
    assert page.inner_text("#dept-figure").replace(" ", "") == f"{len(lit)}/{N}"
    assert f"Only {len(lit)} of {N}" in page.inner_text("#headline")


def test_ac3_2_instructor_tile_shows_32_of_42_beside_the_headline(page):
    """AC3.2 (Adi): "Leave it to the instructor" shows instructor_discretion count/n (%) next to the 4/42 headline."""
    k = FINDINGS["distributions"]["default_rule"]["instructor_discretion"]
    text = page.inner_text("#hero-instructor")
    assert "Leave it to the instructor" in text
    assert f"{k}/ {N} ({round(100 * k / N)}%)" in page.inner_text("#instr-figure")
    # Same row as the dept headline: both panels are children of the hero grid.
    assert page.evaluate("document.getElementById('hero-instructor').parentElement === document.getElementById('hero-dept').parentElement")
    segs = page.eval_on_selector_all("#rule-seg span", "els => els.map(e => [e.dataset.rule, parseFloat(e.style.flexGrow)])")
    assert sum(v for _, v in segs) == N
    assert dict(segs)["instructor_discretion"] == k


def test_ac3_2_kpi_tiles_match_findings(page):
    """AC3.2: KPI tiles show institutions, % dept policy, % encourage AI and % collaboration framing from findings.json."""
    def tile(kpi):
        return page.inner_text(f'[data-kpi="{kpi}"] .value')
    pct = lambda c: f"{round(100 * c / N)}%"  # noqa: E731
    assert tile("institutions") == str(N)
    assert tile("dept_policy") == pct(FINDINGS["dept_statement_finding"]["count"])
    assert tile("encourage") == pct(FINDINGS["distributions"]["default_rule"]["allowed_encouraged"])
    assert tile("collaboration") == pct(FINDINGS["collaboration_framing"]["count"])


# ---------- AC3.3 ----------

def reset_filters(page):
    page.fill("#q", "")
    for sel in ("#f-type", "#f-rule", "#f-se"):
        page.select_option(sel, "")


def test_ac3_3_table_has_one_row_per_institution(page):
    """AC3.3: the explorer table starts with one row per institution."""
    reset_filters(page)
    assert visible_rows(page) == N == len(DOCS_POLICIES["records"])
    assert page.inner_text("#count") == f"Showing {N} of {N} schools"


@pytest.mark.parametrize("query", ["carnegie", "university of california", "STATE", "tech", "zzz-no-match"])
def test_ac3_3_search_filters_rows_by_school_name(page, query):
    """AC3.3: search shows exactly the schools whose name (or slug) contains the query, case-insensitive."""
    reset_filters(page)
    page.fill("#q", query)
    expected = sorted(r["slug"] for r in DOCS_POLICIES["records"] if query.lower() in (r["name"] + " " + r["slug"]).lower())
    shown = sorted(page.eval_on_selector_all("#rows tr.row", "els => els.map(e => e.dataset.slug)"))
    assert shown == expected
    if not expected:
        assert "No schools match" in page.inner_text("#rows")


@pytest.mark.parametrize("select,field,source", [
    ("#f-type", "type", "n_by_type"),
    ("#f-rule", "default_rule", "default_rule"),
    ("#f-se", "se_course_policy", "se"),
])
def test_ac3_3_filters_match_findings_counts(page, select, field, source):
    """AC3.3: each filter option shows exactly as many rows as findings.json counts for that value."""
    counts = {"n_by_type": FINDINGS["n_by_type"], "default_rule": FINDINGS["distributions"]["default_rule"],
              "se": FINDINGS["se_course"]["distribution"]}[source]
    reset_filters(page)
    options = page.eval_on_selector_all(f"{select} option", "els => els.map(e => e.value).filter(Boolean)")
    assert options
    for value in options:
        page.select_option(select, value)
        assert visible_rows(page) == counts[value], f"{field}={value}"
    page.select_option(select, "")


def test_ac3_3_search_and_filter_combine(page):
    """AC3.3: search and a filter apply together (AND)."""
    reset_filters(page)
    page.fill("#q", "university")
    page.select_option("#f-type", "public_r1")
    expected = [r for r in DOCS_POLICIES["records"] if "university" in r["name"].lower() and r["type"] == "public_r1"]
    assert visible_rows(page) == len(expected)
    reset_filters(page)


def test_ac3_3_clicking_a_row_shows_evidence_quotes_with_source_links(page):
    """AC3.3 (spec view 6): clicking a row opens its evidence quotes, each with a link to its source URL."""
    reset_filters(page)
    rec = next(r for r in DOCS_POLICIES["records"] if r["slug"] == "cmu")
    page.click('#rows tr.row[data-slug="cmu"]')
    detail = page.locator('#rows tr[data-detail="cmu"]')
    assert detail.count() == 1
    assert detail.locator(".ev li").count() == len(rec["evidence_sources"])
    hrefs = detail.locator(".ev a").evaluate_all("els => els.map(e => e.href)")
    assert hrefs == [e["url"] for e in rec["evidence_sources"]]
    marks = detail.locator(".ev mark").all_inner_texts()
    assert marks == [e["evidence"] for e in rec["evidence_sources"]]
    page.click('#rows tr.row[data-slug="cmu"]')
    assert page.locator('#rows tr[data-detail="cmu"]').count() == 0


def test_ac3_3_hero_square_opens_that_school_in_the_explorer(page):
    """AC3.3 (extra): selecting a lit square in the hero grid opens that school's evidence in the table."""
    page.click('#unit-grid .unit[data-slug="umd"]')
    assert page.locator('#rows tr[data-detail="umd"]').count() == 1
    assert visible_rows(page) == N


# ---------- AC3.4 ----------

@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_ac3_4_no_horizontal_scroll_at_375px(browser, base_url, scheme):
    """AC3.4: at 375px width the page never scrolls sideways, including with a school's evidence open."""
    pg = open_page(browser, base_url, width=375, scheme=scheme)
    try:
        assert pg.evaluate("document.documentElement.scrollWidth") <= 375
        pg.click('#rows tr.row[data-slug="ncstate"]')
        assert pg.evaluate("document.documentElement.scrollWidth") <= 375
        assert pg.errors == []
    finally:
        pg.close()


# ---------- extras ----------

def test_theme_toggle_switches_and_recolors_charts(browser, base_url):
    """extra: the theme button switches light/dark and the charts re-render with the new palette."""
    pg = open_page(browser, base_url, scheme="light")
    try:
        before = pg.evaluate("Chart.getChart(document.getElementById('chart-default-rule')).data.datasets[0].backgroundColor")
        pg.click("#theme-btn")
        assert pg.evaluate("document.documentElement.dataset.theme") == "dark"
        after = pg.evaluate("Chart.getChart(document.getElementById('chart-default-rule')).data.datasets[0].backgroundColor")
        assert before != after
        assert pg.inner_text("#theme-btn") == "Light mode"
        assert pg.errors == []
    finally:
        pg.close()


def test_method_section_reports_sample_retrieval_date_and_kappa(page):
    """extra (spec view 7): Method shows the sample size, retrieval date and the human-agreement kappa table."""
    text = page.inner_text("#h-method + .method")
    assert f"{N} US computer science departments" in text
    assert DOCS_POLICIES["retrieved"]["max"] in text
    n_h = DOCS_POLICIES["agreement"]["human_vs_claude"]["n_institutions"]
    assert f"Human vs Claude (n={n_h})" in text
    assert "κ" in text
