# Phase 3: Findings dashboard (`docs/findings.html`)
Reads only `docs/data/findings.json` and `policies.json` (copied to `docs/data/`).
## Required views
1. KPI row: number of institutions, % with a dept-level policy, % that encourage AI, % with collaboration framing.
2. Default rule distribution (bar chart).
3. Stance distribution (−2..+2), plus stance by institution type (grouped bar).
4. SE course policy distribution, plus a callout listing the "integrated" courses.
5. Theme frequency (horizontal bar).
6. Searchable and filterable table of all institutions (type, rule, stance, SE policy). Clicking a row shows its evidence quotes with source links.
7. A "Method & limitations" section (sample, coding approach, human-agreement kappa, date of retrieval).
## Acceptance criteria
- AC3.1: The page loads with no console errors (headless Playwright test).
- AC3.2: Every chart total equals the matching count in findings.json (Playwright reads the DOM/chart data).
- AC3.3: The table row count equals the number of institutions. Search filters the rows correctly.
- AC3.4: Works at 375px width with no horizontal scrolling.
