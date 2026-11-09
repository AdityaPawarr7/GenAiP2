#!/usr/bin/env python3
"""Claude Code hook: append prompts, responses, clear/compact events to logs/events.jsonl.
Never blocks Claude: always exits 0."""
import json, os, sys, datetime

def last_turn(transcript_path):
    """Return (assistant_text, usage_sum, n_msgs) for messages after the last user prompt."""
    text, usage, seen, n = [], {}, set(), 0
    try:
        with open(transcript_path, encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
    except Exception:
        return "", {}, 0
    start = 0
    for i, e in enumerate(lines):
        m = e.get("message") or {}
        if e.get("type") == "user" and isinstance(m.get("content"), str):
            start = i
    for e in lines[start:]:
        if e.get("type") != "assistant":
            continue
        m = e.get("message") or {}
        mid = m.get("id")
        for c in m.get("content") or []:
            if isinstance(c, dict) and c.get("type") == "text":
                text.append(c.get("text", ""))
        if mid in seen:
            continue
        seen.add(mid); n += 1
        for k, v in (m.get("usage") or {}).items():
            if isinstance(v, int):
                usage[k] = usage.get(k, 0) + v
    return "\n".join(text), usage, n

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    ev = data.get("hook_event_name", "unknown")
    rec = {"ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "event": ev, "session_id": data.get("session_id")}
    if ev == "UserPromptSubmit":
        prompt = data.get("prompt", "")
        auto = prompt.lstrip().startswith(("<agent-message", "<task-notification", "<system-reminder"))
        rec["actor"] = "Subagent" if auto else "Adi"
        rec["prompt_kind"] = "subagent_handback" if auto else "human"
        rec["prompt"] = prompt if not auto else prompt[:1000]
    elif ev == "Stop":
        txt, usage, n = last_turn(data.get("transcript_path", ""))
        rec.update(actor="Claude", response=txt[:4000], usage=usage, assistant_msgs=n)
    elif ev == "PreCompact":
        rec.update(trigger=data.get("trigger"), custom_instructions=data.get("custom_instructions"))
    elif ev == "SessionStart":
        rec["source"] = data.get("source")  # startup | resume | clear | compact
    root = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    path = os.path.join(root, "logs", "events.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
