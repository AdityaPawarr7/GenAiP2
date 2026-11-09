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

## Phase 2 coding conventions (Claude, from the defaults Adi approved 2026-11-09)
These apply to both Claude's coding and Adi's blind hand-coding.
- **Evidence source:** only `> ` quotes under a section with a real URL. Notes, LIMITATION and Decision lines are context, never evidence. Each evidence string sits on one line of the raw file.
- **policy_level:** `dept` if dept_statement has a URL; else `university` if university_guidance has one; else `course_only` if any course section has one; else `none_found`.
- **Precedence for default_rule, stance, disclosure_required:** dept_statement first, then university_guidance. Use the intro course(s) only when neither official layer addresses the field.
- **default_rule:** `banned` when the official text states a default prohibition ("not allowed unless the instructor permits"); `instructor_discretion` when it leaves the rule to instructors without stating a default (also when it only likens AI to "help from another person"); `allowed_with_disclosure` / `allowed_encouraged` when it states a permissive default.
- **stance:** tone of the same governing text. Default bans are at most −1; a department listing AI use itself as an integrity violation is −2. "Supports … while recognizing concerns" is 0; "encourages" / "focus on positive potential" / "discourage blanket bans" is +1.
- **collaboration_framing:** true if any URL-section quote calls AI a tutor, partner, pair programmer or teammate, or likens it to a human helper in order to permit or guide use (e.g., "treat it like collaboration with another person"). Likening AI to a person only to restrict it as unauthorized assistance does not count.
- **disclosure_required:** `yes` if the governing text requires students to cite, acknowledge or document AI use; `no` only if it explicitly says disclosure is not needed; otherwise `unclear` (including "instructors should consider requiring").
- **se_course_policy:** `integrated` if AI use is required in some work or learning to use AI is a stated course goal; `allowed` if allowed on most graded coding work; `limited` if allowed only for some tasks or with tight conditions; `banned`; `not_found` if the section is not_found or blocked.
- **themes** (explicitly present in any URL-section quote): academic_integrity = integrity, honor code, cheating, plagiarism, misconduct, (un)authorized use; learning_outcomes = AI's effect on learning or skills; career_readiness = workplace, professional or industry practice; specific_tools = names a genAI product (ChatGPT, Copilot, Claude …; detectors such as TurnItIn don't count); equity_access = fairness, access, cost or bias against groups; privacy_security = data privacy or confidentiality; assessment_redesign = changing grading or assessment design because of AI; ai_literacy = learning to use, verify or critically evaluate AI.
