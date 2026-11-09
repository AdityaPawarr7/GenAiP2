"""Build docs/data/timeline.json for the contributions timeline (Phase 5).

Sources:
  logs/events.jsonl  hook events: prompts, responses, /clear, /compact. Their timestamps
                     are authoritative (specs/phase-5-timeline.md, timestamp authority note).
  PROGRESS.md        hand-written log entries (actor and phase tags as written).
  git log            commits with lines added/deleted per file.

Actors:  Adi | Claude | Claude-Cowork | Subagent | System
  A prompt starting with "<agent-message" is a subagent hand-back (actor Subagent), whatever
  the hook recorded: five early hand-backs were logged as actor=Adi before the hook patch.
  Other automatic prompts (<task-notification>, <system-reminder>) are actor System.

Types:   prompt | response | handback | notification | decision | review | commit | clear |
         compact | progress
  PROGRESS.md [Adi] entries take a type from their roles (decision, review, or progress);
  every [Adi] entry also carries `roles`: decision, correction, review, data_work, direction.

Phase of a hook event: hook events carry no phase, so it is inferred. A prompt that names a
specs/phase-N file starts phase N at that prompt; a prompt saying "start Phase N" starts it
right after that prompt. Events before the first such prompt are "setup".

Re-timing: a PROGRESS.md [Adi] entry is matched to the Adi prompt it records (one-to-one,
nearest first, prompt between 15 min before and 5 min after the written time). A matched
entry is ordered by that prompt's hook time; its written time is kept as `written`.
Hook events are never re-timed. A date-only entry takes the time of the timed entry above it in
PROGRESS.md (time_precision stays "date").

Usage: python scripts/build_timeline.py
"""
import json
import re
import subprocess
from collections import Counter, OrderedDict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "logs" / "events.jsonl"
PROGRESS = ROOT / "PROGRESS.md"
OUT = ROOT / "docs" / "data" / "timeline.json"

ET = "-05:00"  # every logged time is US Eastern standard time (Nov 2026)
ACTORS = ["Adi", "Claude", "Claude-Cowork", "Subagent", "System"]
PHASES = ["setup"] + ["phase-%d" % n for n in range(9)]
TYPES = ["prompt", "response", "handback", "notification", "decision", "review", "progress",
         "commit", "clear", "compact"]
ROLES = ["decision", "correction", "review", "data_work", "direction"]
MATCH_WINDOW = (timedelta(minutes=-15), timedelta(minutes=5))  # prompt time minus written time

