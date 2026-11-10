"""Phase 6 acceptance tests: token usage dashboard (specs/phase-6-tokens.md, AC6.1-AC6.4).

Data tests run on the committed docs/data/tokens.json, on small fixture transcripts written to a
temp folder (dedup, activity rules, phase and context maths), and, when this machine has the
Claude Code transcripts (~/.claude/projects/<project>), on an independent recount from them.
Browser tests serve docs/ locally and drive headless Chromium, like the Phase 3-5 tests.
Extra tests (marked "extra" in the docstring) cover the three questions the page must answer.
"""
import functools
import glob
import http.server
import json
import re
import sys
import threading
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import tokens as tk  # noqa: E402

DOCS = ROOT / "docs"
EVENTS = ROOT / "logs" / "events.jsonl"
TEXT = (DOCS / "data" / "tokens.json").read_text(encoding="utf-8")
COMMITTED = json.loads(TEXT)
TYPES = ["input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"]
HAVE_TRANSCRIPTS = tk.TRANSCRIPTS.is_dir()
needs_transcripts = pytest.mark.skipif(not HAVE_TRANSCRIPTS, reason="Claude Code transcripts are not on this machine")


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# ---------- fixture transcripts ----------
FAKE_ROOT = "/fake/project"


def asst(mid, t, usage, tools=(), cwd=FAKE_ROOT, side=False):
    content = [{"type": "tool_use", "name": n, "input": i} for n, i in tools] or [{"type": "text", "text": "ok"}]
    return {"type": "assistant", "timestamp": "2026-11-09T%sZ" % t, "cwd": cwd, "isSidechain": side,
            "message": {"id": mid, "model": "claude-opus-5-5", "usage": usage, "content": content}}


