# CLAUDE.md — Project 2: GenAI Policies in CS Education

You are the implementing agent in an **agentic, spec-driven** project. The human (Adi) supervises through specs, tests and reviews, and rarely edits code directly.

## Read first, every session (including after /clear or /compact)
1. `SPEC.md` holds the goals, architecture and phase list.
2. `PROGRESS.md`: read the **Current State / Handoff** block at the top.
3. `specs/phase-N-*.md`: read the spec for the phase you are told to work on, and only that one.

## Working rules
- Work on ONE phase at a time. Do not start the next phase until Adi approves.
- Before writing code for a phase, restate its acceptance criteria and propose a short plan. Wait for "go".
- Every phase must ship with tests (pytest) that map to its acceptance criteria. Test IDs and names must be descriptive, because they are shown in the validation dashboard.
- Never invent data. Every data claim needs a source URL plus a verbatim quote saved in `data/raw/`. If you cannot find a policy, record `not_found`. Do not guess.
- Keep the dashboards static (HTML/CSS/vanilla JS + Chart.js from cdnjs) under `docs/`, reading JSON from `docs/data/`.
- Python 3, standard library + `requests`, `beautifulsoup4`, `pytest` only, unless the spec says otherwise.

## Logging (required, part of the grade)
- Hooks in `.claude/settings.json` auto-log every prompt, response, /clear and /compact to `logs/events.jsonl`. Do not edit or disable them.
- After each meaningful step, append an entry to `PROGRESS.md`:
  `- [YYYY-MM-DD HH:MM ET] [phase-N] [Claude|Adi] what happened (files touched, tests pass/fail)`
- When Adi makes a decision, corrects you, or reviews something, log it as `[Adi]`.

## "Prepare to clear" protocol
When Adi says **"prepare to clear"** (or "prepare to compact"):
1. Update the **Current State / Handoff** block at the top of `PROGRESS.md`: current phase, what is done, what is next, open questions, and any gotchas.
2. Update the status checkboxes in `SPEC.md`.
3. Run the test suite and record the pass/fail count in the handoff.
4. Reply "Ready to clear" with a one-paragraph summary. Then Adi runs /clear.
