"""Phase 4 acceptance tests: validation pipeline and dashboard (specs/phase-4-validation.md, AC4.1-AC4.4).

The pipeline (scripts/run_validation.py) runs this whole suite, so a few checks behave
differently inside a pipeline run (env VALIDATION_RUN=1): the check that the committed
tests.json matches the current test collection skips, because that run is the one
rewriting tests.json. Run plain `pytest` to apply it.
Browser tests serve docs/ locally and drive headless Chromium, like the Phase 3 tests.
Extra tests (marked "extra" in the docstring) cover the review log, KPIs, charts and layout.
"""
import functools
import http.server
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_validation as rv  # noqa: E402

DOCS = ROOT / "docs"
DATA = DOCS / "data"
TESTS_DIR = ROOT / "tests"
CANARY = TESTS_DIR / "test_phase4_canary.py"
CANARY_ID = "tests/test_phase4_canary.py::"
IN_PIPELINE = os.environ.get("VALIDATION_RUN") == "1"
REVIEW_FIELDS = {"id", "date", "phase", "actor", "reviewed", "method", "outcome", "notes", "acs", "progress_refs"}
TEST_FIELDS = {"id", "phase", "acceptance_criterion", "name", "file", "status", "duration", "message", "timestamp", "run_id"}


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def static_test_acs():
    """AC ids claimed by tests in tests/*.py, read from the source (test names and ac markers)."""
    found = set()
    for path in TESTS_DIR.glob("test_*.py"):
        src = path.read_text(encoding="utf-8")
        found |= {"AC%s.%s" % m for m in re.findall(r"^def test_[Aa][Cc](\d+)_(\d+)_", src, re.M)}
        found |= set(re.findall(r'@pytest\.mark\.ac\("(AC\d+\.\d+)"\)', src))
    return found


# ---------- AC4.1: every AC has a test or a manual review ----------

def test_AC4_1_every_enforced_acceptance_criterion_has_a_test_or_manual_review():
    """AC4.1: each AC of phases 0..ENFORCED_THROUGH_PHASE in specs/phase-*.md has a test (by name or marker) or a review in reviews.json."""
    reviewed = {ac for r in load("reviews.json") for ac in r["acs"]}
    tested = static_test_acs()
    missing = [a["id"] for a in rv.spec_acs() if a["enforced"] and a["id"] not in tested | reviewed]
    assert missing == [], f"ACs with no test and no manual review: {missing}"


def test_AC4_1_spec_parser_finds_every_ac_line_in_the_phase_specs():
    """AC4.1: the parser returns one entry per '- ACx.y' line across specs/phase-*.md, with unique ids."""
    lines = [l for p in (ROOT / "specs").glob("phase-*.md")
             for l in p.read_text(encoding="utf-8").splitlines() if re.match(r"^- AC\d+\.\d+", l.strip())]
    acs = rv.spec_acs()
    assert len(acs) == len(lines) > 0
    assert len({a["id"] for a in acs}) == len(acs)
    assert next(a for a in acs if a["id"] == "AC1.7")["manual"] is True


def test_AC4_1_coverage_check_flags_an_ac_with_no_test_and_no_review():
    """AC4.1: the coverage function reports an AC with neither a test nor a review as uncovered."""
    acs = [{"id": "AC9.1"}, {"id": "AC9.2"}, {"id": "AC9.3"}]
    tests = [{"id": "t::a", "acceptance_criterion": "AC9.1"}]
    reviews = [{"id": "R9", "acs": ["AC9.2"]}]
    cov = rv.coverage(acs, tests, reviews)
    assert cov["AC9.1"]["tests"] == ["t::a"]
    assert cov["AC9.2"]["reviews"] == ["R9"]
    assert cov["AC9.3"] == {"tests": [], "reviews": []}


def test_AC4_1_later_phase_acs_are_listed_as_planned_not_enforced():
    """AC4.1: ACs of phases after ENFORCED_THROUGH_PHASE are in acceptance_criteria.json with enforced=false (shown as planned)."""
    data = load("acceptance_criteria.json")
    assert data["enforced_through_phase"] == rv.ENFORCED_THROUGH_PHASE
    for a in data["acs"]:
        assert a["enforced"] == (a["phase"] <= rv.ENFORCED_THROUGH_PHASE), a["id"]
    assert any(not a["enforced"] for a in data["acs"])