def user(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def u(i=0, o=0, cw=0, cr=0):
    return {"input_tokens": i, "output_tokens": o, "cache_creation_input_tokens": cw, "cache_read_input_tokens": cr,
            "cache_creation": {"ephemeral_5m_input_tokens": cw, "ephemeral_1h_input_tokens": 0}}


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


FIX_EVENTS = [json.dumps(e) for e in [
    {"ts": "2026-11-09T10:00:00-05:00", "event": "SessionStart", "session_id": "aaaaaaaa-1", "source": "startup"},
    {"ts": "2026-11-09T10:00:30-05:00", "event": "UserPromptSubmit", "session_id": "aaaaaaaa-1", "actor": "Adi",
     "prompt": "Read CLAUDE.md and specs/phase-1-data.md. Plan first."},
    {"ts": "2026-11-09T10:20:00-05:00", "event": "SessionStart", "session_id": "bbbbbbbb-2", "source": "clear"},
    {"ts": "2026-11-09T10:20:30-05:00", "event": "UserPromptSubmit", "session_id": "bbbbbbbb-2", "actor": "Adi",
     "prompt": "Read CLAUDE.md and specs/phase-2-analysis.md."},
    {"ts": "2026-11-09T10:40:00-05:00", "event": "PreCompact", "session_id": "bbbbbbbb-2", "trigger": "manual"},
    {"ts": "2026-11-09T10:40:20-05:00", "event": "SessionStart", "session_id": "bbbbbbbb-2", "source": "compact"},
]]


@pytest.fixture(scope="module")
def fix(tmp_path_factory):
    base = tmp_path_factory.mktemp("transcripts")
    # Session A (phase 1): a turn with reading then a web search; the same message id written 3 times
    # (streaming), the last copy carrying the final usage; one line from another project's cwd.
    write_jsonl(base / "aaaaaaaa-1.jsonl", [
        user("Read CLAUDE.md and specs/phase-1-data.md"),
        asst("m1", "15:01:00", u(i=3, o=10, cw=100, cr=1000), [("Read", {"file_path": FAKE_ROOT + "/SPEC.md"})]),
        asst("m2", "15:02:00", u(i=1, o=5, cw=0, cr=2000), [("WebSearch", {"query": "mit ai policy"})]),
        asst("m2", "15:02:00", u(i=1, o=20, cw=0, cr=2000)),
        asst("m2", "15:02:00", u(i=1, o=40, cw=0, cr=2000), [("Write", {"file_path": FAKE_ROOT + "/data/raw/mit.md"})]),
        asst("m3", "15:03:00", u(i=1, o=7, cw=50, cr=3000)),  # text only: inherits the previous label
        asst("zz", "15:03:30", u(i=999, o=999), cwd="/other/project"),
        user("go on"),
        asst("m4", "15:10:00", u(i=1, o=9, cw=10, cr=4000), [("Bash", {"command": ".venv/bin/pytest -q"})]),
        asst("m5", "15:11:00", u(i=1, o=9, cw=10, cr=5000), [("Bash", {"command": "cat >> PROGRESS.md <<EOF\nx\nEOF"})]),
    ])
    # A subagent of session A, which repeats m2 (must not be counted twice) and edits code.
    write_jsonl(base / "aaaaaaaa-1" / "subagents" / "agent-abc12345.jsonl", [
        user("Collect sources for MIT"),
        asst("m2", "15:02:00", u(i=1, o=40, cw=0, cr=2000), side=True),
        asst("s1", "15:05:00", u(i=2, o=30, cw=500, cr=6000), [("Bash", {"command": "curl -sL https://cs.mit.edu/ | head"})], side=True),
        asst("s2", "15:06:00", u(i=2, o=30, cw=0, cr=7000), [("Edit", {"file_path": FAKE_ROOT + "/scripts/x.py"})], side=True),
    ])
    (base / "aaaaaaaa-1" / "subagents" / "agent-abc12345.meta.json").write_text(json.dumps({"description": "Collect raw: mit, cmu", "agentType": "general-purpose"}))
    # Session B (phase 2, after the /clear): small context, then a compact.
    write_jsonl(base / "bbbbbbbb-2.jsonl", [
        user("Read CLAUDE.md and specs/phase-2-analysis.md"),
        asst("b1", "15:21:00", u(i=1, o=5, cw=100, cr=900), [("Write", {"file_path": FAKE_ROOT + "/data/processed/policies.json"})]),
        asst("b2", "15:30:00", u(i=1, o=5, cw=100, cr=8900)),
        asst("b3", "15:41:00", u(i=1, o=5, cw=100, cr=1900)),
    ])
    return tk.build(FIX_EVENTS, base=base, root=FAKE_ROOT)


def by_id(data):
    return {m["id"]: m for m in data["messages"]}


# ---------- AC6.1: totals equal an independent recount ----------

def independent_recount(through):
    """Recount from the raw transcripts without tokens.py: last usage per message id, this project's cwd only."""
    root, last = str(ROOT), {}
    files = glob.glob(str(tk.TRANSCRIPTS / "*.jsonl")) + glob.glob(str(tk.TRANSCRIPTS / "*" / "subagents" / "*.jsonl"))
    for f in sorted(files):
        for line in open(f, encoding="utf-8"):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            m = d.get("message") or {}
            if d.get("type") == "assistant" and m.get("usage") and m.get("id") and (d.get("cwd") or "").startswith(root):
                if ts(d["timestamp"]) <= through:
                    last[m["id"]] = m["usage"]
    return len(last), {t: sum(v.get(t, 0) or 0 for v in last.values()) for t in TYPES}


@needs_transcripts
def test_AC6_1_committed_totals_equal_independent_recount_from_raw_transcripts():
    """AC6.1: the four token totals in tokens.json equal a recount from the raw jsonl (up to transcripts_through)."""
    n, want = independent_recount(ts(COMMITTED["transcripts_through"]))
    assert COMMITTED["counts"]["messages"] == n
    for t in TYPES:
        assert COMMITTED["totals"][t] == want[t], t


def test_AC6_1_fixture_totals_match_hand_computed_sums(fix):
    """AC6.1: on fixture transcripts the totals equal the hand sum of each message's final usage (m2's last copy, no other-project line)."""
    want_out = 10 + 40 + 7 + 9 + 9 + 30 + 30 + 5 + 5 + 5
    want_read = 1000 + 2000 + 3000 + 4000 + 5000 + 6000 + 7000 + 900 + 8900 + 1900
    assert fix["totals"]["output_tokens"] == want_out
    assert fix["totals"]["cache_read_input_tokens"] == want_read
    assert fix["totals"]["input_tokens"] == 3 + 1 + 1 + 1 + 1 + 2 + 2 + 1 + 1 + 1


@pytest.mark.parametrize("group", ["by_phase", "by_activity", "by_session", "by_day", "by_thread"])
def test_AC6_1_every_aggregate_adds_up_to_the_totals(group):
    """AC6.1: each aggregate (phase, activity, session, day, thread) sums to the same four totals as the messages."""
    for t in TYPES + ["total", "messages"]:
        assert sum(v[t] for v in COMMITTED[group].values()) == COMMITTED["totals"][t], (group, t)
    assert abs(sum(v["cost_usd"] for v in COMMITTED[group].values()) - COMMITTED["totals"]["cost_usd"]) < 0.01


def test_AC6_1_totals_equal_the_sum_of_the_message_list():
    """AC6.1: totals equal the sum over the per-message records published in tokens.json."""
    for t in TYPES:
        assert sum(m[t] for m in COMMITTED["messages"]) == COMMITTED["totals"][t]
    assert len(COMMITTED["messages"]) == COMMITTED["counts"]["messages"]


def test_AC6_1_estimated_cost_uses_the_published_prices():
    """AC6.1 (extra): the cost of each fixture-style usage follows the stated $/M prices, incl. 5-minute vs 1-hour cache writes."""
    usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000, "cache_read_input_tokens": 1_000_000,
             "cache_creation_input_tokens": 2_000_000,
             "cache_creation": {"ephemeral_5m_input_tokens": 1_000_000, "ephemeral_1h_input_tokens": 1_000_000}}
    P = COMMITTED["pricing"]["usd_per_million"]
    assert tk.cost(usage) == pytest.approx(P["input"] + P["output"] + P["cache_read"] + P["cache_write_5m"] + P["cache_write_1h"])


