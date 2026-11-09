# Phase 4: Validation pipeline and dashboard (`docs/validation.html`)
## Tasks
1. `scripts/run_validation.py`: runs the full pytest suite with JSON output (pytest-json-report, or junitxml converted to JSON). Writes `docs/data/tests.json` with fields: id, phase, acceptance_criterion, name, file, status, duration, message, timestamp, run_id. Appends a run summary to `docs/data/test_runs.json` (history).
2. Map each test to its AC through its name (`test_ac2_2_...`) or a pytest marker.
3. `docs/data/reviews.json`: logs Adi's manual reviews (spot checks, code reviews) with date, what was reviewed, method, outcome, and notes.
4. Dashboard views: pass/fail KPIs; a filterable table (search, phase, status, AC); expandable rows showing the failure message and test source file; a pass-rate-over-runs line chart; an AC coverage matrix (each AC → tests → status, with ACs that have no tests highlighted in red); a manual review log; the human–Claude agreement (kappa) panel.
## Acceptance criteria
- AC4.1: Every AC in specs/phase-*.md has at least one test or a manual review entry (checked by a test that parses the specs).
- AC4.2: tests.json matches the actual pytest run (same count, same statuses).
- AC4.3: Filters work (Playwright test).
- AC4.4: Includes at least one deliberately failing "canary" test, run once and shown in the history, to prove that the pipeline reports failures. Then remove it.