def test_AC4_1_acceptance_criteria_json_is_up_to_date_with_specs():
    """AC4.1: docs/data/acceptance_criteria.json equals a fresh parse of specs/phase-*.md."""
    assert load("acceptance_criteria.json")["acs"] == rv.spec_acs()


def test_AC4_1_review_entries_have_required_fields_and_valid_actor():
    """AC4.1: every reviews.json entry has date, phase, actor (Adi, Claude-Cowork or Claude), what, method, outcome, notes, ACs."""
    reviews = load("reviews.json")
    assert len({r["id"] for r in reviews}) == len(reviews)
    known = {a["id"] for a in rv.spec_acs()}
    for r in reviews:
        assert set(r) == REVIEW_FIELDS, r["id"]
        assert r["actor"] in {"Adi", "Claude-Cowork", "Claude"}, r["id"]
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$", r["date"]), r["id"]
        assert r["reviewed"] and r["method"] and r["outcome"], r["id"]
        assert set(r["acs"]) <= known, r["id"]


def test_AC4_1_every_review_cites_a_real_progress_md_entry():
    """AC4.1: each review's progress_refs are log-entry prefixes that exist in PROGRESS.md (no invented reviews)."""
    progress = (ROOT / "PROGRESS.md").read_text(encoding="utf-8")
    for r in load("reviews.json"):
        assert r["progress_refs"], r["id"]
        for ref in r["progress_refs"]:
            assert "- " + ref in progress, f"{r['id']}: {ref} not in PROGRESS.md"
        hhmm = r["date"][11:16]
        assert any(hhmm in ref for ref in r["progress_refs"]), f"{r['id']}: date {hhmm} matches no cited entry"


def test_AC4_1_manual_ac_1_7_is_covered_by_adis_spot_check_review():
    """AC4.1: the manual AC1.7 quote spot check is covered by a review by Adi."""
    rev = [r for r in load("reviews.json") if "AC1.7" in r["acs"]]
    assert rev and all(r["actor"] == "Adi" for r in rev)
    assert "5/5" in rev[0]["outcome"]


def test_dashboard_agreement_json_matches_processed_agreement():
    """extra: docs/data/agreement.json is an exact copy of data/processed/agreement.json."""
    assert load("agreement.json") == json.loads((ROOT / "data" / "processed" / "agreement.json").read_text(encoding="utf-8"))


# ---------- AC4.2: tests.json matches the pytest run ----------

FIXTURE_SUITE = '''
import pytest

def test_AC9_1_passes():
    assert True

def test_AC9_2_fails():
    assert 1 + 1 == 3, "deliberate fixture failure"

@pytest.mark.skip(reason="fixture skip")
def test_AC9_3_skipped():
    pass

@pytest.mark.parametrize("x", [1, 2, 3])
def test_AC9_4_param(x):
    assert x != 2

@pytest.mark.ac("AC9.5")
def test_mapped_by_marker():
    assert True

def test_extra_without_ac():
    assert True
'''


@pytest.fixture(scope="module")
def fixture_run(tmp_path_factory):
    d = tmp_path_factory.mktemp("suite")
    (d / "conftest.py").write_text((TESTS_DIR / "conftest.py").read_text(encoding="utf-8"))
    (d / "test_phase9_fixture.py").write_text(FIXTURE_SUITE)
    out = d / "out"
    first, _ = rv.run(["test_phase9_fixture.py"], rootdir=d, out_dir=out, note="first")
    second, _ = rv.run(["test_phase9_fixture.py"], rootdir=d, out_dir=out)
    proc = subprocess.run([sys.executable, "-m", "pytest", "test_phase9_fixture.py", "-v", "-p", "no:cacheprovider", "--rootdir", str(d)],
                          cwd=str(d), capture_output=True, text=True)
    independent = dict(re.findall(r"^(\S+::\S+) (PASSED|FAILED|SKIPPED|ERROR)", proc.stdout, re.M))
    tests = json.loads((out / "tests.json").read_text(encoding="utf-8"))
    runs = json.loads((out / "test_runs.json").read_text(encoding="utf-8"))
    return {"first": first, "second": second, "tests": tests, "runs": runs, "independent": independent, "root": str(d.resolve())}


