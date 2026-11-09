# Phase 5: Contributions timeline (`docs/timeline.html`)
## Tasks
1. `scripts/build_timeline.py`: parses `logs/events.jsonl` + `PROGRESS.md` + `git log` and writes `docs/data/timeline.json` (ts, actor Adi|Claude|Claude-Cowork, phase, type prompt|response|decision|review|commit|clear|compact, summary, detail).
2. Dashboard: a vertical timeline filterable by actor, phase and type; a searchable Q&A log (Adi's prompts paired with Claude's responses); a contribution summary (counts by actor and type per phase, prompts per phase, LOC changed by phase from git); and an "Adi's role" panel listing decisions, corrections and reviews.
## Acceptance criteria
- AC5.1: Every prompt in events.jsonl appears in timeline.json.
- AC5.2: Timestamps are sorted, and each one parses as ISO-8601.
- AC5.3: Every entry has a valid actor and phase.
- AC5.4: Page loads with no console errors, and the filters work (Playwright).