# Roles of PROGRESS.md [Adi] entries come from these rules on the entry text...
ROLE_RULES = [
    ("review", r"^reviewed (?!and approved the phase \d plan)|^ac1\.7 spot check|\bapproved phase \d\b"),
    ("decision", r"\bdecisions?\b|\bdecided\b|\bchose\b|\bdeferred\b|said \"go\"|\(\"go\"\)|"
                 r"\bapproved the phase \d plan\b|\breviewed and approved\b|\bagreed\b|\bkeep\b|\bkept\b"),
    ("correction", r"^reviewed .*\bflagged\b"),
    ("data_work", r"^manually\b|manually opened|\bpasted its text\b|^blind-coded\b"),
    ("direction", r"\basked for\b|\bstarted phase\b|\binstructed\b|\bchose the workflow\b"),
]
# ...plus these overrides, keyed by (written time, first words), for entries the rules miss.
# Each one says why.
ROLE_OVERRIDES = {
    ("2026-11-09 17:46", "Reviewed Phase 3."): (["review", "decision", "correction"],
        "asked for chart fixes: n on each bar and a small-n note for Other"),
    ("2026-11-09 17:31", "Said \"go\" on the Phase 3"): (["decision", "direction", "correction"],
        "asked Claude to fix the stale PROGRESS.md handoff block now, not at the next clear"),
    ("2026-11-09 17:20", "Blind-coded 5 of"): (["data_work", "decision"],
        "blind human coding, then accepted Claude's reasoning on all 24 flags"),
}
# Prompt matches the alignment gets wrong: (written time, first words) -> prompt prefix, or
# None for an entry no prompt records.
MATCH_OVERRIDES = {
    ("2026-11-09 14:55", "Reviewed and approved the Phase 0 plan"): None,  # plan-mode approval, not a prompt
    ("2026-11-09 15:10", "Approved the Phase 1 plan"): "ok sir go",
}
# Who ran each commit. A commit is Claude's when a Claude response or a [Claude] PROGRESS
# entry reports making it; the rest were made by Adi outside the Claude session.
COMMIT_ACTORS = {
    "f1ed5c6": ("Claude", "PROGRESS.md 14:58 [Claude] \"git init + first commit\""),
    "2747335": ("Claude", "Claude response 15:07: \"I committed PROGRESS.md, SPEC.md and logs/events.jsonl as 2747335\""),
    "5060340": ("Adi", "no Claude response or [Claude] entry reports it; generic message, unlike Claude's \"Phase N\" messages"),
    "b7efb9d": ("Adi", "no Claude response or [Claude] entry reports it; generic message, unlike Claude's \"Phase N\" messages"),
    "c0c1ff1": ("Adi", "Claude response 17:21: \"Adi already committed the earlier Phase 2 work (c0c1ff1)\""),
    "8db27c2": ("Claude", "Adi asked \"Then commit Phase 2\" at 17:19; Claude committed"),
    "db469cb": ("Claude", "Claude response 17:49: \"Committed as db469cb\""),
    "acaa996": ("Claude", "Claude response 18:22: \"Phase 4 is committed (acaa996)\""),
    "7617d33": ("Claude", "PROGRESS.md 18:31 [Claude] \"Pushed 7617d33\""),
    "90cc388": ("Claude", "Claude response 18:31: added the live URL to the README and committed"),
}

# Public-site redaction: local paths and email addresses never reach timeline.json.
# The project path has spaces and an apostrophe, so it is replaced literally first.
LITERALS = [(str(ROOT), "<project>"), (str(Path.home()), "<home>")]
REDACTIONS = [
    (re.compile(r"/private/tmp/claude-\S*"), "<scratchpad>"),
    (re.compile(r"-Users-[\w-]+"), "<project-slug>"),
    (re.compile(r"/(?:Users|home)/[^/\s]+"), "<home>"),
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "<email>"),
]


def redact(text):
    for lit, rep in LITERALS:
        text = text.replace(lit, rep)
    for pat, rep in REDACTIONS:
        text = pat.sub(rep, text)
    return text


def iso(dt):
    return dt.isoformat()


def parse_ts(s):
    return datetime.fromisoformat(s)


def one_line(text, limit=180):
    text = re.sub(r"<pasted_content[^>]*>.*?</pasted_content>",
                  lambda m: "[pasted text, %d characters]" % len(m.group(0)), text, flags=re.S)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


# ---------- hook events ----------

def is_handback(prompt):
    return prompt.lstrip().startswith("<agent-message")


def is_automatic(prompt):
    return prompt.lstrip().startswith(("<agent-message", "<task-notification", "<system-reminder"))


def handback_text(prompt):
    """The subagent's report without the harness frame (header line and indentation)."""
    body = re.sub(r"^<agent-message[^>]*>\s*", "", prompt.strip())
    body = re.sub(r"</agent-message>\s*$", "", body)
    lines = body.splitlines()
    if lines and lines[0].startswith("[Subagent hand-back]"):
        lines = lines[1:]
    return "\n".join(l[2:] if l.startswith("  ") else l for l in lines).strip()


def notification_text(prompt):
    m = re.search(r"<summary>(.*?)</summary>", prompt, re.S)
    ev = re.search(r"<event>(.*?)</event>", prompt, re.S)
    st = re.search(r"<status>(.*?)</status>", prompt, re.S)
    parts = [x.group(1).strip() for x in (m, ev, st) if x]
    return " · ".join(parts) or prompt


