# PROGRESS.md

## Current State / Handoff
- **Current phase:** Phase 0 complete and approved by Adi. Next is Phase 1 (data collection), which has not started.
- **Done:** requirements.txt, .gitignore, and .venv (Python 3.9.6 with pytest 8.4.2, requests 2.32.5, bs4 4.15.0). Hooks verified writing to logs/events.jsonl. tests/test_phase0_setup.py covers AC0.1–AC0.4. Git initialised with commit f1ed5c6 "Phase 0 scaffold".
- **Next:** read specs/phase-1-data.md (plus specs/codebook.md and data/institutions_seed.md), restate the Phase 1 acceptance criteria, propose a plan, and wait for Adi's "go".
- **Tests:** 6/6 passing (`.venv/bin/pytest -v`), as of 2026-11-09 15:03 ET.
- **Open questions:** none.
- **Gotchas:** the project lives in iCloud Drive, so the path contains spaces and an apostrophe. Always quote paths. Use `.venv/bin/pytest` and `.venv/bin/python`, because system python3 has no pytest. The system Python is 3.9, so avoid 3.10+ syntax (`match`, `X | Y` type hints). AC0.1 checks dirs and spec/doc files only; later-phase outputs (institutions.csv, policies.json, docs/*.html) are not checked yet. The PROGRESS.md and SPEC.md updates from prepare-to-clear are not committed yet (Adi has not asked for a commit).

---

## Log
- [2026-11-09] [setup] [Adi] Chose the workflow (Adi drives Claude Code), the scope (~40 institutions), and the stack (Python + static GitHub Pages site).
- [2026-11-09] [setup] [Claude-Cowork] Wrote CLAUDE.md, SPEC.md, the phase specs, the codebook, and the logging hooks.
- [2026-11-09 14:55 ET] [phase-0] [Adi] Reviewed and approved the Phase 0 plan (plan-mode approval in Claude Code).
- [2026-11-09 14:56 ET] [phase-0] [Claude] Created requirements.txt (requests, beautifulsoup4, pytest), .gitignore, and a .venv on Python 3.9.6 (pytest 8.4.2, requests 2.32.5, bs4 4.15.0).
- [2026-11-09 14:57 ET] [phase-0] [Claude] Confirmed hooks write to logs/events.jsonl (SessionStart + UserPromptSubmit present). Wrote tests/test_phase0_setup.py (6 tests covering AC0.1–AC0.4); 6/6 pass.
- [2026-11-09 14:58 ET] [phase-0] [Claude] git init + first commit "Phase 0 scaffold".
- [2026-11-09 15:03 ET] [phase-0] [Adi] Reviewed Phase 0 and approved it. Flagged that PROGRESS.md looked un-updated (the stale handoff block), and asked to prepare to clear.
- [2026-11-09 15:03 ET] [phase-0] [Claude] Prepare to clear: updated the handoff block, ticked Phase 0 in SPEC.md, and re-ran the suite (6/6 pass).
