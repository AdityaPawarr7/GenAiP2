# Northeastern University
retrieved: 2026-11-09
## dept_statement
url: not_found

## university_guidance
url: https://provost.northeastern.edu/wp-content/uploads/2025/07/Standards-and-Recommendations-for-the-Use-of-Generative-AI-in-Teaching-and-Learning-at-Northeastern-FINAL-07.01.25.pdf
source_date: 2025 "Published 7/1/2025"
> AI systems—referring primarily, though not exclusively, to generative AI tools in this document—can be of great value in creating new opportunities for learning and building AI skills that students will need in the workplace. However, the use of AI in teaching and learning contexts presents challenges, including overreliance that interferes with building foundational knowledge, use without appropriate oversight or attribution, as well as policy and legal compliance issues.

> 1. The university supports faculty autonomy in determining appropriate AI use in their courses.

> 2. Instructors should clearly communicate to students the permitted uses of generative AI in coursework. This communication should be written in the syllabus, assignment guidelines, and conveyed verbally in class (see suggested strategies below).

> If AI use is allowed on assignments, instructors should consider requiring students to disclose how they use it.

> At present, AI detection tools are unreliable and generate false positives; as such, these tools are not recommended to check for student AI use.

url: https://osccr.sites.northeastern.edu/academic-integrity-policy/
source_date: undated
> The University defines cheating as using or attempting to use unauthorized materials, information, or study aids in any academic exercise.

> Unauthorized use of aids such as but not limited to notes, text, the Internet, artificial intelligence, chatbots, cell phones, etc. to complete any academic assignment.

url: https://policies.northeastern.edu/policy125/
source_date: 2025 "Issued: March 31, 2025"
> Artificial Intelligence (“AI”) offers opportunities for enhancing invention, creativity, discovery, effectiveness and efficiency in teaching, research, and administration (“University Operations”)

> Any faculty or staff member seeking to incorporate the use of an AI System in University Operations or Outside Professional Activities must:

## intro_course
course: CS 2000 Introduction to Program Design and Implementation (public resources site)
url: https://neu-pdi.github.io/cs2000-public-resources/syllabus
source_date: undated
> AI coding assistants like Cursor, Windsurf, and Copilot should not be used in this course. We believe that using an AI assistant is an important skill that should be covered after the basics (which is why there is a different policy in CS 3100).

> The same is true of asking questions of chat models like ChatGPT, Claude, Gemini, etc. Putting assignment instructions into such a model and getting out code or test cases amounts to getting the model to do the thinking for you — and as a result, you will not learn.

> Part of the reason for these being guidelines, rather than academic integrity policies, is that some interaction with LLMs is now unavoidable

course: CS 2100 Program Design and Implementation I (public resources site, "26fa" version)
url: https://neu-pdi.github.io/cs2100-public-resources/syllabus
source_date: undated
> AI coding assistants like Cursor, Windsurf, and Copilot should not be used in this course. We believe that using an AI assistant is an important skill that should be covered after the basics (which is why there is a different policy in CS 3100).

> You may use AI language models for non-assignment-related things.

> If an instructor is suspicious of a student's overuse of AI, they may ask to meet with the student and have them explain their code. The student must fully understand all code that they have submitted.

## se_course
course: CS 4530 Fundamentals of Software Engineering, Fall 2026
url: https://neu-se.github.io/CS4530-Fall-2026/policies/ai
source_date: 2026 "CS4530, Fall 2026"
> We ask for written reflections to understand your own thought process and practice communication, not because we want to read lots of LLM output. Please show respect and do not use LLM-based tools to generate your written assignments.

> For IP1, IP2, and Activities: The use of Artificial Intelligence (AI) tools is forbidden .

> For IP3 and the Team Project: The following policy is a draft . We solicit feedback from students who have already used AI tools in their programming. The use of Artificial Intelligence (AI) tools is permitted , subject to the following:

> Each team should have a common policy about the use of AI in their project.

> “Vibe” coding, in which the AI writes large chunks of code without supervision, is strongly discouraged .

> Treat it like a very junior (but over-eager) engineer, who needs constant supervision and frequent correction.

## notes
dept_statement: no Khoury College-level genAI policy for students found. Checked khoury.northeastern.edu/ai (program/research marketing page, no policy), a guessed Khoury academic-integrity URL (404), and several web searches; Khoury course policies appear to be set per course on top of university policy. Recorded not_found.
university_guidance: (1) Provost "Standards and Recommendations for the Use of Generative AI in Teaching and Learning at Northeastern" (Published 7/1/2025). It is a PDF (the only form linked from Policy 125 and the CATLR page), so check_quotes reports SKIP; text extracted with pypdf in the scratchpad only and quotes copied from that text (PDF line wraps joined). (2) OSCCR Academic Integrity Policy (HTML, undated): lists unauthorized use of "artificial intelligence, chatbots" as cheating. (3) Policy 125 "Policy on the Use of Artificial Intelligence Systems" (issued March 31, 2025): LIMITATION: it governs faculty and staff use of AI in university operations (attribution, accuracy, non-discrimination, AI Review Committee approval), not student coursework; it is included because it is the governing policy that the teaching Standards implement. Default rule: instructor discretion. The CATLR "Northeastern Guidance on AI in Teaching and Learning" page only links to these provost documents.
intro_course: Khoury's current intro sequence is CS 2000 (CS1, Pyret then Python) and CS 2100 (CS1.5/CS2, Program Design and Implementation I), followed by CS 3100 (PDI 2). Both public syllabi ban AI coding assistants and chat models for assignments, with an explicit note that CS 3100 has a different (more permissive) policy; the CS 2000 page says these are "guidelines, rather than academic integrity policies". Term: neither page shows a full-year term in its text; the CS 2100 site has a version selector whose current version is "26fa" (also 26su, 26sp, 25fa), which suggests Fall 2026 but does not contain the year in full, so source_date is undated (judgement call for Adi). CS 2000 page shows only a copyright year (ignored). CS 3100 public syllabus (neu-pdi.github.io/cs3100-public-resources/syllabus) returned HTTP 404, so its AI policy was not captured. The older Fundies sites (course.ccs.neu.edu/cs2500, cs2510) have no AI policy text (cs2510 page is Summer 2025). "obselete" is a typo on the CS 2100 page (not quoted).
se_course: CS 4530 Fundamentals of Software Engineering, Fall 2026 course site (Adeel Bhutta and Mitch Wand). Split policy: AI forbidden for IP1, IP2 and activities (LLM chat allowed only as a search substitute for learning, no copy-paste); permitted for IP3 and the team project under a policy explicitly labelled "draft"; LLMs not to be used for written reflections. Spaces before "." / "," in quotes ("forbidden .", "draft .", "permitted ,", "discouraged .") come from bold/emphasis markup in the page text and are kept as extracted. The page's "Last updated" stamp is a site build time (changes on each rebuild), so source_date uses the "CS4530, Fall 2026" title instead. Fall 2025 version of the same course forbade AI for individual projects.
