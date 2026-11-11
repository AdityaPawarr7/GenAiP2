# GenAI policies in CS education

How do US computer science departments handle generative AI? This project reads the official AI language of 42 US CS departments, their universities, and their intro and software engineering courses, codes it against a fixed codebook, and publishes the results as static dashboards. Every code cites a verbatim quote with its source URL.

**Live site:** https://adityapawarr7.github.io/GenAiP2/ ([Findings](https://adityapawarr7.github.io/GenAiP2/findings.html) · [Validation](https://adityapawarr7.github.io/GenAiP2/validation.html) · [Timeline](https://adityapawarr7.github.io/GenAiP2/timeline.html) · [Tokens](https://adityapawarr7.github.io/GenAiP2/tokens.html) · [Reflection](https://adityapawarr7.github.io/GenAiP2/reflection.html))

**Full write-up:** see [Project report](#project-report) below.

**Video walkthrough:** coming soon <!-- Replace this line with: [Watch on YouTube](https://www.youtube.com/watch?v=YOUR_VIDEO_ID) -->

Headline findings: only 4 of 42 CS departments publish their own generative AI statement, and 32 of 42 (76%) leave the rules to each instructor.

## Dashboards

| Dashboard | Page | Status |
|---|---|---|
| Findings | [`docs/findings.html`](docs/findings.html) | Live |
| Validation | [`docs/validation.html`](docs/validation.html) | Live |
| Contributions timeline | [`docs/timeline.html`](docs/timeline.html) | Live |
| Token usage | [`docs/tokens.html`](docs/tokens.html) | Live |
| Reflection (Phase 8, by Adi) | [`docs/reflection.html`](docs/reflection.html) | Live |

The landing page is [`docs/index.html`](docs/index.html). The site is plain HTML, CSS and JavaScript with Chart.js 4.4.1 vendored in `docs/assets/vendor/`; each page reads JSON from `docs/data/`.

## Project report

Figures come from the data files in `docs/data/` as last rebuilt on 2026-11-10. Each subsection links to the dashboard that shows the full detail.

### 1. Research questions and method

- **RQ1:** How are students permitted or encouraged to use genAI in CS courses?
- **RQ2:** What tone do official statements take on AI?
- **RQ3:** Do they frame AI as a collaborator?
- **RQ4:** How do software engineering (SE) courses handle AI?
- **RQ5:** Do patterns differ by institution type?

**Sample.** 42 US institutions: 16 private R1, 23 public R1 and 3 others (Harvey Mudd, Williams, Cal Poly SLO). For each one, the agent searched for four sources: the CS department's own statement, university-level guidance, intro CS syllabi (CS1/CS2), and the undergraduate SE course syllabus. Every source is saved in `data/raw/<school>.md` with its URL, retrieval date, a `source_date`, and verbatim quotes only. A source that could not be found is recorded as `not_found` or `blocked`, never guessed.

**Approach: qualitative content analysis with a fixed codebook** (`specs/codebook.md`). Claude coded each school on these fields:

- policy level
- default rule
- stance (−2 to +2)
- collaboration framing
- disclosure required
- SE course policy
- themes

Every code cites an evidence quote, and a test checks that each quote is an exact substring of the raw file. Three checks back up the coding:

1. **Human check:** Adi blind-coded 5 randomly sampled schools.
2. **Second AI coder:** a separate Claude session, which never saw Claude Code's codes, coded 10 schools.
3. **Keyword check:** a script flags codes that seem to contradict the wording of the text (29 flags raised for review).

### 2. Findings ([dashboard](https://adityapawarr7.github.io/GenAiP2/findings.html))

- **Departments rarely speak for themselves.** Only **4 of 42** CS departments publish their own genAI statement (UW, Harvard SEAS, UMD, and BU's Computing & Data Sciences). The other 38 defer to university guidance or course syllabi.
- **The rule is "ask your instructor."** **32 of 42 (76%)** leave AI use to each instructor. 8 ban it unless the instructor permits it, 2 allow it with disclosure, and **none** encourage it by default.
- **The tone is neutral to cautious, not enthusiastic.** 24 neutral, 10 cautious, 1 hostile, 7 positive, 0 enthusiastic. The mean stance is −0.12: private R1s average 0.00, public R1s −0.17.
- **About a quarter talk about AI as a collaborator** (tutor, partner, pair programmer): **11 of 42 (26%)**, more often at private R1s (6/16) than public R1s (4/23).
- **Disclosure is half-settled.** 21 schools require students to disclose or cite AI use; for the other 21 it is unclear.
- **SE courses are where AI gets built in.** 23 schools had a findable SE course policy. Of those, 12 limit AI, **6 build it into the course** (CMU, Princeton, UT Austin, Virginia Tech, NC State, Brown), 3 allow it and 2 ban it.
- **Themes:** academic integrity (37), specific tools named (34), learning outcomes (31), AI literacy (15), career readiness (6), equity (4), privacy (3), assessment redesign (2). Policies talk about integrity and learning far more than about preparing students for AI-assisted careers.
- **Recency:** of 41 university guidance pages, 18 are dated 2026, 3 still date from 2023, and 15 are undated.

### 3. Agentic workflow

The project was built by Claude Code under Adi's supervision, following a spec-driven loop:

1. `SPEC.md` holds the goals, research questions and architecture, and `CLAUDE.md` holds the agent's rules.
2. Each phase (0–8) has its own spec in `specs/phase-N-*.md` with numbered acceptance criteria (ACs).
3. For each phase, Claude read only that spec, restated the ACs, proposed a plan, and waited for Adi's "go".
4. After building, it ran the tests, logged the work to `PROGRESS.md`, and waited for Adi's review.
5. On **"prepare to clear"**, Claude updated the handoff block in `PROGRESS.md` and the checkboxes in `SPEC.md`, then Adi ran `/clear`. The next session restarted from the files, not from memory.
6. Hooks in `.claude/settings.json` logged every prompt, response and `/clear` to `logs/events.jsonl` automatically, so the record does not depend on the agent remembering to write it.

Planning, spec drafting and some reviews happened in a separate Claude (Cowork) chat, which appears as **Claude-Cowork** in the logs.

### 4. Validation evidence ([dashboard](https://adityapawarr7.github.io/GenAiP2/validation.html))

- **777 pytest tests:** 771 passed, 0 failed, 6 skipped. The skipped ones are live-site checks that run only with `CHECK_LIVE=1`, and they pass there (19/19).

  | Phase | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
  |---|---|---|---|---|---|---|---|---|---|
  | Tests | 6 | 219 | 305 | 76 | 49 | 48 | 44 | 20 | 10 |

- **Every AC is covered** by at least one test, or by a logged manual review where a test can't do the job (AC1.7, Adi's browser spot check: 5/5 quotes matched). A test parses the specs to enforce this.
- **The pipeline is proven to report failures.** A deliberate "canary" test was run once and appears as a red run in the history of 16 validation runs. Four other runs failed for real during development and were fixed, and they are kept in the history rather than deleted.
- **Anti-hallucination checks:** every evidence quote must be an exact substring of its raw source. `scripts/check_quotes.py` re-fetches the live pages to confirm the quotes; pages that block scripts were checked against saved copies.
- **Agreement with independent coders:**

  | Field | Human vs Claude (n=5) | Second AI vs Claude (n=10) |
  |---|---|---|
  | Policy level | 100% (κ 1.00) | 100% (κ 1.00) |
  | Default rule | 80% (κ 0.55) | 90% (κ 0.63) |
  | Stance | **0%** (weighted κ 0.17) | 100% (κ 1.00) |
  | Collaboration framing | 80% (κ 0.62) | 100% (κ 1.00) |
  | Disclosure required | 40% (κ 0.06) | 100% (κ 1.00) |
  | SE course policy | 60% (κ 0.41) | 100% (κ 1.00) |

  The two AIs agree almost perfectly. That shows the coding is *consistent*, but the number is inflated, because the second coder used codebook conventions written from these same cases. The human disagrees most on **tone** and **disclosure**. Adi decided not to recode to chase agreement, and the result is reported as a finding: tone is the subjective part of this analysis.
- **Mistakes caught in review**, all logged in `docs/data/reviews.json`:
  - Adi caught that Claude Code had not updated `PROGRESS.md` in Phase 0.
  - Claude-Cowork found subagent results being logged as Adi's prompts, and the hook was patched.
  - Claude Code refused to log a review containing unfilled placeholders.
  - A pre-publish privacy scan removed the home path and emails from the published files.

### 5. Contributions ([timeline](https://adityapawarr7.github.io/GenAiP2/timeline.html))

| Actor | Contribution |
|---|---|
| **Adi** | 42 prompts; 21 decisions, including scope, the coding rules, keeping the codes unchanged and the privacy calls; 8 reviews; 3 corrections; manual data work, including pasting the blocked University of Michigan pages, the AC1.7 spot check, and blind coding. Adi also wrote the reflection. Ran all 10 `/clear`s and approved every phase before it was committed. |
| **Claude Code** | Wrote all the code (about 9,200 lines added), collected and coded the data (about 31,000 lines of data files), wrote the tests, and kept the logs. It used 21 subagents in Phase 1 for parallel data collection. |
| **Claude-Cowork** | Drafted the initial specs, the codebook and the logging hooks; reviewed batches and plans; built the blind human-coding form; acted as the independent second AI coder; imported the dataviz skill. |

The authoritative record is the timeline built from `logs/events.jsonl`, `PROGRESS.md` and the git history. Hook timestamps take precedence over hand-written ones.

### 6. Token usage ([dashboard](https://adityapawarr7.github.io/GenAiP2/tokens.html))

- **About 157M tokens** across 1,527 API calls in 11 Claude Code sessions. That is about $72 at API list prices; the project actually ran on a $20/month Pro plan. **97% of tokens were cache reads**, meaning context re-read on every step.
- **By activity:**

  | Activity | Tokens | Share |
  |---|---|---|
  | Gathering data | 81.5M | 52% |
  | Running validation | 46.3M | 29% |
  | Planning and docs | 10.7M | 7% |
  | Writing code | 9.7M | 6% |
  | Processing data | 9.2M | 6% |

  Writing code was one of the cheapest steps; reading web pages and re-running checks dominated.
- **Phase 1 (data collection) used 100M tokens, 64% of the total.** 88.6M of that came from 21 parallel subagents. Fetching web pages is what fills the context.
- **`/clear` works.** Across 10 clears, the average context per call fell from **about 166K to 52K tokens**, an estimated 29.6M tokens that were not re-read. `/compact` was never used, so there is no measured comparison for it.
- Not measured: tokens used in the Claude-Cowork planning chat.

### 7. Limitations

- The sample leans toward R1 universities, with only 3 non-R1 schools.
- Department statements may exist on pages the search did not find.
- 19 of 42 SE course policies were not found or were behind a login.
- The source URL for the Michigan faculty guidance is unconfirmed.
- The human check covers only 5 schools, and the AI–AI agreement is inflated (see section 4).
- Stance is subjective.
- Policies change; everything here reflects pages retrieved on 2026-11-09.

### 8. Evaluation and reflection

Adi's reflection on the project and on agentic vs. AI-assisted development, written by Adi, is on the [reflection page](https://adityapawarr7.github.io/GenAiP2/reflection.html).

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
