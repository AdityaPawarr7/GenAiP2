# Phase 6: Token usage dashboard (`docs/tokens.html`)
## Data sources
- Claude Code transcripts: `~/.claude/projects/*/*.jsonl`. Keep only lines whose `cwd` is this project. Each assistant message has `message.usage` {input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens}. Deduplicate by `message.id`.
- `logs/events.jsonl`: phase markers, plus /clear (SessionStart source=clear) and /compact (PreCompact) events.
- Manual entries in `logs/manual_usage.md` (e.g., /usage screenshots, % of plan limit) and Cowork-session estimates.
## Tasks
1. `scripts/tokens.py` → `docs/data/tokens.json`: per message (ts, session, phase, activity, the four token types), plus aggregates by phase, activity, session and day.
2. Assign each message an activity: gathering_data / processing_data / writing_code / running_validation / planning_docs, using its tool calls (WebSearch/WebFetch → gathering, Bash running pytest → validation, Write/Edit on .py/.html → code, etc.).
3. Clear/compact analysis: context size (input + cache tokens) per turn plotted over time, with clear and compact events marked. Report the average context size before vs. after each event and the tokens saved.
4. Dashboard: KPIs (total, by type, cache hit %); stacked bar by phase; donut by activity; a context-size line with clear/compact markers; a sessions table; an "insights" text section.
## Acceptance criteria
- AC6.1: Token totals in tokens.json equal an independent recomputation from the raw jsonl (test).
- AC6.2: No duplicate message IDs are counted.
- AC6.3: Every message has a phase and an activity.
- AC6.4: Page loads with no console errors (Playwright).