def test_AC4_2_pipeline_json_matches_an_independent_pytest_run_on_a_fixture_suite(fixture_run):
    """AC4.2: on a fixture suite (pass, fail, skip, parametrized), tests.json has the same tests and statuses as a separate `pytest -v` run."""
    ind = fixture_run["independent"]
    got = {t["id"]: t["status"].upper() for t in fixture_run["tests"]["tests"]}
    assert len(ind) == 8
    assert got == ind


def test_AC4_2_run_summary_counts_equal_the_per_test_statuses(fixture_run):
    """AC4.2: the run summary (total, passed, failed, skipped, pass rate) is computed from the per-test records."""
    s = fixture_run["tests"]["run"]
    assert (s["total"], s["passed"], s["failed"], s["errors"], s["skipped"]) == (8, 5, 2, 0, 1)
    assert s["pass_rate"] == round(5 / 7, 4)
    assert sorted(t.split("::")[1] for t in s["failed_tests"]) == ["test_AC9_2_fails", "test_AC9_4_param[2]"]


def test_AC4_2_failure_message_and_ac_mapping_are_recorded(fixture_run):
    """AC4.2: a failing test keeps its assertion message; ACs map from the test name or the ac marker; extras get none."""
    by_name = {t["name"]: t for t in fixture_run["tests"]["tests"]}
    assert "deliberate fixture failure" in by_name["test_AC9_2_fails"]["message"]
    assert by_name["test_AC9_4_param[3]"]["acceptance_criterion"] == "AC9.4"
    assert by_name["test_mapped_by_marker"]["acceptance_criterion"] == "AC9.5"
    assert by_name["test_extra_without_ac"]["acceptance_criterion"] is None
    assert all(t["phase"] == 9 for t in by_name.values())


def test_AC4_2_each_run_is_appended_to_the_history(fixture_run):
    """AC4.2: test_runs.json gains one summary per run, in order, with the run's note."""
    runs = fixture_run["runs"]
    assert [r["run_id"] for r in runs] == [fixture_run["first"]["run_id"], fixture_run["second"]["run_id"]]
    assert runs[0]["note"] == "first"
    assert runs[-1] == fixture_run["tests"]["run"]


def test_AC4_2_tests_json_records_have_all_spec_fields():
    """AC4.2: every tests.json record has id, phase, acceptance_criterion, name, file, status, duration, message, timestamp, run_id."""
    data = load("tests.json")
    for t in data["tests"]:
        assert set(t) == TEST_FIELDS, t["id"]
        assert t["status"] in {"passed", "failed", "error", "skipped"}
        assert t["run_id"] == data["run"]["run_id"] and t["timestamp"] == data["run"]["timestamp"]
        assert t["phase"] == int(re.search(r"test_phase(\d+)", t["file"]).group(1))


def test_AC4_2_failure_messages_use_repo_relative_paths(fixture_run):
    """AC4.2: failure messages never contain the absolute repo path (the site is published), in the fixture run and in tests.json."""
    assert not any(str(ROOT) in t["message"] for t in load("tests.json")["tests"])
    failing = [t for t in fixture_run["tests"]["tests"] if t["status"] == "failed"]
    assert failing and all("test_phase9_fixture.py" in t["message"] for t in failing)
    assert not any(fixture_run["root"] in t["message"] for t in failing)


def test_AC4_2_committed_tests_json_summary_equals_its_records_and_last_history_entry():
    """AC4.2: tests.json's run summary matches its own records and is the latest entry in test_runs.json."""
    data = load("tests.json")
    recount = rv.summarize(data["tests"], data["run"]["run_id"], data["run"]["timestamp"], data["run"]["duration"], data["run"]["note"])
    assert recount == data["run"]
    if not IN_PIPELINE:
        assert load("test_runs.json")[-1] == data["run"]