# ---------- AC6.2: no duplicate message ids ----------

def test_AC6_2_committed_message_ids_are_unique():
    """AC6.2: every message id appears once in tokens.json."""
    ids = [m["id"] for m in COMMITTED["messages"]]
    assert len(ids) == len(set(ids))


def test_AC6_2_streamed_copies_count_once_with_their_final_usage(fix):
    """AC6.2: a message written as 3 lines (output 5, 20, 40) counts once, with output 40."""
    ids = [m["id"] for m in fix["messages"]]
    assert ids.count("m2") == 1
    assert by_id(fix)["m2"]["output_tokens"] == 40


def test_AC6_2_message_repeated_in_a_subagent_file_counts_once(fix):
    """AC6.2: an id present in both a main transcript and a subagent transcript is counted once, as the main thread's."""
    m2 = by_id(fix)["m2"]
    assert m2["thread"] == "main"
    assert fix["by_thread"]["subagent"]["messages"] == 2


def test_AC6_2_lines_from_other_projects_are_dropped(fix):
    """AC6.2 (extra): an assistant line whose cwd is another project is not counted."""
    assert "zz" not in by_id(fix)


# ---------- AC6.3: phase and activity on every message ----------

def test_AC6_3_every_committed_message_has_a_known_phase_and_activity():
    """AC6.3: each message in tokens.json carries a phase from the phase list and one of the five activities."""
    bad = [m["id"] for m in COMMITTED["messages"] if m["phase"] not in COMMITTED["phases"] or m["activity"] not in COMMITTED["activities"]]
    assert bad == []


def test_AC6_3_activity_rules_on_fixture(fix):
    """AC6.3: WebSearch → gathering; pytest → validation; PROGRESS.md append → planning; curl → gathering;
    Edit .py → code; Write data/processed → processing."""
    a = {k: v["activity"] for k, v in by_id(fix).items()}
    assert a["m2"] == "gathering_data"
    assert a["m4"] == "running_validation"
    assert a["m5"] == "planning_docs"
    assert a["s1"] == "gathering_data"
    assert a["s2"] == "writing_code"
    assert a["b1"] == "processing_data"


def test_AC6_3_unlabelled_calls_inherit_within_their_turn(fix):
    """AC6.3: a read-only call takes the next label in its turn (m1 → gathering); a trailing text-only call
    takes the previous one (m3, b2, b3)."""
    a = {k: v["activity"] for k, v in by_id(fix).items()}
    assert a["m1"] == "gathering_data"
    assert a["m3"] == "gathering_data"
    assert a["b2"] == a["b3"] == "processing_data"


@pytest.mark.parametrize("labels,want", [
    ([None, None], ["planning_docs", "planning_docs"]),
    ([None, "writing_code", None], ["writing_code", "writing_code", "writing_code"]),
    (["gathering_data", None, "running_validation"], ["gathering_data", "running_validation", "running_validation"]),
])
def test_AC6_3_turn_fill_rule(labels, want):
    """AC6.3: next label in the turn first, then the previous one, else planning_docs."""
    assert tk.fill_turn(labels) == want