PHASE_SPEC = re.compile(r"^\s*Read\b[^\n]*?specs/phase-(\d)")
PHASE_START = re.compile(r"\bstart Phase (\d)", re.I)


def hook_entries(lines):
    """One entry per hook event, in file order, with the inferred phase."""
    out, phase, pending = [], "setup", None
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        e = json.loads(line)
        ts, kind = e["ts"], e["event"]
        if pending:
            phase, pending = pending, None
        base = {"ts": ts, "ts_source": "hook", "time_precision": "second", "source": "events.jsonl:%d" % i,
                "session": e.get("session_id", "")[:8]}
        if kind == "UserPromptSubmit":
            p = e.get("prompt", "")
            if not is_automatic(p):
                m = PHASE_SPEC.search(p)
                if m:
                    phase = "phase-" + m.group(1)
                m2 = PHASE_START.search(p)
                if m2:
                    pending = "phase-" + m2.group(1)
            if is_handback(p):
                txt = redact(handback_text(p))
                ent = dict(base, actor="Subagent", type="handback", summary=one_line(txt), detail=txt)
                if e.get("actor") != "Subagent":
                    ent["relabeled_from"] = e.get("actor")
            elif is_automatic(p):
                txt = redact(notification_text(p))
                ent = dict(base, actor="System", type="notification", summary=one_line(txt), detail=redact(p))
            else:
                txt = redact(p)
                ent = dict(base, actor="Adi", type="prompt", summary=one_line(txt), detail=txt)
        elif kind == "Stop":
            txt = redact(e.get("response", ""))
            ent = dict(base, actor="Claude", type="response", summary=one_line(txt) or "(no response text logged for this turn)", detail=txt)
        elif kind == "SessionStart":
            src = e.get("source", "")
            if src not in ("clear", "compact"):
                continue
            ent = dict(base, actor="Adi", type=src, summary="/" + src + ": context reset, new session " + base["session"],
                       detail="")
        else:
            continue
        ent["phase"] = phase
        out.append(ent)
    return out


# ---------- PROGRESS.md ----------

ENTRY = re.compile(r"^- \[(\d{4}-\d{2}-\d{2})(?: (\d{1,2}:\d{2}))?(?: ET)?\] \[([\w-]+)\] \[([\w-]+)\] (.*)$")


def roles_for(written, text):
    for (w, start), (roles, why) in ROLE_OVERRIDES.items():
        if written == w and text.startswith(start):
            return roles, why
    low = text.lower()
    return [r for r, pat in ROLE_RULES if re.search(pat, low)], None


def progress_entries(text):
    out, last_ts = [], None
    for n, line in enumerate(text.splitlines(), 1):
        m = ENTRY.match(line)
        if not m:
            continue
        date, hm, phase, actor, body = m.groups()
        written = date + (" " + hm if hm else "")
        if hm:
            ts = last_ts = "%sT%s:00%s" % (date, hm.zfill(5), ET)
        elif last_ts and last_ts.startswith(date):
            ts = last_ts  # date-only entry: placed right after the timed entry above it in the file
        else:
            ts = "%sT00:00:00%s" % (date, ET)
        body = redact(body)
        ent = {"ts": ts, "ts_source": "progress", "time_precision": "minute" if hm else "date",
               "written": written + " ET", "source": "PROGRESS.md:%d" % n, "actor": actor, "phase": phase,
               "type": "progress", "summary": one_line(body, 220), "detail": body}
        if actor == "Adi":
            roles, why = roles_for(written, body)
            ent["roles"] = roles
            if why:
                ent["role_note"] = why
            ent["type"] = "review" if "review" in roles else ("decision" if "decision" in roles else "progress")
        out.append(ent)
    return out


