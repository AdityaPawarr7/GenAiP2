# Phase 1: Data collection
## Input
`data/institutions_seed.md` (~42 schools). Adi may edit it before you start.
## Tasks
1. Build `data/institutions.csv` with columns: `slug,name,type(private_r1|public_r1|other),state,cs_dept_url`.
2. For each institution, use WebSearch/WebFetch to find (in priority order):
   a. the CS department's official statement or policy on AI/genAI,
   b. the university-level genAI guidance for teaching or academic integrity,
   c. one or more intro CS course syllabus AI policies (CS1/CS2),
   d. the software engineering course AI policy (the undergraduate SE course, e.g. "Software Engineering", "Software Design").
3. Save `data/raw/<slug>.md` with this exact structure:
   ```
   # <Name>
   retrieved: YYYY-MM-DD
   ## dept_statement
   url: ... | not_found
   > verbatim excerpt(s), max ~150 words each
   ## university_guidance
   ## intro_course
   course: <code + title>
   ## se_course
   course: <code + title>
   ## notes
   ```
4. Work in **batches of 10 institutions**. After each batch, append to PROGRESS.md, then stop so Adi can decide whether to /clear. This saves tokens.
5. Do NOT paraphrase inside `>` blocks. Use verbatim text only. If a page is blocked, record `blocked` and try one alternative source.
## Acceptance criteria
- AC1.1: `institutions.csv` has 35 or more rows, unique slugs, and a valid `type`.
- AC1.2: Every slug has a `data/raw/<slug>.md` file with all 5 section headers.
- AC1.3: Every section has a `url:` line that is either an http(s) URL or `not_found`/`blocked`.
- AC1.4: Every section with a URL has at least one `>` quote block.
- AC1.5: At least 70% of institutions have a URL for at least one of the dept_statement/university_guidance sections.
- AC1.6: At least 50% of institutions have a URL for se_course.
- AC1.7 (spot check, manual): Adi opens 5 random URLs and confirms that the quotes match. Log the result in PROGRESS.md.