def test_AC4_2_committed_tests_json_matches_current_test_collection():
    """AC4.2: the test ids in tests.json are exactly what pytest collects now (skipped inside a pipeline run, which rewrites tests.json)."""
    if IN_PIPELINE:
        pytest.skip("inside run_validation.py: tests.json is being rewritten by this run")
    proc = subprocess.run([sys.executable, "-m", "pytest", "tests", "--collect-only", "-q", "-p", "no:cacheprovider"],
                          cwd=str(ROOT), capture_output=True, text=True)
    collected = {l for l in proc.stdout.splitlines() if "::" in l}
    assert collected, proc.stdout[-2000:]
    assert {t["id"] for t in load("tests.json")["tests"]} == collected


# ---------- AC4.4: canary ----------

def test_AC4_4_history_contains_a_canary_run_that_reported_the_failure():
    """AC4.4: test_runs.json has a run where the deliberately failing canary test was reported as failed."""
    if CANARY.exists():
        pytest.skip("canary step in progress: the canary run is being recorded now")
    canary_runs = [r for r in load("test_runs.json") if any(f.startswith(CANARY_ID) for f in r["failed_tests"])]
    assert canary_runs, "no run in the history reported the canary failure"
    assert canary_runs[0]["failed"] + canary_runs[0]["errors"] >= 1


def test_AC4_4_canary_test_was_removed_after_its_run():
    """AC4.4: the canary test file is gone, the latest tests.json does not contain it, and a later run is in the history."""
    if CANARY.exists():
        pytest.skip("canary step in progress: the canary run is being recorded now")
    runs = load("test_runs.json")
    idx = max(i for i, r in enumerate(runs) if any(f.startswith(CANARY_ID) for f in r["failed_tests"]))
    if not IN_PIPELINE:  # inside a pipeline run, this run is the later one and is appended after the tests finish
        assert idx < len(runs) - 1, "no run after the canary run"
    assert not any(t["id"].startswith(CANARY_ID) for t in load("tests.json")["tests"])


# ---------- browser fixtures ----------

sync_api = pytest.importorskip("playwright.sync_api")


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def base_url():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_QuietHandler, directory=str(DOCS)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}/validation.html"
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


@pytest.fixture
def fresh(page):
    page.click("#reset")
    page.evaluate("document.querySelectorAll('#rows tr.row[aria-expanded=\"true\"]').forEach(r => r.click())")
    return page


# Empty before the pipeline's first run, so collection never crashes.
TESTS = load("tests.json")["tests"] if (DATA / "tests.json").exists() else []


def shown_ids(page):
    return page.eval_on_selector_all("#rows tr.row", "rows => rows.map(r => r.dataset.id)")


def expect_rows(page, pred):
    want = sorted(t["id"] for t in TESTS if pred(t))
    assert sorted(shown_ids(page)) == want
    assert page.text_content("#count") == f"Showing {len(want)} of {len(TESTS)} tests"


# ---------- AC4.3: filters ----------

def test_validation_page_loads_without_console_errors(browser, base_url):
    """extra: validation.html loads with no console or page errors, in light and dark color schemes."""
    for scheme in ("light", "dark"):
        pg = open_page(browser, base_url, scheme=scheme)
        try:
            assert pg.evaluate("document.body.dataset.ready") == "true"
            assert pg.errors == []
        finally:
            pg.close()


def test_AC4_3_unfiltered_table_lists_every_test_in_tests_json(fresh):
    """AC4.3: with no filters, the table has one row per tests.json record."""
    expect_rows(fresh, lambda t: True)


@pytest.mark.parametrize("phase", sorted({int(re.search(r"(\d+)", f.name).group(1)) for f in TESTS_DIR.glob("test_phase*.py")}))
def test_AC4_3_phase_filter_shows_only_that_phases_tests(fresh, phase):
    """AC4.3: choosing a phase shows exactly the tests from that phase's test file."""
    fresh.select_option("#f-phase", str(phase))
    expect_rows(fresh, lambda t: t["phase"] == phase)