def _align(entries, prompts):
    """Order-preserving alignment of entries to prompts: most matches, then least total time gap.
    Two entries may share one prompt (one message, two logged decisions) at a 5-minute penalty."""
    lo, hi = MATCH_WINDOW
    ew = [parse_ts(e["ts"]) for e in entries]
    pt = [parse_ts(p["ts"]) for p in prompts]
    memo = {}

    def best(i, last):
        if i == len(entries):
            return (0, 0.0, ())
        key = (i, last)
        if key not in memo:
            cands = [best(i + 1, last)]
            for k in range(max(last, 0), len(prompts)):
                d = pt[k] - ew[i]
                if d > hi:
                    break
                if d < lo:
                    continue
                n, cost, picks = best(i + 1, k)
                gap = abs(d.total_seconds()) + (300 if k == last else 0)
                cands.append((n + 1, cost + gap, ((i, k),) + picks))
            memo[key] = max(cands, key=lambda c: (c[0], -c[1]))
        return memo[key]

    return best(0, -1)[2]


def match_progress_to_prompts(progress, hooks):
    """Re-time [Adi] PROGRESS entries to the Adi prompt they record."""
    prompts = [h for h in hooks if h["type"] == "prompt"]
    adi = sorted((p for p in progress if p["actor"] == "Adi" and p["time_precision"] == "minute"),
                 key=lambda p: parse_ts(p["ts"]))
    forced, free = [], []
    for p in adi:
        o = [v for (w, start), v in MATCH_OVERRIDES.items() if p["written"] == w + " ET" and p["detail"].startswith(start)]
        (forced if o else free).append((p, o[0] if o else None))
    pairs = [(free[i][0], prompts[k]) for i, k in _align([p for p, _ in free], prompts)]
    for p, prefix in forced:
        if prefix is not None:
            pairs.append((p, next(h for h in prompts if h["detail"].startswith(prefix))))
    for p, h in pairs:
        p["ts"], p["ts_source"], p["time_precision"] = h["ts"], "hook (matched prompt)", "second"
        p["prompt_ref"] = h["source"]
        h.setdefault("progress_refs", []).append(p["source"])


# ---------- git ----------

def loc_kind(path):
    if path.startswith("logs/"):
        return "logs"
    if path.startswith(("data/", "docs/data/")) or "/vendor/" in path:
        return "data"
    if path.endswith(".md"):
        return "docs"
    return "code"


