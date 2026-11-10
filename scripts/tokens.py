"""Build docs/data/tokens.json for the token usage dashboard (Phase 6).

Sources
  ~/.claude/projects/<this project>/*.jsonl               main-session transcripts
  ~/.claude/projects/<this project>/<session>/subagents/  subagent transcripts (+ .meta.json with
                                                          the task description). Phase 1's data
                                                          collection ran here, so they must be read.
  logs/events.jsonl   phase markers (same inference as build_timeline.py) and /clear, /compact events.

Counting rules
  * Only assistant lines whose `cwd` is this project (or a folder inside it) are kept.
  * One API message is written as several lines (one per content block) that share
    `message.id`. A message is counted ONCE: its usage is the LAST line for that id in file
    order (earlier copies can carry partial output_tokens while the reply was still streaming);
    its tool calls are the union of all its lines. Ids are unique across all files.
  * context size of a main-thread message = input + cache_creation + cache_read tokens: what
    the model had to read on that call.

Phase: the phase in force at the message's time, from the timeline of hook events
(build_timeline.hook_entries). Subagent messages get the phase in force while they ran.

Activity: each message gets exactly one of ACTIVITIES.
  1. Every tool call is classified with TOOL_RULES / BASH_RULES / PATH_RULES below (first
     match wins). Calls that only read or look around (Read, grep, cat, ls ...) get no label.
  2. A message with several labelled calls takes the first one in ACTIVITY_PRIORITY.
  3. A message with no labelled call (pure reading, or text only) takes the label of the next
     labelled message in the same turn (reading usually precedes the action it serves), else the
     previous one in the turn, else planning_docs. A turn runs from one real user prompt to the
     next; a subagent transcript is one turn.

Estimated cost: API list prices for claude-opus-5-5 (the only model in the transcripts), from
the claude-api skill's model table (cached 2026-11-03): $4/M input, $20/M output, $0.20/M cache
read; cache writes 1.25x input for the 5-minute tier, 2x for the 1-hour tier. This is an API
price equivalent, not what the subscription plan charged.

Usage: python scripts/tokens.py
"""
import glob
import json
import os
import re
import sys
from collections import Counter, OrderedDict, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_timeline as bt  # noqa: E402

EVENTS = ROOT / "logs" / "events.jsonl"
OUT = ROOT / "docs" / "data" / "tokens.json"
TRANSCRIPTS = Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(ROOT))
ET = timezone(timedelta(hours=-5))  # every logged time is US Eastern standard time (Nov 2026)

TYPES = ["input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"]
ACTIVITIES = ["gathering_data", "processing_data", "writing_code", "running_validation", "planning_docs"]
ACTIVITY_PRIORITY = ["running_validation", "writing_code", "processing_data", "gathering_data", "planning_docs"]
PHASES = bt.PHASES
WINDOW = 5  # turns averaged before / after a /clear or /compact

PRICES = OrderedDict([  # USD per million tokens, claude-opus-5-5
    ("input", 4.00), ("output", 20.00), ("cache_write_5m", 5.00), ("cache_write_1h", 8.00), ("cache_read", 0.20),
])
PRICE_NOTE = ("API list price for claude-opus-5-5 (claude-api skill model table, cached 2026-11-03): $4/M input, "
              "$20/M output, $0.20/M cache read; cache writes 1.25x input (5-minute) and 2x (1-hour). "
              "An API-price equivalent, not what the plan charged.")

