"""Build docs/data/policies.json for the findings dashboard (Phase 3).

The dashboard may read only docs/data/findings.json and docs/data/policies.json
(specs/phase-3-findings-dashboard.md). data/processed/policies.json has evidence
quotes but no source links, so this script copies each record and attaches, per
evidence key, the raw section, URL, course and source_date of the quote that
contains it (looked up in data/raw/<slug>.md, URL sources only, never notes).
It also adds the Method facts: retrieval dates and the agreement summary.
Nothing in data/processed/ is changed.

Usage: python3 scripts/build_dashboard_data.py
"""
import json
import re
import sys
from pathlib import Path

from codebook_schema import load_institutions
from raw_format import RAW_DIR, ROOT, SOURCE_SECTIONS, parse_raw

POLICIES_PATH = ROOT / "data" / "processed" / "policies.json"
AGREEMENT_PATH = ROOT / "data" / "processed" / "agreement.json"
OUT_PATH = ROOT / "docs" / "data" / "policies.json"


def section_courses(path):
    """{section: [course line or None per url source]} in file order (the parser drops course lines)."""
    out, current, pending = {}, None, None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+(\w+)\s*$", line)
        if m:
            current, pending = m.group(1), None
            out[current] = []
            continue
        if current is None:
            continue
        m = re.match(r"^course:\s*(.+?)\s*$", line)
        if m:
            pending = m.group(1)
            continue
        if re.match(r"^url:\s*\S+", line):
            out[current].append(pending)
    return out


def url_sources(slug):
    """Flat list of URL sources with section, course and quotes, in raw-file order."""
    path = RAW_DIR / f"{slug}.md"
    raw = parse_raw(path)
    courses = section_courses(path)
    sources = []
    for sec in SOURCE_SECTIONS:
        last_course = None
        for i, s in enumerate(raw.get(sec, [])):
            course = courses.get(sec, [None] * (i + 1))[i] or last_course
            last_course = course
            if not s["url"].startswith(("http://", "https://")):
                continue
            sources.append({
                "section": sec,
                "url": s["url"],
                "course": course,
                "source_date": s.get("source_date"),
                "quotes": s["quotes"],
            })
    return sources


def find_source(evidence, sources):
    for s in sources:
        for q in s["quotes"]:
            if evidence in q:
                return s, q
    return None, None


def enrich(record):
    sources = url_sources(record["slug"])
    out = dict(record)
    items = []
    for key, ev in record["evidence"].items():
        src, quote = find_source(ev, sources)
        items.append({
            "key": key,
            "evidence": ev,
            "quote": quote,
            "section": src["section"] if src else None,
            "url": src["url"] if src else None,
            "course": src["course"] if src else None,
            "source_date": src["source_date"] if src else None,
        })
    out["evidence_sources"] = items
    return out


def agreement_summary():
    if not AGREEMENT_PATH.exists():
        return None
    data = json.loads(AGREEMENT_PATH.read_text(encoding="utf-8"))
    summary = {}
    for pair in ("human_vs_claude", "ai2_vs_claude"):
        block = data.get(pair)
        if not block:
            continue
        summary[pair] = {
            "status": block.get("status"),
            "n_institutions": block.get("n_institutions"),
            "slugs": block.get("slugs"),
            "fields": block.get("fields"),
        }
    return summary


def build():
    types = {r["slug"]: r for r in load_institutions()}
    policies = json.loads(POLICIES_PATH.read_text(encoding="utf-8"))
    records, retrieved = [], []
    for p in policies:
        rec = enrich(p)
        inst = types.get(p["slug"], {})
        rec["name"] = inst.get("name")
        rec["type"] = inst.get("type")
        records.append(rec)
        r = parse_raw(RAW_DIR / f"{p['slug']}.md")["_meta"].get("retrieved")
        if r:
            retrieved.append(r)
    return {
        "source": "data/processed/policies.json + source links from data/raw (scripts/build_dashboard_data.py)",
        "n": len(records),
        "retrieved": {"min": min(retrieved), "max": max(retrieved)} if retrieved else None,
        "agreement": agreement_summary(),
        "records": records,
    }


def main():
    data = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    missing = [f"{r['slug']}.{e['key']}" for r in data["records"] for e in r["evidence_sources"] if not e["url"]]
    print(f"wrote {data['n']} records to {OUT_PATH.relative_to(ROOT)}")
    for m in missing:
        print("NO SOURCE:", m)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
