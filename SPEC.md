# SPEC.md — Master Specification

## Project goal
Gather and analyze how US computer science departments talk about generative AI (genAI) in their official publications, and how they permit or encourage students to use it in CS and software engineering (SE) courses. Communicate the findings in a web dashboard. Also build web interfaces for (a) validation and test results, (b) human vs. Claude contributions over time, and (c) token usage.

## Research questions
- RQ1: How are students permitted or encouraged to use genAI in CS courses? (default rule: banned, instructor discretion, allowed with disclosure, or encouraged)
- RQ2: What is the overall tone of departments' official language about AI, from negative to positive?
- RQ3: Do policies frame AI as a *collaborator* (pair programmer, tutor) or only as a tool, risk or integrity issue?
- RQ4: How are software engineering courses specifically handling AI? (banned, allowed, or integrated into the curriculum)
- RQ5: Do the patterns differ by institution type? (private R1, public R1, other)

## Analysis approach
**Qualitative content analysis with a fixed codebook, LLM-assisted coding, and human verification.**
1. Collect primary-source text, with URL, retrieval date and verbatim excerpts.
2. Claude codes each institution against the codebook in `specs/codebook.md`.
3. Every coded value must cite an excerpt as evidence (traceability).
4. Adi independently hand-codes a random sample of 10 institutions. We report agreement (percent agreement and Cohen's kappa) between the human and Claude coding as evidence of reliability.
5. A keyword and lexicon cross-check (e.g., "encourage", "prohibit", "collaborat*") flags disagreements between the text and the assigned codes.
6. Summarize with descriptive statistics: distributions, cross-tabs by institution type, and theme frequencies.

## Architecture
```
data/raw/<slug>.md          verbatim excerpts + URLs per institution (Phase 1)
data/institutions.csv       sample list (Phase 1)
data/processed/policies.json  coded records (Phase 2)
scripts/                    collection, coding helpers, analysis, token + log parsers
tests/                      pytest suites (all phases)
docs/                       GitHub Pages site
  index.html                landing page + links
  findings.html             Dashboard 1: research findings
  validation.html           Dashboard 2: tests and validation evidence
  timeline.html             Dashboard 3: contributions and timeline
  tokens.html               Dashboard 4: token usage
  data/*.json               data consumed by the dashboards
logs/events.jsonl           auto-logged prompts/responses/clear/compact (hooks)
PROGRESS.md                 human-readable timestamped log + handoff
```

## Phases (update checkboxes as you go)
- [x] Phase 0: Setup and logging check — `specs/phase-0-setup.md`
- [x] Phase 1: Data collection — `specs/phase-1-data.md` (done: 42/42 schools, AC1.7 spot check 5/5, approved by Adi 2026-11-09)
- [x] Phase 2: Coding and analysis — `specs/phase-2-analysis.md` (42/42 coded, 530 tests pass, agreement reported, committed 2026-11-09)
- [ ] Phase 3: Findings dashboard — `specs/phase-3-findings-dashboard.md`
- [ ] Phase 4: Validation pipeline and dashboard — `specs/phase-4-validation.md`
- [ ] Phase 5: Contributions timeline — `specs/phase-5-timeline.md`
- [ ] Phase 6: Token usage dashboard — `specs/phase-6-tokens.md`
- [ ] Phase 7: Publish (GitHub + Pages) — `specs/phase-7-publish.md`
- [ ] Phase 8: Evaluation and reflection (Adi writes it; Claude supplies numbers) — `specs/phase-8-evaluation.md`

## Deadlines
Nov 10: application · Nov 11: documentation · Nov 12: presentation
