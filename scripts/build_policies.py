"""Assemble data/processed/policies.json from Claude's hand-coded batches.

Hand codes live in data/processed/coding/batch*.json (every codebook field except
source_date). This script copies source_date per section from data/raw/<slug>.md
(never typed by hand), checks each evidence string against the raw file, and
writes the records sorted in institutions.csv order.

Usage: python3 scripts/build_policies.py
"""
import csv
import json
import sys
from pathlib import Path

from raw_format import RAW_DIR, ROOT, SOURCE_SECTIONS, has_url, parse_raw, parse_source_date

CODING_DIR = ROOT / "data" / "processed" / "coding"
OUT_PATH = ROOT / "data" / "processed" / "policies.json"
CSV_PATH = ROOT / "data" / "institutions.csv"


def section_source_date(sources):
    """Most recent year among a section's dated URL sources, "undated", or None (no URL)."""
    url_sources = [s for s in sources if s["url"].startswith(("http://", "https://"))]
    if not url_sources:
        return None
    years = []
    for s in url_sources:
        parsed = parse_source_date(s.get("source_date"))
        if parsed and parsed[0] != "undated":
            years.append(parsed[0])
    return max(years) if years else "undated"


def source_dates(slug):
    raw = parse_raw(RAW_DIR / f"{slug}.md")
    return {sec: section_source_date(raw.get(sec, [])) for sec in SOURCE_SECTIONS}


def evidence_quotes(slug):
    """All quotes under URL sources of the four source sections (notes excluded)."""
    raw = parse_raw(RAW_DIR / f"{slug}.md")
    quotes = []
    for sec in SOURCE_SECTIONS:
        for s in raw.get(sec, []):
            if has_url([s]):
                quotes.extend(s["quotes"])
    return quotes


def evidence_problems(record):
    text = (RAW_DIR / f"{record['slug']}.md").read_text(encoding="utf-8")
    quotes = evidence_quotes(record["slug"])
    problems = []
    for key, ev in record["evidence"].items():
        if ev not in text:
            problems.append(f"{record['slug']}.{key}: not a substring of the raw file")
        elif not any(ev in q for q in quotes):
            problems.append(f"{record['slug']}.{key}: not inside a quote under a URL source")
    return problems


def load_coded():
    records = []
    for path in sorted(CODING_DIR.glob("batch*.json")):
        records.extend(json.loads(path.read_text(encoding="utf-8")))
    return records


def main():
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        order = [r["slug"] for r in csv.DictReader(f)]
    records = load_coded()
    problems = []
    for r in records:
        r["source_date"] = source_dates(r["slug"])
        problems.extend(evidence_problems(r))
    records.sort(key=lambda r: order.index(r["slug"]) if r["slug"] in order else len(order))
    OUT_PATH.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(records)} records to {OUT_PATH.relative_to(ROOT)}")
    for p in problems:
        print("EVIDENCE PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
