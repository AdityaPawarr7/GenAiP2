# Phase 2: Coding and analysis
## Tasks
1. Code each `data/raw/<slug>.md` against `specs/codebook.md`. Output `data/processed/policies.json` (a list of records following the codebook schema). Every code has an `evidence` field containing an exact substring of the raw file.
2. `scripts/lexicon_check.py`: counts keywords per institution and flags records where the lexicon disagrees with `stance` (e.g., "prohibit" appears but stance ≥ +1). Output `data/processed/flags.json`.
3. `scripts/sample_for_human.py`: picks a random sample of 10 slugs with a fixed seed of 42. Writes `data/processed/human_coding_template.csv` for Adi to fill in blind, without seeing Claude's codes.
4. `scripts/agreement.py`: after Adi fills `human_coding.csv`, computes percent agreement and Cohen's kappa per field. Output `data/processed/agreement.json`.
5. `scripts/analyze.py`: produces `docs/data/findings.json` with distributions, cross-tabs by type, theme counts, the collaboration-framing share, an SE-course summary, and example quotes.
## Acceptance criteria
- AC2.1: `policies.json` validates against the schema (all required fields present, enums valid).
- AC2.2: Every `evidence` string is an exact substring of the matching raw file (anti-hallucination test).
- AC2.3: Every institution in the CSV has exactly one record.
- AC2.4: The kappa function matches a hand-computed textbook example (unit test).
- AC2.5: The counts in `findings.json` equal counts recomputed directly from `policies.json`.
- AC2.6: The lexicon check runs, and its flags are listed for Adi's review.
