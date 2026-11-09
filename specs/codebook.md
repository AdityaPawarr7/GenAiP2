# Codebook (per institution)
| field | type / values | definition |
|---|---|---|
| slug | str | matches institutions.csv |
| policy_level | dept / university / course_only / none_found | highest official level of AI guidance found |
| default_rule | banned / instructor_discretion / allowed_with_disclosure / allowed_encouraged / unclear | default rule for students in CS courses |
| stance | int −2..+2 | −2 hostile/prohibitive, −1 cautious/restrictive, 0 neutral/procedural, +1 permissive/positive, +2 enthusiastic/encouraging |
| collaboration_framing | bool | text frames AI as collaborator/partner/pair-programmer/tutor (not only as a tool or risk) |
| disclosure_required | yes / no / unclear | must students cite or disclose AI use? |
| se_course_policy | banned / limited / allowed / integrated / not_found | integrated = AI use is taught or required in the course |
| themes | list of: academic_integrity, learning_outcomes, career_readiness, specific_tools, equity_access, privacy_security, assessment_redesign, ai_literacy | themes explicitly present |
| evidence | dict field→verbatim excerpt | one excerpt per non-trivial code |
| source_date | dict section→int year / "undated" / null | per source section (dept_statement, university_guidance, intro_course, se_course): the most recent year among that section's `source_date:` lines in `data/raw/`; "undated" if none of its sources is dated; null if the section has no URL. Copied from the raw file, never inferred. Used in Phase 2 to report policy recency |
| confidence | high / medium / low | Claude's confidence in its coding |
| notes | str | |
Coding rules: code only from text in `data/raw/`. If unsure, use `unclear` and `low`. Do not infer from reputation.