# ---------- activity rules ----------
SCRIPTS_PROCESSING = r"scripts/(build_policies|analyze|agreement|lexicon_check|sample_for_human|build_dashboard_data|build_timeline|build_coding_page|tokens|codebook_schema|raw_format)\.py"
BASH_RULES = [  # (activity, regex on the command); first match wins. curl status checks count as
    # validation only against the live site (github.io/GenAiP2); elsewhere they are page hunting.
    ("running_validation", r"\bpytest\b|run_validation\.py|playwright|check_quotes\.py|validate_palette|CHECK_LIVE|github\.io/GenAiP2|node --check|py_compile"),
    ("gathering_data", r"\bcurl\b|\bwget\b|requests\.(get|head|Session)|urllib|pagetext\.py|/pages/"),
    ("planning_docs", r">>?\s*\"?PROGRESS\.md|PROGRESS\.md\"?\s*$|sed -i[^|;&]*(PROGRESS|SPEC|README|CLAUDE)\.md|\bgit (add|commit|push|init|config)\b|\bgh\b"),
    ("gathering_data", r"(>|tee|sed -i\S*\s).*data/raw/"),
    ("processing_data", SCRIPTS_PROCESSING + r"|(>|tee|sed -i\S*\s).*(data/|docs/data/)|data/(processed|coding)/|docs/data/|institutions\.csv"),
    ("writing_code", r"(cat|tee)\s*>+\s*\S*\.(py|js|html|css|json)\b|sed -i\S*\s.*\.(py|js|html|css)\b"),
]
PATH_RULES = [  # (activity, regex on a Write/Edit file path relative to the project); first match wins
    ("gathering_data", r"^data/raw/"),
    ("processing_data", r"^data/|^docs/data/"),
    ("writing_code", r"\.(py|js|html|css|sh)$|^\.claude/(settings|hooks)"),
    ("planning_docs", r"\.md$|\.txt$"),
]
TOOL_RULES = {  # tools whose name alone decides
    "WebSearch": "gathering_data", "WebFetch": "gathering_data",
    "ExitPlanMode": "planning_docs", "EnterPlanMode": "planning_docs",
}


def bash_activity(cmd):
    for act, pat in BASH_RULES:
        if re.search(pat, cmd):
            return act
    return None


def path_activity(path, root=str(ROOT)):
    p = str(path)
    if p.startswith(root):
        p = p[len(root):].lstrip("/")
    elif p.startswith("/"):
        return None  # scratchpad and other files outside the project: helpers, no label
    for act, pat in PATH_RULES:
        if re.search(pat, p):
            return act
    return None


def call_activity(name, inp, root=str(ROOT)):
    if name in TOOL_RULES:
        return TOOL_RULES[name]
    if name == "Bash":
        return bash_activity(inp.get("command", ""))
    if name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        return path_activity(inp.get("file_path") or inp.get("notebook_path") or "", root)
    if name == "Agent":
        d = (inp.get("description", "") + " " + inp.get("prompt", "")[:400]).lower()
        return "gathering_data" if re.search(r"collect|gather|find|fetch|search", d) else "planning_docs"
    return None


def message_activity(calls, root=str(ROOT)):
    acts = {call_activity(n, i, root) for n, i in calls} - {None}
    for a in ACTIVITY_PRIORITY:
        if a in acts:
            return a
    return None


def fill_turn(labels):
    """Unlabelled messages take the next label in the turn, else the previous, else planning_docs."""
    out, nxt = list(labels), None
    for i in range(len(out) - 1, -1, -1):
        if out[i] is None:
            out[i] = ("next", nxt) if nxt else None
        else:
            nxt = out[i]
    prev = None
    for i, v in enumerate(out):
        if isinstance(v, tuple):
            out[i] = v[1]
        elif v is None:
            out[i] = prev or "planning_docs"
        prev = out[i]
    return out


# ---------- transcripts ----------

def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def is_real_prompt(d):
    """A user line that starts a new turn: typed text, not a tool result or harness meta line."""
    if d.get("type") != "user" or d.get("isMeta"):
        return False
    c = (d.get("message") or {}).get("content")
    if isinstance(c, str):
        return True
    return isinstance(c, list) and not any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c)


def transcript_files(base=TRANSCRIPTS):
    main = sorted(glob.glob(str(base / "*.jsonl")))
    subs = sorted(glob.glob(str(base / "*" / "subagents" / "*.jsonl")))
    return main, subs


