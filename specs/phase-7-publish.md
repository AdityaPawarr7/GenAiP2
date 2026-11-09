# Phase 7: Publish
1. Check `gh auth status`. If it is not logged in, ask Adi to run `gh auth login`.
2. Create a public repo named `genai-cs-policies` and push.
3. Enable GitHub Pages from `/docs` on main. Add the live URL to the README.
4. README: project overview, links to the 4 dashboards, how to reproduce (`pip install -r requirements.txt`, the scripts in order, pytest), and the agentic workflow description.
## Acceptance criteria
- AC7.1: The live URL returns 200 for all 5 pages (checked with curl).
- AC7.2: Every relative link on the site resolves (link-checker test).
