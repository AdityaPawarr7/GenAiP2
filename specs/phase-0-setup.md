# Phase 0: Setup and logging check
## Tasks
1. Create `requirements.txt` (requests, beautifulsoup4, pytest) and `.gitignore` (venv, __pycache__, .DS_Store).
2. Run `git init` with first commit "Phase 0 scaffold".
3. Verify that the hooks are writing to `logs/events.jsonl` (the prompt that started this phase should already be logged).
4. Write `tests/test_phase0_setup.py`.
## Acceptance criteria (each one is a test)
- AC0.1: All files listed in SPEC.md's architecture exist (dirs + spec files).
- AC0.2: `logs/events.jsonl` exists, and every line is valid JSON with `ts` and `event` keys.
- AC0.3: At least one `UserPromptSubmit` event has been logged.
- AC0.4: `.claude/settings.json` registers the UserPromptSubmit, Stop, PreCompact and SessionStart hooks.