def read_transcript(path, root=str(ROOT)):
    """Messages of one transcript file in order: dicts with id, ts, usage, calls, turn."""
    msgs, order, turn = {}, [], 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if is_real_prompt(d):
                turn += 1
            if d.get("type") != "assistant":
                continue
            if not (d.get("cwd") or "").startswith(root):
                continue
            m = d.get("message") or {}
            mid, usage = m.get("id"), m.get("usage")
            if not mid or not usage:
                continue
            if mid not in msgs:
                msgs[mid] = {"id": mid, "ts": d.get("timestamp"), "usage": usage, "calls": [], "turn": turn,
                             "sidechain": bool(d.get("isSidechain")), "model": m.get("model")}
                order.append(mid)
            else:
                msgs[mid]["usage"] = usage  # last copy wins
            for b in m.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    msgs[mid]["calls"].append((b.get("name"), b.get("input") or {}))
    return [msgs[i] for i in order]


def subagent_meta(path):
    meta = Path(path[:-len(".jsonl")] + ".meta.json")
    try:
        return json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def cost(u, speed_mult=1.0):
    cc = u.get("cache_creation") or {}
    w1h = cc.get("ephemeral_1h_input_tokens", 0) or 0
    w5m = (u.get("cache_creation_input_tokens", 0) or 0) - w1h
    usd = ((u.get("input_tokens", 0) or 0) * PRICES["input"] + (u.get("output_tokens", 0) or 0) * PRICES["output"] +
           w5m * PRICES["cache_write_5m"] + w1h * PRICES["cache_write_1h"] +
           (u.get("cache_read_input_tokens", 0) or 0) * PRICES["cache_read"]) / 1e6
    return usd * speed_mult


# ---------- phases + events ----------

def phase_timeline(event_lines):
    hooks = bt.hook_entries(event_lines)
    return [(parse_ts(h["ts"]), h["phase"]) for h in hooks]


def phase_at(ts, timeline):
    cur = "setup"
    for t, p in timeline:
        if t > ts:
            break
        cur = p
    return cur


def context_events(event_lines):
    """/clear and /compact events from events.jsonl. A PreCompact and the SessionStart(compact) that
    follows it within 10 minutes are one event (timed at the PreCompact)."""
    out = []
    for n, line in enumerate(event_lines, 1):
        if not line.strip():
            continue
        e = json.loads(line)
        kind = None
        if e["event"] == "SessionStart" and e.get("source") in ("clear", "compact"):
            kind = e["source"]
        elif e["event"] == "PreCompact":
            kind = "compact"
        if not kind:
            continue
        ts = parse_ts(e["ts"])
        if kind == "compact" and out and out[-1]["type"] == "compact" and ts - parse_ts(out[-1]["ts"]) < timedelta(minutes=10):
            continue
        out.append({"ts": e["ts"], "type": kind, "session": e.get("session_id", "")[:8],
                    "trigger": e.get("trigger") or e.get("source"), "source": "events.jsonl:%d" % n})
    return out


# ---------- build ----------

def zero():
    return OrderedDict([(t, 0) for t in TYPES] + [("total", 0), ("cost_usd", 0.0), ("messages", 0)])


def add(acc, m):
    for t in TYPES:
        acc[t] += m[t]
    acc["total"] += m["total"]
    acc["cost_usd"] += m["cost_usd"]
    acc["messages"] += 1


def rounded(acc):
    acc = OrderedDict(acc)
    acc["cost_usd"] = round(acc["cost_usd"], 4)
    return acc