@pytest.mark.parametrize("status", ["passed", "failed", "skipped"])
def test_AC4_3_status_filter_shows_only_tests_with_that_status(fresh, status):
    """AC4.3: choosing a status shows exactly the tests with that status (an empty result shows the no-match message)."""
    fresh.select_option("#f-status", status)
    expect_rows(fresh, lambda t: t["status"] == status)
    if not any(t["status"] == status for t in TESTS):
        assert "No tests match" in fresh.text_content("#rows")


@pytest.mark.parametrize("ac", ["AC1.2", "AC2.4", "AC3.3", "AC4.3", "none"])
def test_AC4_3_ac_filter_shows_only_tests_mapped_to_that_ac(fresh, ac):
    """AC4.3: choosing an AC shows exactly its tests; 'No AC, extra' shows the tests with no AC."""
    fresh.select_option("#f-ac", ac)
    expect_rows(fresh, lambda t: t["acceptance_criterion"] == (None if ac == "none" else ac))


def test_AC4_3_search_matches_test_id_substring_case_insensitively(fresh):
    """AC4.3: typing in search keeps only tests whose id or message contains the text, ignoring case."""
    fresh.fill("#q", "KAPPA")
    expect_rows(fresh, lambda t: "kappa" in (t["id"] + " " + t["message"]).lower())
    fresh.fill("#q", "zzz-no-such-test")
    assert shown_ids(fresh) == []
    assert "No tests match" in fresh.text_content("#rows")


def test_AC4_3_filters_combine_and_reset_clears_them(fresh):
    """AC4.3: phase + status + AC + search narrow together (AND); Reset restores every row."""
    fresh.select_option("#f-phase", "2")
    fresh.select_option("#f-status", "passed")
    fresh.select_option("#f-ac", "AC2.2")
    fresh.fill("#q", "berkeley")
    expect_rows(fresh, lambda t: t["phase"] == 2 and t["status"] == "passed" and t["acceptance_criterion"] == "AC2.2" and "berkeley" in t["id"])
    fresh.click("#reset")
    expect_rows(fresh, lambda t: True)
    assert fresh.input_value("#f-phase") == fresh.input_value("#f-ac") == fresh.input_value("#q") == ""


def test_AC4_3_selecting_an_ac_in_the_coverage_matrix_filters_the_table(fresh):
    """AC4.3: selecting an AC row in the coverage matrix sets the AC filter to it."""
    fresh.click('#cov li.ac[data-ac="AC2.5"]')
    assert fresh.input_value("#f-ac") == "AC2.5"
    expect_rows(fresh, lambda t: t["acceptance_criterion"] == "AC2.5")


def test_AC4_3_row_expands_to_show_message_and_source_file(fresh):
    """AC4.3: selecting a test row opens its details with the source file and message; selecting again closes it."""
    t = next(x for x in TESTS if x["acceptance_criterion"] == "AC2.4")
    fresh.fill("#q", t["name"])
    row = fresh.locator(f'#rows tr.row[data-id="{t["id"]}"]')
    row.click()
    detail = fresh.locator("#rows tr.detail-row").first
    assert detail.is_visible()
    text = detail.text_content()
    assert t["file"] in text and t["id"] in text
    assert ("Passed, no message." in text) if t["status"] == "passed" else (t["message"][:40] in text)
    row.click()
    assert fresh.locator("#rows tr.detail-row").count() == 0


# ---------- extras: KPIs, charts, coverage, reviews, agreement, layout ----------

def test_kpis_equal_the_run_summary_in_tests_json(fresh):
    """extra: the Tests passed / Failing / Manual reviews tiles equal tests.json and reviews.json."""
    run = load("tests.json")["run"]
    val = lambda k: fresh.text_content(f'.kpi[data-kpi="{k}"] .value')
    assert val("passed").startswith(str(run["passed"])) and val("passed").endswith(str(run["passed"] + run["failed"] + run["errors"]))
    assert val("failed") == str(run["failed"] + run["errors"])
    assert val("reviews") == str(len(load("reviews.json")))


