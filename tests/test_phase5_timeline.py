"""Phase 5 acceptance tests: contributions timeline (specs/phase-5-timeline.md, AC5.1-AC5.4).

Data tests run on the committed docs/data/timeline.json, on a fresh build from the current
logs/events.jsonl + PROGRESS.md + git log, and on small fixtures for the parsing rules
(hand-back relabeling, phase inference, hook-time authority, redaction).
Browser tests serve docs/ locally and drive headless Chromium, like the Phase 3 and 4 tests.
Extra tests (marked "extra" in the docstring) cover the role panel, KPIs, Q&A log and layout.
"""
import functools
import http.server
import json
import re
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_timeline as bt  # noqa: E402

DOCS = ROOT / "docs"
EVENTS = ROOT / "logs" / "events.jsonl"
COMMITTED = json.loads((DOCS / "data" / "timeline.json").read_text(encoding="utf-8"))
FRESH = bt.build(EVENTS.read_text(encoding="utf-8").splitlines(),
                 (ROOT / "PROGRESS.md").read_text(encoding="utf-8"), bt.git_commits())
ET = "-05:00"


def hook_prompts(through=None):
    """(events.jsonl line, ts) of every UserPromptSubmit, optionally up to a timestamp."""
    out = []
    for n, line in enumerate(EVENTS.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        e = json.loads(line)
        if e["event"] == "UserPromptSubmit" and (through is None or e["ts"] <= through):
            out.append(("events.jsonl:%d" % n, e["ts"]))
    return out


def ev(ts, event, **kw):
    return json.dumps(dict({"ts": "2026-11-09T%s%s" % (ts, ET), "event": event, "session_id": "s1"}, **kw))


FIXTURE_EVENTS = [
    ev("10:00:00", "SessionStart", source="startup"),
    ev("10:01:00", "UserPromptSubmit", actor="Adi", prompt="Read CLAUDE.md and specs/phase-2-analysis.md. Plan first."),
    ev("10:02:00", "Stop", actor="Claude", response="Here is the plan."),
    ev("10:03:20", "UserPromptSubmit", actor="Adi", prompt="go. Also note in specs/phase-5-timeline.md that hooks win."),
    ev("10:04:00", "UserPromptSubmit", actor="Adi", prompt='<agent-message from="a1">\n[Subagent hand-back] frame\n  Batch done: 3 schools.\n</agent-message>'),
    ev("10:04:30", "UserPromptSubmit", actor="Subagent", prompt="<task-notification>\n<summary>Monitor event: build</summary>\n</task-notification>"),
    ev("10:05:00", "Stop", actor="Claude", response="Done. Saved to /Users/someone/Library/x.txt, mail me at a.b@example.edu"),
    ev("10:06:00", "UserPromptSubmit", actor="Adi", prompt="Approved. Commit, then start Phase 7 early."),
    ev("10:07:00", "Stop", actor="Claude", response="Committed. Starting Phase 7."),
    ev("10:08:00", "SessionStart", source="clear", session_id="s2"),
]
FIXTURE_PROGRESS = """# PROGRESS.md
- [2026-11-09] [setup] [Adi] Chose the workflow.
- [2026-11-09 10:05 ET] [phase-2] [Adi] Said "go" on the Phase 2 plan.
- [2026-11-09 10:06 ET] [phase-2] [Claude] Built the thing.
- [2026-11-09 ET] [phase-2] [Claude-Cowork] Wrote a helper.
- [2026-11-09 10:06 ET] [phase-2] [Adi] Reviewed Phase 2. Flagged a stale handoff block.
"""
FIXTURE_COMMITS = [{"hash": "abc1234", "ts": "2026-11-09T10:06:30" + ET, "subject": "Phase 2: analysis", "files": 2,
                    "loc": {"code": {"added": 10, "deleted": 2}, "docs": {"added": 1, "deleted": 0},
                            "data": {"added": 0, "deleted": 0}, "logs": {"added": 5, "deleted": 0}}}]
FIX = bt.build(FIXTURE_EVENTS, FIXTURE_PROGRESS, FIXTURE_COMMITS)
FIX_BY_SRC = {e["source"]: e for e in FIX["entries"]}


# ---------- AC5.1: every prompt in events.jsonl appears ----------

def test_AC5_1_every_prompt_in_events_jsonl_appears_in_committed_timeline_json():
    """AC5.1: each UserPromptSubmit line of logs/events.jsonl up to the file's events_through time is an entry, at its hook time."""
    by_src = {e["source"]: e for e in COMMITTED["entries"]}
    want = hook_prompts(COMMITTED["events_through"])
    missing = [s for s, ts in want if s not in by_src or by_src[s]["ts"] != ts]
    assert want and missing == []


def test_AC5_1_fresh_build_includes_every_prompt_logged_so_far():
    """AC5.1: building from the current events.jsonl yields one prompt/hand-back/notification entry per UserPromptSubmit."""
    srcs = {e["source"] for e in FRESH["entries"] if e["type"] in ("prompt", "handback", "notification")}
    assert {s for s, _ in hook_prompts()} == srcs


def test_AC5_1_fixture_prompts_handbacks_and_notifications_are_all_kept():
    """AC5.1: on a fixture log, Adi's prompts, the hand-back and the notification all become entries."""
    types = [FIX_BY_SRC["events.jsonl:%d" % n]["type"] for n in (2, 4, 5, 6, 8)]
    assert types == ["prompt", "prompt", "handback", "notification", "prompt"]


def test_AC5_1_subagent_handbacks_are_labelled_subagent_even_when_logged_as_adi():
    """AC5.1: a prompt starting with "<agent-message" is actor Subagent, type handback, with the hook's label kept as relabeled_from."""
    e = FIX_BY_SRC["events.jsonl:5"]
    assert (e["actor"], e["type"], e["relabeled_from"]) == ("Subagent", "handback", "Adi")
    assert e["detail"] == "Batch done: 3 schools."
    real = [x for x in COMMITTED["entries"] if x.get("relabeled_from")]
    assert len(real) == 5 and all(x["actor"] == "Subagent" for x in real)


def test_AC5_1_only_agent_message_prompts_count_as_subagent_handbacks():
    """AC5.1: automatic <task-notification> prompts are actor System, not Subagent; no Adi prompt starts with "<"."""
    assert FIX_BY_SRC["events.jsonl:6"]["actor"] == "System"
    for e in COMMITTED["entries"]:
        if e["type"] == "handback":
            assert e["actor"] == "Subagent"
        if e["type"] == "prompt":
            assert e["actor"] == "Adi" and not e["detail"].lstrip().startswith("<agent-message")


# ---------- AC5.2: ISO-8601, sorted ----------

@pytest.mark.parametrize("name,data", [("committed", COMMITTED), ("fresh", FRESH), ("fixture", FIX)])
def test_AC5_2_every_timestamp_parses_as_iso8601_with_a_timezone(name, data):
    """AC5.2: every entry's ts parses with datetime.fromisoformat and carries a UTC offset."""
    for e in data["entries"]:
        assert datetime.fromisoformat(e["ts"]).utcoffset() is not None, e["id"]


@pytest.mark.parametrize("name,data", [("committed", COMMITTED), ("fresh", FRESH), ("fixture", FIX)])
def test_AC5_2_entries_are_sorted_by_timestamp(name, data):
    """AC5.2: entries are in non-decreasing time order, and ids follow that order."""
    ts = [datetime.fromisoformat(e["ts"]) for e in data["entries"]]
    assert ts == sorted(ts)
    assert [e["id"] for e in data["entries"]] == ["e%03d" % i for i in range(1, len(ts) + 1)]


def test_AC5_2_hook_timestamps_are_never_changed():
    """AC5.2: every hook entry keeps exactly the ts written in events.jsonl (hook times are authoritative)."""
    lines = EVENTS.read_text(encoding="utf-8").splitlines()
    for e in FRESH["entries"]:
        if e["ts_source"] == "hook":
            n = int(e["source"].split(":")[1])
            assert json.loads(lines[n - 1])["ts"] == e["ts"], e["source"]


def test_AC5_2_progress_entry_is_ordered_by_the_hook_time_of_the_prompt_it_records():
    """AC5.2: an [Adi] PROGRESS.md entry written at 10:05 is placed at its prompt's hook time (10:03:20) and keeps the written time."""
    e = FIX_BY_SRC["PROGRESS.md:3"]
    assert e["ts"] == "2026-11-09T10:03:20" + ET
    assert e["written"] == "2026-11-09 10:05 ET"
    assert FIX["entries"][[x["id"] for x in FIX["entries"]].index(e["prompt_ref"])]["source"] == "events.jsonl:4"


def test_AC5_2_date_only_progress_entries_follow_the_entry_above_them():
    """AC5.2: a date-only PROGRESS.md entry takes the time of the timed entry above it; one with none above sits at midnight."""
    assert FIX_BY_SRC["PROGRESS.md:5"]["ts"] == "2026-11-09T10:06:00" + ET
    assert FIX_BY_SRC["PROGRESS.md:2"]["ts"] == "2026-11-09T00:00:00" + ET
    assert {FIX_BY_SRC[s]["time_precision"] for s in ("PROGRESS.md:2", "PROGRESS.md:5")} == {"date"}


def test_AC5_2_real_adi_progress_entries_match_the_right_prompts():
    """AC5.2: spot checks on the real log: the batch-4 review, item-4 decision and AC1.7 spot check map to 16:39, 16:41 and 16:44 prompts."""
    by_id = {e["id"]: e for e in FRESH["entries"]}
    got = {}
    for e in FRESH["entries"]:
        if e["actor"] == "Adi" and e["ts_source"] == "hook (matched prompt)":
            got[e["detail"][:20]] = by_id[e["prompt_ref"]]["ts"][11:16]
    assert got["Reviewed batch 4: (1"] == "16:39"
    assert got["Item 4: keep the wil"] == "16:41"
    assert got["AC1.7 spot check: ma"] == "16:44"
    assert got["Approved the Phase 1"] == "15:11"
    assert "Reviewed and approved" not in got  # plan-mode approval: no prompt records it


# ---------- AC5.3: valid actor and phase ----------

@pytest.mark.parametrize("name,data", [("committed", COMMITTED), ("fresh", FRESH), ("fixture", FIX)])
def test_AC5_3_every_entry_has_a_valid_actor_phase_and_type(name, data):
    """AC5.3: actor in Adi|Claude|Claude-Cowork|Subagent|System, phase in setup|phase-0..8, type in the declared list."""
    for e in data["entries"]:
        assert e["actor"] in bt.ACTORS, e
        assert e["phase"] in bt.PHASES, e
        assert e["type"] in bt.TYPES, e
        assert e["summary"].strip(), e["id"]


def test_AC5_3_roles_appear_only_on_adi_entries_and_are_valid():
    """AC5.3: roles (decision, correction, review, data_work, direction) are only on Adi's PROGRESS.md entries."""
    for e in COMMITTED["entries"]:
        if "roles" in e:
            assert e["actor"] == "Adi" and e["ts_source"] != "hook", e["id"]
            assert set(e["roles"]) <= set(bt.ROLES)


def test_AC5_3_phase_is_inferred_from_the_spec_a_read_prompt_names():
    """AC5.3: "Read ... specs/phase-2" sets phase-2; naming specs/phase-5 in a non-Read prompt does not; "start Phase 7" switches after that prompt."""
    phases = [FIX_BY_SRC["events.jsonl:%d" % n]["phase"] for n in (2, 3, 4, 8, 9, 10)]
    assert phases == ["phase-2", "phase-2", "phase-2", "phase-2", "phase-7", "phase-7"]


def test_AC5_3_real_log_phases_follow_the_phase_sequence():
    """AC5.3: on the real log, first prompts per phase are the spec-read prompts, and Phase 7 starts after the Phase 4 approval."""
    first = {}
    for e in COMMITTED["entries"]:
        if e["type"] == "prompt":
            first.setdefault(e["phase"], e["detail"])
    for p in ("phase-0", "phase-1", "phase-2", "phase-3", "phase-4", "phase-5"):
        assert first[p].startswith("Read CLAUDE.md") and "specs/" + p in first[p], p
    assert first["phase-7"].startswith("A")  # the "A" (option A) reply after Phase 4 approval


def test_AC5_3_commit_actors_are_backed_by_evidence():
    """AC5.3: every commit in git log is an entry with an actor and a stated reason; Adi made 5060340, b7efb9d and c0c1ff1."""
    commits = {e["commit"]["hash"]: e for e in FRESH["entries"] if e["type"] == "commit"}
    log = subprocess.run(["git", "log", "--format=%h"], cwd=str(ROOT), capture_output=True, text=True).stdout.split()
    assert set(log) == set(commits)
    assert all(e["actor_evidence"] for e in commits.values())
    assert {h for h, e in commits.items() if e["actor"] == "Adi"} >= {"5060340", "b7efb9d", "c0c1ff1"}


def test_AC5_3_clear_events_are_adi_actions_with_a_phase():
    """AC5.3: each SessionStart with source=clear is a /clear entry by Adi; startup sessions are not entries."""
    clears = [e for e in FIX["entries"] if e["type"] == "clear"]
    assert len(clears) == 1 and clears[0]["actor"] == "Adi" and clears[0]["phase"] == "phase-7"
    assert "events.jsonl:1" not in FIX_BY_SRC


# ---------- data extras ----------

def test_timeline_json_contains_no_local_paths_or_email_addresses():
    """extra: the published file has no home or project path, scratchpad path, or email address."""
    raw = (DOCS / "data" / "timeline.json").read_text(encoding="utf-8")
    assert str(ROOT) not in raw and str(Path.home()) not in raw
    assert not re.search(r"/Users/|/private/tmp/|-Users-", raw)
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", raw)


def test_redaction_replaces_paths_and_emails_in_fixture_text():
    """extra: the fixture response's home path and email are replaced with placeholders."""
    e = FIX_BY_SRC["events.jsonl:7"]
    assert "/Users/" not in e["detail"] and "example.edu" not in e["detail"]
    assert "<home>" in e["detail"] and "<email>" in e["detail"]


def test_summary_counts_match_a_recount_of_the_entries():
    """extra: summary[phase].actors and .types equal counts over entries; LOC sums equal the commits' numstat totals."""
    for p, s in COMMITTED["summary"].items():
        es = [e for e in COMMITTED["entries"] if e["phase"] == p]
        for a in bt.ACTORS:
            assert s["actors"].get(a, 0) == sum(1 for e in es if e["actor"] == a)
        for t in bt.TYPES:
            assert s["types"].get(t, 0) == sum(1 for e in es if e["type"] == t)
        code = sum(e["commit"]["loc"]["code"]["added"] for e in es if e["type"] == "commit")
        assert s["loc"].get("code_added", 0) == code


def test_qa_pairs_cover_every_adi_prompt_once_with_same_session_replies():
    """extra: each Adi prompt is one Q&A pair; its turns are responses/hand-backs from the same session, after the prompt."""
    by_id = {e["id"]: e for e in COMMITTED["entries"]}
    prompts = [e["id"] for e in COMMITTED["entries"] if e["type"] == "prompt"]
    assert [q["prompt"] for q in COMMITTED["qa"]] == prompts
    for q in COMMITTED["qa"]:
        p = by_id[q["prompt"]]
        for t in q["turns"]:
            assert by_id[t]["session"] == p["session"] and by_id[t]["ts"] >= p["ts"]
            assert by_id[t]["type"] in ("response", "handback", "notification")


# ---------- browser (AC5.4) ----------

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


@pytest.fixture(scope="module")
def page(browser, base_url):
    pg = open_page(browser, base_url + "timeline.html")
    yield pg
    pg.close()


@pytest.fixture
def fresh(page):
    page.click("#reset")
    return page


def visible(page, attr):
    return page.eval_on_selector_all("#tl li.ev", "els => els.map(e => e.dataset.%s)" % attr)


ENTRIES = COMMITTED["entries"]


def test_AC5_4_page_loads_with_no_console_errors(page):
    """AC5.4: timeline.html reaches data-ready=true with no console errors or page errors."""
    assert page.get_attribute("body", "data-ready") == "true"
    assert page.errors == []


def test_AC5_4_unfiltered_timeline_lists_every_entry(fresh):
    """AC5.4: with no filters, one timeline row per entry in timeline.json, in file order."""
    ids = fresh.eval_on_selector_all("#tl li.ev", "els => els.map(e => e.id)")
    assert ids == [e["id"] for e in ENTRIES]
    assert fresh.text_content("#count") == f"Showing {len(ENTRIES)} of {len(ENTRIES)} entries"


@pytest.mark.parametrize("actor", ["Adi", "Claude", "Subagent"])
def test_AC5_4_actor_filter_shows_only_that_actor(fresh, actor):
    """AC5.4: choosing an actor leaves exactly that actor's entries."""
    fresh.select_option("#f-actor", actor)
    got = visible(fresh, "actor")
    assert got and set(got) == {actor} and len(got) == sum(1 for e in ENTRIES if e["actor"] == actor)


@pytest.mark.parametrize("phase", ["phase-1", "phase-4"])
def test_AC5_4_phase_filter_shows_only_that_phase(fresh, phase):
    """AC5.4: choosing a phase leaves exactly that phase's entries, under one phase divider."""
    fresh.select_option("#f-phase", phase)
    got = visible(fresh, "phase")
    assert got and set(got) == {phase} and len(got) == sum(1 for e in ENTRIES if e["phase"] == phase)
    assert fresh.eval_on_selector_all("#tl li.divider", "els => els.length") == 1


@pytest.mark.parametrize("typ", ["prompt", "handback", "commit"])
def test_AC5_4_type_filter_shows_only_that_type(fresh, typ):
    """AC5.4: choosing a type leaves exactly the entries of that type."""
    fresh.select_option("#f-type", typ)
    got = visible(fresh, "type")
    assert got and set(got) == {typ} and len(got) == sum(1 for e in ENTRIES if e["type"] == typ)


def test_AC5_4_role_filter_shows_adis_corrections(fresh):
    """AC5.4: the role filter "Adi: Correction" leaves only Adi entries tagged correction."""
    fresh.select_option("#f-role", "correction")
    ids = fresh.eval_on_selector_all("#tl li.ev", "els => els.map(e => e.id)")
    assert ids == [e["id"] for e in ENTRIES if "correction" in e.get("roles", [])] and ids


def test_AC5_4_filters_combine_and_reset_restores_everything(fresh):
    """AC5.4: actor + phase + search narrow together; an impossible combination shows the empty message; Reset restores all."""
    fresh.select_option("#f-actor", "Adi")
    fresh.select_option("#f-phase", "phase-1")
    fresh.fill("#q", "umich")
    n = len(visible(fresh, "actor"))
    want = [e for e in ENTRIES if e["actor"] == "Adi" and e["phase"] == "phase-1" and "umich" in (e["summary"] + " " + e["detail"]).lower()]
    assert n == len(want) > 0
    fresh.select_option("#f-type", "commit")
    assert visible(fresh, "actor") == [] and fresh.is_visible("#tl li.empty")
    fresh.click("#reset")
    assert len(visible(fresh, "actor")) == len(ENTRIES)


def test_AC5_4_qa_search_filters_prompt_pairs(fresh):
    """AC5.4: the Q&A search keeps only pairs whose prompt or replies contain the words; the phase filter narrows further."""
    total = len(COMMITTED["qa"])
    assert fresh.eval_on_selector_all("#qa li.qa-item", "els => els.length") == total
    fresh.fill("#qa-q", "playwright")
    n = fresh.eval_on_selector_all("#qa li.qa-item", "els => els.length")
    assert 0 < n < total
    fresh.select_option("#qa-phase", "phase-0")
    assert fresh.eval_on_selector_all("#qa li.qa-item", "els => els.length") == 0
    fresh.fill("#qa-q", "")
    fresh.select_option("#qa-phase", "")
    assert fresh.eval_on_selector_all("#qa li.qa-item", "els => els.length") == total


def test_adis_role_panel_lists_every_tagged_entry_per_role(page):
    """extra: the Decisions/Corrections/Reviews/Manual data work columns list exactly the Adi entries with that role."""
    for role in ("decision", "correction", "review", "data_work"):
        ids = page.eval_on_selector_all(f'.role[data-role="{role}"] li[data-id]', "els => els.map(e => e.dataset.id)")
        assert ids == [e["id"] for e in ENTRIES if role in e.get("roles", [])], role
        assert ids, role


def test_show_in_timeline_jumps_to_and_opens_the_entry(fresh):
    """extra: "Show in timeline" on a role item resets filters, opens the entry's details and highlights it."""
    fresh.select_option("#f-actor", "Claude")
    btn = fresh.query_selector('.role[data-role="data_work"] [data-goto]')
    target = btn.get_attribute("data-goto")
    btn.click()
    assert fresh.get_attribute("#" + target, "class").split().count("flash") == 1
    assert fresh.evaluate(f"document.querySelector('#{target} details').open") is True
    assert len(visible(fresh, "actor")) == len(ENTRIES)


def test_kpi_tiles_match_counts_in_timeline_json(page):
    """extra: prompt, decision, correction, review and data-work tiles equal counts from timeline.json."""
    def role(r):
        return sum(1 for e in ENTRIES if r in e.get("roles", []))
    want = {"prompts": sum(1 for e in ENTRIES if e["type"] == "prompt"), "decision": role("decision"),
            "correction": role("correction"), "review": role("review"), "data_work": role("data_work")}
    for k, v in want.items():
        assert page.text_content(f'[data-kpi="{k}"] .value') == str(v), k


def test_counts_table_totals_match_timeline_json(page):
    """extra: the counts table's total row for Adi's prompts and Claude's responses equals the JSON counts."""
    cells = page.eval_on_selector_all("#summary tfoot td", "els => els.map(e => e.textContent)")
    assert cells[1] == str(sum(1 for e in ENTRIES if e["type"] == "prompt"))
    assert cells[7] == str(sum(1 for e in ENTRIES if e["type"] == "response"))


def test_charts_render_one_bar_group_per_active_phase(page):
    """extra: the actor, prompt and LOC charts each have one label per phase with any entries."""
    active = [p for p, s in COMMITTED["summary"].items() if any(s["actors"].values())]
    for cid in ("chart-actors", "chart-prompts", "chart-loc"):
        n = page.evaluate(f"Chart.getChart(document.getElementById('{cid}')).data.labels.length")
        assert n == len(active), cid


def test_every_dashboard_nav_links_to_the_timeline(browser, base_url):
    """extra: index, findings, validation and timeline pages all have a Timeline link in the nav; the landing card links it."""
    for name in ("index.html", "findings.html", "validation.html", "timeline.html"):
        html = (DOCS / name).read_text(encoding="utf-8")
        nav = html.split('<nav class="pages"')[1].split("</nav>")[0]
        assert 'href="timeline.html"' in nav, name
    assert 'class="card" href="timeline.html"' in (DOCS / "index.html").read_text(encoding="utf-8")


def test_timeline_page_has_no_horizontal_scroll_at_375px(browser, base_url):
    """extra: at 375px the page never scrolls sideways."""
    pg = open_page(browser, base_url + "timeline.html", width=375)
    try:
        assert pg.evaluate("document.documentElement.scrollWidth") <= 375
        assert pg.errors == []
    finally:
        pg.close()


def test_theme_toggle_switches_to_dark_and_redraws_charts_without_errors(browser, base_url):
    """extra: the theme button sets data-theme=dark and the charts redraw with the dark Adi color."""
    pg = open_page(browser, base_url + "timeline.html")
    try:
        pg.evaluate("localStorage.removeItem('theme')")
        pg.click("#theme-btn")
        assert pg.get_attribute("html", "data-theme") == "dark"
        color = pg.evaluate("Chart.getChart(document.getElementById('chart-prompts')).data.datasets[0].backgroundColor")
        assert color.lower() == "#3987e5"
        assert pg.errors == []
        pg.evaluate("localStorage.removeItem('theme')")
    finally:
        pg.close()