def collect(base=TRANSCRIPTS, root=str(ROOT)):
    """All messages from main and subagent transcripts, deduplicated by message id across files."""
    main, subs = transcript_files(base)
    seen, out, agents = set(), [], OrderedDict()
    for path in main + subs:
        is_sub = "/subagents/" in path
        session = (Path(path).parent.parent.name if is_sub else Path(path).stem)[:8]
        agent = Path(path).stem.replace("agent-", "")[:8] if is_sub else None
        msgs = [m for m in read_transcript(path, root) if m["id"] not in seen]
        if is_sub:
            meta = subagent_meta(path)
            agents[agent] = {"agent": agent, "session": session, "description": meta.get("description", ""),
                             "agent_type": meta.get("agentType", "")}
        labels = fill_turn_by_turn(msgs, root)
        for m, act in zip(msgs, labels):
            seen.add(m["id"])
            m.update(session=session, agent=agent, thread="subagent" if is_sub else "main", activity=act)
            out.append(m)
    return out, agents


def fill_turn_by_turn(msgs, root=str(ROOT)):
    labels = [message_activity(m["calls"], root) for m in msgs]
    out, i = [], 0
    while i < len(msgs):
        j = i
        while j < len(msgs) and msgs[j]["turn"] == msgs[i]["turn"]:
            j += 1
        out.extend(fill_turn(labels[i:j]))
        i = j
    return out


def build(event_lines, base=TRANSCRIPTS, root=str(ROOT)):
    raw, agents = collect(base, root)
    timeline = phase_timeline(event_lines)
    msgs = []
    for m in sorted(raw, key=lambda m: m["ts"]):
        u, ts = m["usage"], parse_ts(m["ts"])
        rec = OrderedDict([("id", m["id"]), ("ts", ts.astimezone(ET).isoformat()), ("session", m["session"]),
                           ("thread", m["thread"]), ("agent", m["agent"]), ("phase", phase_at(ts, timeline)),
                           ("activity", m["activity"])])
        for t in TYPES:
            rec[t] = u.get(t, 0) or 0
        rec["total"] = sum(rec[t] for t in TYPES)
        rec["context"] = rec["input_tokens"] + rec["cache_creation_input_tokens"] + rec["cache_read_input_tokens"]
        rec["cost_usd"] = round(cost(u, 2.0 if u.get("speed") == "fast" else 1.0), 6)
        rec["tools"] = sorted({n for n, _ in m["calls"]})
        msgs.append(rec)

    totals = zero()
    by = {k: defaultdict(zero) for k in ("phase", "activity", "session", "day", "thread")}
    phase_activity = defaultdict(lambda: defaultdict(zero))
    phase_thread = defaultdict(lambda: defaultdict(zero))
    by_agent = defaultdict(zero)
    tool_counts = defaultdict(Counter)
    for r in msgs:
        add(totals, r)
        for k in by:
            add(by[k][r[k] if k != "day" else r["ts"][:10]], r)
        add(phase_activity[r["phase"]][r["activity"]], r)
        add(phase_thread[r["phase"]][r["thread"]], r)
        if r["agent"]:
            add(by_agent[r["agent"]], r)
            tool_counts[r["agent"]].update(r["tools"])

    events = context_events(event_lines)
    ctx = context_analysis(msgs, events)
    sessions = session_table(msgs, events, event_lines)

    agent_rows = []
    for a, info in agents.items():
        if a not in by_agent:
            continue
        row = OrderedDict(info)
        first = next(r for r in msgs if r["agent"] == a)
        row["phase"] = first["phase"]
        row["start"] = first["ts"]
        row["end"] = [r for r in msgs if r["agent"] == a][-1]["ts"]
        row["tool_calls"] = dict(tool_counts[a])
        row.update(rounded(by_agent[a]))
        agent_rows.append(row)
    agent_rows.sort(key=lambda r: r["start"])

    cache_in = totals["cache_read_input_tokens"]
    all_in = totals["input_tokens"] + totals["cache_creation_input_tokens"] + totals["cache_read_input_tokens"]
    return OrderedDict([
        ("generated_at", datetime.now().astimezone().replace(microsecond=0).isoformat()),
        ("transcripts_through", msgs[-1]["ts"] if msgs else None),
        ("model", sorted({m["model"] for m in raw if m.get("model")})),
        ("types", TYPES), ("activities", ACTIVITIES), ("phases", PHASES),
        ("pricing", OrderedDict([("usd_per_million", PRICES), ("note", PRICE_NOTE)])),
        ("rules", OrderedDict([("dedup", "one count per message.id; usage from the last line for that id"),
                               ("activity_priority", ACTIVITY_PRIORITY), ("context_window_turns", WINDOW)])),
        ("counts", OrderedDict([("messages", len(msgs)), ("main_messages", sum(1 for r in msgs if r["thread"] == "main")),
                                ("subagent_messages", sum(1 for r in msgs if r["thread"] == "subagent")),
                                ("subagents", len(agent_rows)), ("sessions", len(by["session"])),
                                ("clears", sum(1 for e in events if e["type"] == "clear")),
                                ("compacts", sum(1 for e in events if e["type"] == "compact"))])),
        ("totals", rounded(totals)),
        ("cache_hit_pct", round(100.0 * cache_in / all_in, 2) if all_in else 0.0),
        ("by_phase", OrderedDict((p, rounded(by["phase"][p])) for p in PHASES if p in by["phase"])),
        ("by_activity", OrderedDict((a, rounded(by["activity"][a])) for a in ACTIVITIES if a in by["activity"])),
        ("by_thread", OrderedDict((t, rounded(by["thread"][t])) for t in ("main", "subagent") if t in by["thread"])),
        ("by_day", OrderedDict((d, rounded(v)) for d, v in sorted(by["day"].items()))),
        ("by_session", OrderedDict((s, rounded(v)) for s, v in by["session"].items())),
        ("phase_activity", OrderedDict((p, OrderedDict((a, rounded(phase_activity[p][a])) for a in ACTIVITIES if a in phase_activity[p]))
                                       for p in PHASES if p in phase_activity)),
        ("phase_thread", OrderedDict((p, OrderedDict((t, rounded(phase_thread[p][t])) for t in ("main", "subagent") if t in phase_thread[p]))
                                     for p in PHASES if p in phase_thread)),
        ("subagents", agent_rows),
        ("sessions", sessions),
        ("context", ctx),
        ("not_measured", ["Claude-Cowork sessions (setup, reviews, the human-coding page and the second AI coder) ran outside "
                          "Claude Code; their transcripts are not on this machine, so their tokens are not counted.",
                          "Session 231b8c0c holds only a /clear and no API calls."]),
        ("messages", msgs),
    ])


