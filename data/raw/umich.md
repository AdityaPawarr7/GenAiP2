# University of Michigan
retrieved: 2026-11-09
## dept_statement
url: not_found

## university_guidance
url: https://genai.umich.edu/guidance/faculty
source_date: undated
> Policies will vary between campuses, departments, and even individual classes. Each instructor must clearly articulate their own expectations and policies for GenAI use.

> First familiarize yourself with any revised academic integrity policies from your school/college. Then draft a statement in your syllabus on acceptable uses of GenAI in your classroom.

> U-M does not recommend the use of AI-detection technology at this time given their high error rate.

> Common approaches to updating academic misconduct policies are to consider GenAI as prohibited help from another “person” (e.g., UCLA), or as a “source” that should be acknowledged (e.g., UW Madison). The “person” approach misleadingly attributes sentience and a reasoning capacity to GenAI. The “source” approach is more workable.

url: https://genai.umich.edu/node/53
source_date: 2023 "U-M Information and Technology Services • 9/23"
> As these tools become ubiquitous, it is more productive and of better service to students to focus on helping them surpass AI outputs and to use AI assistance responsibly, rather than prohibiting it altogether.

> Course policies might fall into one of three categories: ... Specific uses of GenAI are encouraged (generating ideas, editing, translating, outlining) ... Specific uses of GenAI are allowed if students clearly distinguish between their original work and GenAI output (highlighting output, tracking changes in GenAI output) ... Any use of GenAI constitutes academic misconduct

> Due to a lack of reliability and transparency in the detection process, such detection tools should not be considered a solution or approach to teaching in a GenAI era.

## intro_course
course: EECS 280 Programming and Introductory Data Structures, Fall 2026
url: https://eecs280.org/syllabus.html
source_date: 2026 "The University of Michigan, Fall 2026"
> The use of generative AI tools or AI-assisted code editors (e.g. ChatGPT, Gemini, Claude, Copilot, Cursor, etc.) is permitted only in the same contexts where collaboration with another person is allowed, following the guidelines above.

> Additionally, the use of generative AI in a deceptive or malicious fashion is prohibited. This includes but is not limited to: Impersonating yourself or others in course contexts, for example in emails, virtual office hours, or online course forums. Passing off generated content as your own work when contributing to group assignments.

course: EECS 183 Elementary Programming Concepts, Fall 2026
url: blocked

## se_course
course: EECS 481 Software Engineering, Fall 2026
url: https://eecs481.org/
source_date: 2026 "Lectures and Details (Fall 2026)"
> Students can us free AI tools and support for all assignments (but not examinations) in this course. For equity reasons, we do not allow the use of paid AI.

## notes
LIMITATION: every umich.edu host tried (genai.umich.edu, cse.engin.umich.edu, www.engin.umich.edu, ecas.engin.umich.edu, record.umich.edu, provost.umich.edu, its.umich.edu, crlt.umich.edu, lsa.umich.edu, facultysenate.umich.edu, oscr.umich.edu) returned HTTP 403 to pagetext.py from this environment, so no umich.edu page could be fetched or verified. Course sites hosted off umich.edu (eecs280.org, eecs481.org) were fetchable.
dept_statement: could not inspect cse.engin.umich.edu directly (403). Web searches found no CSE/EECS department-wide genAI policy; a Michigan Daily article (older, date unclear) reported that EECS had not set a department-wide AI policy, and a GovTech article says U-M has no campus-wide AI policy and leaves it to schools/faculty. Recorded not_found, but this rests on search only, not on a direct check of the CSE site; Adi should review (could be re-checked from a browser). LIMITATION (Adi, 2026-11-09): Adi has not checked cse.engin.umich.edu manually; not_found rests on web search only.
university_guidance: genai.umich.edu returns HTTP 403 to pagetext.py, so these sources were captured manually by Adi (2026-11-09) and check_quotes reports them as unverifiable (SKIP). (1) https://genai.umich.edu/guidance/faculty — Adi opened the page in a browser and pasted its text; saved verbatim at data/raw/sources/umich_genai_guidance_faculty.txt (the paste begins mid-word, "niversity of Michigan’s GenAI offerings"). Quotes were copied from that file. The URL is the page the subagent identified as U-M's faculty guidance and the one Adi was asked to open; the pasted text matches that page's topic, but Adi has not yet explicitly confirmed the URL. LIMITATION (Adi, 2026-11-09): Adi could not confirm which URL the pasted text came from; the URL stays marked unconfirmed. (2) "Getting Started with Generative AI: U-M Instructor Guide" (U-M ITS, dated 9/23, PDF metadata 2023-09-27), listed by the subagent at genai.umich.edu/node/53. Adi supplied the PDF; saved at data/raw/sources/umich_genai_instructor_guide_0923.pdf. Text extracted with pypdf (scratchpad only); quotes copied from the extracted text with PDF line wraps joined; the "..." in the three-categories quote stands for the bullet characters between list items. LIMITATION: the instructor guide is from Sept 2023, and the faculty page says misconduct policies "should be updated this summer" (also 2023-era wording), so both may predate current practice. Default rule is instructor discretion; no campus-wide ban or mandate.
intro_course: EECS 280 (CS2-level, Fall 2026 syllabus on eecs280.org; same page is mirrored at eecs280staff.github.io/eecs280.org/syllabus.html). The syllabus also has an Allowed Use / Prohibited Use table (allowed: learning concepts, understanding compiler errors, brainstorming edge cases, generating practice exam questions; prohibited: generating project code or test cases, exhaustive proofreading, asking for test-case lists, use during exams); the table cells interleave in extracted text so they were not quoted. EECS 183 (CS1): eecs183.org timed out (connection timeout) on every attempt and the GitHub-hosted copies tried (eecs183.github.io/...) returned 404; recorded blocked (site unreachable, not login). No alternative EECS 183 source found.
se_course: EECS 481 Software Engineering, Fall 2026 course homepage (eecs481.org), "Free AI Resources" section: free AI tools allowed on all assignments but not exams; paid AI disallowed for equity reasons. "can us" is a typo on the original page.
