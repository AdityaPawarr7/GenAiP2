# PROGRESS.md

## Current State / Handoff
- **Current phase:** Phase 0 (setup)
- **Done:** scaffold, specs, CLAUDE.md, and logging hooks were created by Claude in Cowork on Adi's direction
- **Next:** Adi opens Claude Code in this folder and runs Phase 0
- **Tests:** none yet
- **Open questions:** none
- **Gotchas:** the project lives in iCloud Drive, so the path contains spaces and an apostrophe. Always quote paths.

---

## Log
- [2026-11-09] [setup] [Adi] Chose the workflow (Adi drives Claude Code), the scope (~40 institutions), and the stack (Python + static GitHub Pages site).
- [2026-11-09] [setup] [Claude-Cowork] Wrote CLAUDE.md, SPEC.md, the phase specs, the codebook, and the logging hooks.
- [2026-11-09 14:55 ET] [phase-0] [Adi] Reviewed and approved the Phase 0 plan (plan-mode approval in Claude Code).
- [2026-11-09 14:56 ET] [phase-0] [Claude] Created requirements.txt (requests, beautifulsoup4, pytest), .gitignore, and a .venv on Python 3.9.6 (pytest 8.4.2, requests 2.32.5, bs4 4.15.0).
- [2026-11-09 14:57 ET] [phase-0] [Claude] Confirmed hooks write to logs/events.jsonl (SessionStart + UserPromptSubmit present). Wrote tests/test_phase0_setup.py (6 tests covering AC0.1–AC0.4); 6/6 pass.
- [2026-11-09 14:58 ET] [phase-0] [Claude] git init + first commit "Phase 0 scaffold".
