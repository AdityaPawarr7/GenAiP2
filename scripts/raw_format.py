"""Parse data/raw/<slug>.md files into sections of (url, quotes) sources."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
SECTIONS = ["dept_statement", "university_guidance", "intro_course", "se_course", "notes"]
SOURCE_SECTIONS = SECTIONS[:4]
MISSING = ("not_found", "blocked")


def parse_raw(path):
    """Return {section: [{"url": str, "quotes": [str]}]} plus "_headers" (list) and "_meta" (dict)."""
    result = {"_headers": [], "_meta": {}}
    current = None
    quote_lines = None

    def flush_quote():
        nonlocal quote_lines
        if quote_lines is not None and current and result[current]:
            result[current][-1]["quotes"].append(" ".join(quote_lines).strip())
        quote_lines = None

    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+(\w+)\s*$", line)
        if m:
            flush_quote()
            current = m.group(1)
            result["_headers"].append(current)
            result[current] = []
            continue
        if current is None:
            m = re.match(r"^(retrieved):\s*(.+)$", line)
            if m:
                result["_meta"][m.group(1)] = m.group(2).strip()
            continue
        if line.startswith(">"):
            if quote_lines is None:
                quote_lines = []
            quote_lines.append(line[1:].strip())
            continue
        flush_quote()
        m = re.match(r"^url:\s*(\S+)", line)
        if m:
            result[current].append({"url": m.group(1), "quotes": []})
    flush_quote()
    return result


def has_url(sources):
    return any(s["url"].startswith(("http://", "https://")) for s in sources)