@pytest.mark.parametrize("cmd,want", [
    (".venv/bin/python scripts/run_validation.py --note x", "running_validation"),
    ("CHECK_LIVE=1 .venv/bin/pytest tests/test_phase7_publish.py", "running_validation"),
    ("curl -s -o /dev/null -w '%{http_code}' https://adityapawarr7.github.io/GenAiP2/", "running_validation"),
    ("curl -s -o /dev/null -w '%{http_code}' https://cs.yale.edu/", "gathering_data"),
    (".venv/bin/python scripts/pagetext.py https://x.edu out.txt", "gathering_data"),
    (".venv/bin/python scripts/agreement.py", "processing_data"),
    ("git add -A && git commit -m 'Phase 6'", "planning_docs"),
    ("grep -n policy data/raw/mit.md", None),
])
def test_AC6_3_bash_rules(cmd, want):
    """AC6.3: the shell-command rules give the documented step (read-only commands get no label of their own)."""
    assert tk.bash_activity(cmd) == want


def test_AC6_3_phases_follow_the_hook_timeline(fix):
    """AC6.3: messages after "Read … specs/phase-1" are phase-1; after the /clear and "specs/phase-2" they are phase-2;
    subagent calls take the phase running at their time."""
    p = {k: v["phase"] for k, v in by_id(fix).items()}
    assert p["m1"] == p["s1"] == "phase-1"
    assert p["b1"] == p["b3"] == "phase-2"


def test_AC6_3_subagents_in_the_committed_data_all_ran_in_phase_1():
    """AC6.3 (extra): every subagent message falls in Phase 1, the only phase that launched subagents."""
    assert {m["phase"] for m in COMMITTED["messages"] if m["thread"] == "subagent"} == {"phase-1"}


# ---------- clear / compact analysis ----------

def test_clear_and_compact_events_match_events_jsonl():
    """extra: tokens.json lists one /clear per SessionStart(clear) in events.jsonl and one /compact per PreCompact."""
    ev = [json.loads(l) for l in EVENTS.read_text(encoding="utf-8").splitlines() if l.strip()]
    through = ts(COMMITTED["generated_at"])
    clears = sum(1 for e in ev if e["event"] == "SessionStart" and e.get("source") == "clear" and ts(e["ts"]) <= through)
    compacts = sum(1 for e in ev if e["event"] == "PreCompact" and ts(e["ts"]) <= through)
    assert COMMITTED["counts"]["clears"] == clears
    assert COMMITTED["counts"]["compacts"] == compacts


def test_context_before_after_maths_on_fixture(fix):
    """extra: before/after = mean context of the main-thread calls on each side (up to 5); savings = gap summed over the
    calls until the next event; a PreCompact + SessionStart(compact) pair is one event."""
    ev = fix["context"]["events"]
    assert [e["type"] for e in ev] == ["clear", "compact"]
    ctx = {k: v["context"] for k, v in by_id(fix).items()}
    before = [ctx[k] for k in ("m1", "m2", "m3", "m4", "m5")]
    assert ev[0]["before_avg"] == round(sum(before) / 5)
    assert ev[0]["after_avg"] == round((ctx["b1"] + ctx["b2"]) / 2)  # b3 is after the compact
    assert ev[0]["tokens_saved_est"] == sum(max(0, ev[0]["before_avg"] - ctx[k]) for k in ("b1", "b2"))
    assert ev[1]["before_avg"] == round((ctx["b1"] + ctx["b2"]) / 2) and ev[1]["after_avg"] == ctx["b3"]


def test_context_series_is_main_thread_only_and_equals_input_plus_cache():
    """extra: the context series has one point per main-thread call, and context = input + cache writes + cache reads."""
    main = [m for m in COMMITTED["messages"] if m["thread"] == "main"]
    assert len(COMMITTED["context"]["series"]) == len(main)
    for m in main:
        assert m["context"] == m["input_tokens"] + m["cache_creation_input_tokens"] + m["cache_read_input_tokens"]


def test_tokens_json_has_no_local_paths_or_emails():
    """extra: tokens.json is public, so it holds no home paths, project paths or email addresses."""
    assert "/Users/" not in TEXT and str(Path.home()) not in TEXT
    assert not re.search(r"[\w.+-]+@[\w-]+\.(edu|com|ai|org)\b", TEXT)


@needs_transcripts
def test_subagent_count_matches_subagent_transcripts():
    """extra: one subagent row per subagent transcript with calls up to transcripts_through."""
    files = glob.glob(str(tk.TRANSCRIPTS / "*" / "subagents" / "*.jsonl"))
    assert COMMITTED["counts"]["subagents"] == len(files)


# ---------- browser (AC6.4) ----------

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
    pg = open_page(browser, base_url + "tokens.html")
    yield pg
    pg.close()


