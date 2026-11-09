# GenAI policies in CS education

How do US computer science departments handle generative AI? This project reads the official AI language of 42 US CS departments, their universities, and their intro and software engineering courses, codes it against a fixed codebook, and publishes the results as static dashboards. Every code cites a verbatim quote with its source URL.

**Live site:** _(added after GitHub Pages is enabled)_

Headline findings: only 4 of 42 CS departments publish their own generative AI statement, and 32 of 42 (76%) leave the rules to each instructor.

## Dashboards

| Dashboard | Page | Status |
|---|---|---|
| Findings | [`docs/findings.html`](docs/findings.html) | Live |
| Validation | [`docs/validation.html`](docs/validation.html) | Live |
| Contributions timeline | `docs/timeline.html` | Coming soon (Phase 5) |
| Token usage | `docs/tokens.html` | Coming soon (Phase 6) |

The landing page is [`docs/index.html`](docs/index.html). The site is plain HTML, CSS and JavaScript with Chart.js 4.4.1 vendored in `docs/assets/vendor/`; each page reads JSON from `docs/data/`.

## Reproduce

Python 3.9+.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium     # for the browser tests

# 1. Sources (data/raw/<slug>.md) were collected by the agent with scripts/pagetext.py.
#    Re-verify every quote against the live pages (needs network; pages change over time):
python scripts/check_quotes.py

# 2. Coding and analysis
python scripts/build_policies.py          # data/processed/coding/batch*.json -> data/processed/policies.json
python scripts/lexicon_check.py           # keyword cross-check -> data/processed/flags.json
python scripts/agreement.py               # human and second-AI agreement -> data/processed/agreement.json
python scripts/analyze.py                 # -> docs/data/findings.json

# 3. Dashboard data
python scripts/build_dashboard_data.py    # -> docs/data/policies.json
python scripts/run_validation.py          # runs pytest -> docs/data/tests.json, test_runs.json, ...

# 4. Tests only
pytest

# View the site locally
python -m http.server -d docs 8000        # then open http://localhost:8000
```

## How it was built: agentic, spec-driven development

The code, data collection and coding were done by an AI agent (Claude Code). The human (Adi) supervised through specs, tests and reviews and rarely edited code directly.

- **Specs first.** `SPEC.md` sets the goals and architecture; each phase has a spec in `specs/phase-N-*.md` with numbered acceptance criteria (ACs). `CLAUDE.md` holds the agent's working rules.
- **One phase at a time.** For each phase the agent restated the ACs and proposed a plan, then waited for Adi's "go". Adi reviewed every phase before it was committed.
- **Tests map to ACs.** Every phase ships pytest tests named after the AC they check (`test_AC2_2_...`). The [validation dashboard](docs/validation.html) shows each AC, its tests, and the manual reviews that stand in for checks a test can't make (for example, Adi's browser spot check of quotes).
- **No invented data.** Each data claim has a source URL and a verbatim quote in `data/raw/`; a test checks that every evidence string is an exact substring of its raw file. Missing policies are recorded as `not_found`.
- **Independent checks.** Adi blind-coded a sample of schools, and a second AI session coded another sample independently; agreement is reported on the validation dashboard. The two coders differ most on tone (stance), and that disagreement is reported as a finding rather than smoothed over.
- **Everything is logged.** Hooks in `.claude/settings.json` write every prompt, response, `/clear` and `/compact` to `logs/events.jsonl`. `PROGRESS.md` is the human-readable log, with a handoff block the agent updates before each context clear.

## Repository layout

```
SPEC.md, CLAUDE.md, PROGRESS.md   goals, agent rules, timestamped log
specs/                            phase specs and the codebook
data/raw/                         verbatim excerpts + URLs per institution
data/processed/                   coded records, agreement, flags
scripts/                          collection, coding, analysis and validation scripts
tests/                            pytest suites, one per phase
docs/                             the published site (GitHub Pages)
logs/events.jsonl                 hook log of the whole session
tools/                            the blind human-coding form
```