def context_analysis(msgs, events):
    main = [r for r in msgs if r["thread"] == "main"]
    series = [{"ts": r["ts"], "context": r["context"], "session": r["session"], "phase": r["phase"]} for r in main]
    rows = []
    for i, e in enumerate(events):
        t = parse_ts(e["ts"])
        nxt = parse_ts(events[i + 1]["ts"]) if i + 1 < len(events) else None
        prv = parse_ts(events[i - 1]["ts"]) if i else None
        # Before: up to WINDOW calls since the previous event; after: up to WINDOW calls before the next one.
        before = [r for r in main if parse_ts(r["ts"]) < t and (prv is None or parse_ts(r["ts"]) > prv)][-WINDOW:]
        after_all = [r for r in main if parse_ts(r["ts"]) > t and (nxt is None or parse_ts(r["ts"]) < nxt)]
        after = after_all[:WINDOW]
        row = OrderedDict(e)
        row["phase"] = before[-1]["phase"] if before else (after[0]["phase"] if after else None)
        row["before_avg"] = round(sum(r["context"] for r in before) / len(before)) if before else None
        row["before_last"] = before[-1]["context"] if before else None
        row["after_avg"] = round(sum(r["context"] for r in after) / len(after)) if after else None
        row["after_first"] = after[0]["context"] if after else None
        row["before_n"], row["after_n"], row["turns_until_next"] = len(before), len(after), len(after_all)
        if before and after:
            row["change_pct"] = round(100.0 * (row["after_avg"] - row["before_avg"]) / row["before_avg"], 1)
            # Tokens not re-read: each call until the next event would otherwise have carried the
            # pre-event context; we count the gap against what it actually read.
            row["tokens_saved_est"] = sum(max(0, row["before_avg"] - r["context"]) for r in after_all)
        else:
            row["change_pct"] = row["tokens_saved_est"] = None
        rows.append(row)
    valid = [r for r in rows if r["before_avg"] is not None and r["after_avg"] is not None]
    summ = OrderedDict()
    for kind in ("clear", "compact"):
        v = [r for r in valid if r["type"] == kind]
        summ[kind] = OrderedDict([("events", sum(1 for r in rows if r["type"] == kind)), ("measured", len(v)),
                                  ("avg_before", round(sum(r["before_avg"] for r in v) / len(v)) if v else None),
                                  ("avg_after", round(sum(r["after_avg"] for r in v) / len(v)) if v else None),
                                  ("tokens_saved_est", sum(r["tokens_saved_est"] for r in v))])
    return OrderedDict([("series", series), ("events", rows), ("summary", summ)])