def test_AC6_4_page_loads_with_no_console_errors(page):
    """AC6.4: tokens.html reaches data-ready=true with no console errors or page errors."""
    assert page.get_attribute("body", "data-ready") == "true"
    assert page.errors == []


@pytest.mark.parametrize("scheme,width", [("dark", 1280), ("light", 375)])
def test_AC6_4_no_console_errors_in_dark_mode_and_on_a_phone(browser, base_url, scheme, width):
    """AC6.4: also error-free in dark mode and at 375px, with no sideways scroll on the phone."""
    pg = open_page(browser, base_url + "tokens.html", width=width, scheme=scheme)
    try:
        assert pg.get_attribute("body", "data-ready") == "true" and pg.errors == []
        assert pg.evaluate("document.documentElement.scrollWidth") <= width
    finally:
        pg.close()


def test_AC6_4_metric_toggle_switches_charts_to_cost_without_errors(page):
    """AC6.4 (extra): the Tokens / Est. API cost toggle re-renders the step charts in dollars, with no errors."""
    page.click('#metric button[data-metric="cost_usd"]')
    rows = page.eval_on_selector_all('details[data-for="chart-phase"] th', "els => els.map(e => e.textContent)")
    assert rows[-1] == "Total est. API cost"
    page.click('#metric button[data-metric="total"]')
    assert page.errors == []


def test_kpis_show_total_cost_cache_hit_and_types(page):
    """extra: KPI tiles show total tokens, estimated cost, cache hit % and the four token types from tokens.json."""
    labels = page.eval_on_selector_all("#kpis .label", "els => els.map(e => e.textContent)")
    assert labels[:3] == ["Total tokens", "Estimated API cost", "Cache hit rate"]
    assert page.text_content("#kpis .kpi:nth-child(3) .value") == "%.1f%%" % COMMITTED["cache_hit_pct"]
    assert page.eval_on_selector_all("#types .kpi", "els => els.length") == 4


def test_question_1_step_chart_lists_every_activity_largest_first(page):
    """extra (question 1): the by-step table lists the five steps, largest token total first."""
    names = page.eval_on_selector_all('details[data-for="chart-activity"] tbody tr td:first-child', "els => els.map(e => e.textContent)")
    want = sorted(COMMITTED["by_activity"], key=lambda a: -COMMITTED["by_activity"][a]["total"])
    labels = {"gathering_data": "Gathering data", "processing_data": "Processing data", "writing_code": "Writing code",
              "running_validation": "Running validation", "planning_docs": "Planning and docs"}
    assert names == [labels[a] for a in want]


def test_question_2_context_chart_has_a_marker_per_clear_and_compact(page):
    """extra (question 2): the context line chart carries one marker per /clear and /compact, and the before/after table one row each."""
    n = page.evaluate("Chart.getChart('chart-context').options.plugins.markers.events.length")
    assert n == COMMITTED["counts"]["clears"] + COMMITTED["counts"]["compacts"]
    assert page.eval_on_selector_all("#ctx-table tbody tr", "els => els.length") == n
    assert page.evaluate("Chart.getChart('chart-context').data.datasets[0].data.length") == len(COMMITTED["context"]["series"])


def test_question_3_subagent_section_reports_phase_1_cost(page):
    """extra (question 3): one bar per Phase 1 subagent, and the Phase 1 split matches tokens.json."""
    n = page.evaluate("Chart.getChart('chart-agents').data.labels.length")
    assert n == sum(1 for a in COMMITTED["subagents"] if a["phase"] == "phase-1")
    vals = page.evaluate("Chart.getChart('chart-p1').data.datasets[0].data")
    p1 = COMMITTED["phase_thread"]["phase-1"]
    assert vals == [p1["main"]["total"], p1["subagent"]["total"]]


def test_sessions_table_has_one_row_per_session(page):
    """extra: the sessions table lists every session in tokens.json."""
    rows = page.eval_on_selector_all("#sessions tbody tr", "els => els.map(e => e.dataset.session)")
    assert rows == [s["session"] for s in COMMITTED["sessions"]]


def test_every_dashboard_nav_links_to_tokens():
    """extra: index, findings, validation, timeline and tokens pages all have a Tokens link in the nav."""
    for name in ("index", "findings", "validation", "timeline", "tokens"):
        html = (DOCS / (name + ".html")).read_text(encoding="utf-8")
        nav = html.split('<nav class="pages"')[1].split("</nav>")[0]
        assert 'href="tokens.html"' in nav, name