def test_pass_rate_chart_has_one_point_per_history_run(fresh):
    """extra: the pass-rate line has one point per test_runs.json entry, with the recorded pass rate."""
    runs = load("test_runs.json")
    if not runs:
        assert "No pipeline runs recorded yet" in fresh.text_content("#h-runs + .sub + .panel")
        return
    data = fresh.evaluate("Chart.getChart(document.getElementById('chart-runs')).data.datasets[0].data")
    assert data == [None if r["pass_rate"] is None else round(r["pass_rate"] * 100, 2) for r in runs]


def test_coverage_matrix_marks_acs_without_tests_in_red_and_later_phases_as_planned(fresh):
    """extra: every AC from the specs is in the matrix; uncovered ones get the red 'uncovered' class, and only planned phases have them."""
    acs = load("acceptance_criteria.json")["acs"]
    items = fresh.eval_on_selector_all("#cov li.ac", "els => els.map(e => [e.dataset.ac, e.dataset.status, e.className])")
    assert [i[0] for i in items] == [a["id"] for a in acs]
    enforced = {a["id"]: a["enforced"] for a in acs}
    for ac, status, cls in items:
        assert ("uncovered" in cls) == (status == "uncovered")
        if status == "uncovered":
            assert not enforced[ac], f"{ac} is enforced but uncovered"
    assert dict((i[0], i[1]) for i in items)["AC1.7"] == "manual"


def test_review_log_lists_every_review_with_actor(fresh):
    """extra: the review log shows each reviews.json entry with its actor and PROGRESS.md reference."""
    reviews = load("reviews.json")
    shown = fresh.eval_on_selector_all("#reviews li.review", "els => els.map(e => [e.id, e.dataset.actor])")
    assert sorted(shown) == sorted(["review-" + r["id"], r["actor"]] for r in reviews)


def test_agreement_panel_shows_kappas_and_the_keep_codes_decision(fresh):
    """extra: the agreement chart uses agreement.json percentages, and the note reports Adi's keep-codes decision and every stance/disclosure disagreement."""
    ag = load("agreement.json")
    h = ag["human_vs_claude"]
    ds = fresh.evaluate("Chart.getChart(document.getElementById('chart-agree')).data.datasets.map(d => d.data)")
    fields = ["policy_level", "default_rule", "stance", "collaboration_framing", "disclosure_required", "se_course_policy"]
    assert ds[0] == [round(h["fields"][f]["percent_agreement"] * 100) for f in fields]
    note = fresh.text_content("#agree-note")
    assert "all codes stay unchanged" in note and "%.2f" % h["fields"]["stance"]["weighted_kappa_linear"] in note
    want = [(d["slug"], d["field"]) for d in h["disagreements"] if d["field"] in ("stance", "disclosure_required")]
    got = fresh.eval_on_selector_all("#dis tbody tr", "els => els.map(e => [e.dataset.slug, e.dataset.field])")
    assert [tuple(g) for g in got] == want


def test_validation_page_has_no_horizontal_scroll_at_375px(browser, base_url):
    """extra: at 375px the page never scrolls sideways, including with a test's details open."""
    for scheme in ("light", "dark"):
        pg = open_page(browser, base_url, width=375, scheme=scheme)
        try:
            assert pg.evaluate("document.documentElement.scrollWidth") <= 375
            pg.locator("#rows tr.row").first.click()
            assert pg.evaluate("document.documentElement.scrollWidth") <= 375
            assert pg.errors == []
        finally:
            pg.close()


def test_validation_theme_toggle_recolors_charts(browser, base_url):
    """extra: the theme button switches light/dark and the agreement chart re-renders with the dark palette."""
    pg = open_page(browser, base_url, scheme="light")
    try:
        before = pg.evaluate("Chart.getChart(document.getElementById('chart-agree')).data.datasets[0].backgroundColor")
        pg.click("#theme-btn")
        after = pg.evaluate("Chart.getChart(document.getElementById('chart-agree')).data.datasets[0].backgroundColor")
        assert pg.evaluate("document.documentElement.dataset.theme") == "dark"
        assert (before, after) == ("#2a78d6", "#3987e5")
        assert pg.errors == []
    finally:
        pg.close()