def session_table(msgs, events, event_lines):
    out = []
    sessions = OrderedDict()
    for r in msgs:
        sessions.setdefault(r["session"], []).append(r)
    starts = sorted(parse_ts(rs[0]["ts"]) for rs in sessions.values())
    for s, rs in sessions.items():
        main = [r for r in rs if r["thread"] == "main"]
        acc = zero()
        for r in rs:
            add(acc, r)
        # Ended by /clear when a clear falls between this session's last main message and the next session's start.
        end_ts = parse_ts(main[-1]["ts"]) if main else parse_ts(rs[-1]["ts"])
        nxt_start = next((t for t in starts if t > end_ts), None)
        cleared = any(e["type"] == "clear" and end_ts < parse_ts(e["ts"]) and (nxt_start is None or parse_ts(e["ts"]) <= nxt_start)
                      for e in events)
        how = "clear" if cleared else "open"
        phases = []
        for r in rs:
            if r["phase"] not in phases:
                phases.append(r["phase"])
        row = OrderedDict([("session", s), ("start", rs[0]["ts"]), ("end", rs[-1]["ts"]), ("phases", phases),
                           ("main_messages", len(main)), ("subagent_messages", len(rs) - len(main)),
                           ("subagents", len({r["agent"] for r in rs if r["agent"]})),
                           ("peak_context", max([r["context"] for r in main] or [0])), ("ended_by", how),
                           ("compacts", sum(1 for e in events if e["type"] == "compact" and e["session"] == s))])
        row.update(rounded(acc))
        out.append(row)
    return out


def main():
    lines = EVENTS.read_text(encoding="utf-8").splitlines()
    if not TRANSCRIPTS.is_dir():
        sys.exit("No transcripts at %s" % TRANSCRIPTS)
    data = build(lines)
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    text = bt.redact(text)
    OUT.write_text(text + "\n", encoding="utf-8")
    t, c = data["totals"], data["counts"]
    print("tokens.json: %d messages (%d main, %d subagent, %d subagents); %s tokens; est $%.2f; cache hit %.1f%%; "
          "%d clears, %d compacts" % (c["messages"], c["main_messages"], c["subagent_messages"], c["subagents"],
                                       format(t["total"], ","), t["cost_usd"], data["cache_hit_pct"], c["clears"], c["compacts"]))
    for a, v in data["by_activity"].items():
        print("  %-20s %12s tokens  $%8.2f  %4d msgs" % (a, format(v["total"], ","), v["cost_usd"], v["messages"]))


if __name__ == "__main__":
    main()