def git_commits():
    fmt = "\x1e%h\x1f%aI\x1f%s"
    try:
        raw = subprocess.run(["git", "log", "--numstat", "--format=" + fmt], cwd=str(ROOT),
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    out = []
    for block in raw.split("\x1e")[1:]:
        head, _, rest = block.partition("\n")
        h, ts, subject = head.split("\x1f")
        loc = OrderedDict((k, {"added": 0, "deleted": 0}) for k in ("code", "docs", "data", "logs"))
        files = 0
        for row in rest.strip().splitlines():
            a, d, path = row.split("\t", 2)
            files += 1
            if a == "-":  # binary file
                continue
            k = loc_kind(path.split(" => ")[-1].rstrip("}"))
            loc[k]["added"] += int(a)
            loc[k]["deleted"] += int(d)
        out.append({"hash": h, "ts": ts, "subject": subject, "files": files, "loc": loc})
    return out


def phase_at(ts, hooks):
    cur = "setup"
    for h in hooks:
        if h["ts"] > ts:
            break
        cur = h["phase"]
    return cur


def commit_entries(commits, hooks):
    out = []
    for c in commits:
        m = re.match(r"Phase (\d)", c["subject"])
        phase = "phase-" + m.group(1) if m else phase_at(c["ts"], hooks)
        actor, evidence = COMMIT_ACTORS.get(c["hash"], ("Claude" if m else "Adi", "rule: \"Phase N\" message = Claude"))
        code = c["loc"]["code"]
        out.append({"ts": c["ts"], "ts_source": "git", "time_precision": "second", "source": "git:" + c["hash"],
                    "actor": actor, "actor_evidence": evidence, "phase": phase, "type": "commit",
                    "summary": "%s %s" % (c["hash"], c["subject"]),
                    "detail": "%d files; code +%d −%d" % (c["files"], code["added"], code["deleted"]),
                    "commit": {"hash": c["hash"], "files": c["files"], "loc": c["loc"]}})
    return out


# ---------- assembly ----------

def qa_pairs(entries):
    """Adi's prompts, each with the responses and hand-backs that followed it in the same session."""
    out, cur = [], None
    for e in entries:
        if e["ts_source"] != "hook":
            continue
        if e["type"] == "prompt":
            cur = {"prompt": e["id"], "session": e["session"], "phase": e["phase"], "turns": []}
            out.append(cur)
        elif e["type"] in ("clear", "compact"):
            cur = None
        elif cur and e["session"] == cur["session"] and e["type"] in ("response", "handback", "notification"):
            cur["turns"].append(e["id"])
    return out


def summarize(entries):
    by_phase = OrderedDict((p, {"actors": Counter(), "types": Counter(), "roles": Counter(),
                                "loc": Counter(), "commits": 0}) for p in PHASES)
    for e in entries:
        s = by_phase[e["phase"]]
        s["actors"][e["actor"]] += 1
        s["types"][e["type"]] += 1
        for r in e.get("roles", []):
            s["roles"][r] += 1
        if e["type"] == "commit":
            s["commits"] += 1
            for k, v in e["commit"]["loc"].items():
                s["loc"][k + "_added"] += v["added"]
                s["loc"][k + "_deleted"] += v["deleted"]
    return OrderedDict((p, {k: (dict(v) if isinstance(v, Counter) else v) for k, v in s.items()})
                       for p, s in by_phase.items())


def build(events_lines, progress_text, commits):
    hooks = hook_entries(events_lines)
    progress = progress_entries(progress_text)
    match_progress_to_prompts(progress, hooks)
    commits_e = commit_entries(commits, hooks)
    # Stable sort by time; ties keep source order (hook, then PROGRESS.md, then git).
    entries = sorted(hooks + progress + commits_e, key=lambda e: parse_ts(e["ts"]))
    for n, e in enumerate(entries, 1):
        e["id"] = "e%03d" % n
    id_by_source = {e["source"]: e["id"] for e in entries}
    for e in entries:
        if "prompt_ref" in e:
            e["prompt_ref"] = id_by_source[e["prompt_ref"]]
        if "progress_refs" in e:
            e["progress_refs"] = [id_by_source[s] for s in e["progress_refs"]]
    hook_ts = [e["ts"] for e in hooks]
    return OrderedDict([
        ("generated_at", datetime.now().astimezone().replace(microsecond=0).isoformat()),
        ("events_through", max(hook_ts) if hook_ts else None),
        ("actors", ACTORS), ("phases", PHASES), ("types", TYPES), ("roles", ROLES),
        ("counts", {"hook_events": len(hooks), "progress_entries": len(progress), "commits": len(commits_e),
                    "relabeled_handbacks": sum(1 for e in hooks if e.get("relabeled_from")),
                    "retimed_progress_entries": sum(1 for e in progress if "prompt_ref" in e)}),
        ("summary", summarize(entries)),
        ("qa", qa_pairs(entries)),
        ("entries", entries),
    ])


def main():
    data = build(EVENTS.read_text(encoding="utf-8").splitlines(), PROGRESS.read_text(encoding="utf-8"), git_commits())
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    c = data["counts"]
    print("timeline.json: %d entries (%d hook, %d PROGRESS.md, %d commits); %d hand-backs relabeled; %d entries re-timed"
          % (len(data["entries"]), c["hook_events"], c["progress_entries"], c["commits"],
             c["relabeled_handbacks"], c["retimed_progress_entries"]))


if __name__ == "__main__":
    main()
