"""Descriptive statistics from policies.json -> docs/data/findings.json (Dashboard 1 input).

Every count here is computed from data/processed/policies.json joined with
data/institutions.csv (for institution type); nothing is typed by hand.

Usage: python3 scripts/analyze.py
"""
import json
from collections import Counter

from codebook_schema import CODED_FIELDS, ENUMS, STANCES, THEMES, load_institutions, load_policies
from raw_format import ROOT, SOURCE_SECTIONS

OUT_PATH = ROOT / "docs" / "data" / "findings.json"
TYPES = ["private_r1", "public_r1", "other"]
FIELD_VALUES = dict(ENUMS, stance=STANCES, collaboration_framing=[True, False])
EXAMPLES_PER_VALUE = 3


def key(v):
    """JSON object keys must be strings; keep stance/bool values readable."""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def distribution(records, field):
    c = Counter(r[field] for r in records)
    return {key(v): c.get(v, 0) for v in FIELD_VALUES[field]}


def crosstab(records, field, types):
    return {t: distribution([r for r in records if r["type"] == t], field) for t in types}


def share(k, n):
    return round(k / n, 4) if n else None


def source_coverage(records):
    """Sections with a URL are exactly those whose source_date is not null."""
    out = {}
    for sec in SOURCE_SECTIONS:
        slugs = [r["slug"] for r in records if r["source_date"][sec] is not None]
        out[sec] = {"count": len(slugs), "share": share(len(slugs), len(records)), "slugs": slugs}
    return out


def dept_statement_finding(records, coverage):
    dept = coverage["dept_statement"]
    without = [r for r in records if r["source_date"]["dept_statement"] is None]
    return {
        "headline": (f"Only {dept['count']} of {len(records)} CS departments/schools publish their own "
                     f"genAI statement; the other {len(without)} defer to university guidance or "
                     f"course syllabi."),
        "count": dept["count"],
        "n": len(records),
        "share": dept["share"],
        "slugs": dept["slugs"],
        "records": [{"slug": r["slug"], "name": r["name"], "default_rule": r["default_rule"],
                     "stance": r["stance"], "confidence": r["confidence"], "notes": r["notes"]}
                    for r in records if r["slug"] in dept["slugs"]],
        "without_dept_statement": {
            "count": len(without),
            "policy_level": distribution(without, "policy_level"),
            "default_rule": distribution(without, "default_rule"),
        },
    }


def theme_counts(records, types):
    overall = {t: sum(t in r["themes"] for r in records) for t in THEMES}
    by_type = {ty: {t: sum(t in r["themes"] for r in records if r["type"] == ty) for t in THEMES}
               for ty in types}
    return {"overall": overall, "by_type": by_type,
            "share": {t: share(c, len(records)) for t, c in overall.items()}}


def collaboration_summary(records, types):
    yes = [r for r in records if r["collaboration_framing"]]
    by_type = {}
    for t in types:
        group = [r for r in records if r["type"] == t]
        k = sum(r["collaboration_framing"] for r in group)
        by_type[t] = {"count": k, "n": len(group), "share": share(k, len(group))}
    return {"count": len(yes), "n": len(records), "share": share(len(yes), len(records)),
            "by_type": by_type,
            "examples": [{"slug": r["slug"], "name": r["name"], "quote": r["evidence"]["collaboration_framing"]}
                         for r in yes]}


def se_summary(records, types):
    found = [r for r in records if r["se_course_policy"] != "not_found"]
    return {
        "n_with_policy": len(found),
        "n_not_found": len(records) - len(found),
        "distribution": distribution(records, "se_course_policy"),
        "distribution_found_only": {k: v for k, v in distribution(found, "se_course_policy").items()
                                    if k != "not_found"},
        "by_type": crosstab(records, "se_course_policy", types),
        "courses": [{"slug": r["slug"], "name": r["name"], "type": r["type"],
                     "policy": r["se_course_policy"], "quote": r["evidence"]["se_course_policy"],
                     "source_date": r["source_date"]["se_course"]} for r in found],
    }


def stance_summary(records, types):
    def mean(group):
        return round(sum(r["stance"] for r in group) / len(group), 3) if group else None
    return {"mean": mean(records),
            "mean_by_type": {t: mean([r for r in records if r["type"] == t]) for t in types}}


def recency(records):
    out = {}
    for sec in SOURCE_SECTIONS:
        c = Counter(r["source_date"][sec] for r in records if r["source_date"][sec] is not None)
        years = sorted(v for v in c if v != "undated")
        out[sec] = {"by_year": {str(y): c[y] for y in years}, "undated": c.get("undated", 0),
                    "with_url": sum(c.values())}
    return out


def examples(records, field):
    out = {}
    for v in FIELD_VALUES[field]:
        hits = [r for r in records if r[field] == v and field in r["evidence"]]
        if hits:
            out[key(v)] = [{"slug": r["slug"], "name": r["name"], "quote": r["evidence"][field]}
                           for r in hits[:EXAMPLES_PER_VALUE]]
    return out


def build(policies, institutions):
    info = {r["slug"]: r for r in institutions}
    records = [dict(p, type=info[p["slug"]]["type"], name=info[p["slug"]]["name"]) for p in policies]
    types = [t for t in TYPES if any(r["type"] == t for r in records)]
    coverage = source_coverage(records)
    return {
        "n": len(records),
        "n_by_type": {t: sum(r["type"] == t for r in records) for t in types},
        "source": "data/processed/policies.json (Claude-coded, codebook in specs/codebook.md)",
        "dept_statement_finding": dept_statement_finding(records, coverage),
        "source_coverage": coverage,
        "distributions": {f: distribution(records, f) for f in CODED_FIELDS + ["confidence"]},
        "crosstabs_by_type": {f: crosstab(records, f, types) for f in CODED_FIELDS},
        "stance": stance_summary(records, types),
        "themes": theme_counts(records, types),
        "collaboration_framing": collaboration_summary(records, types),
        "se_course": se_summary(records, types),
        "recency": recency(records),
        "examples": {f: examples(records, f) for f in ["default_rule", "stance", "disclosure_required"]},
        "institutions": [{"slug": r["slug"], "name": r["name"], "type": r["type"],
                          **{f: r[f] for f in CODED_FIELDS}, "themes": r["themes"],
                          "confidence": r["confidence"]} for r in records],
    }


def main():
    findings = build(load_policies(), load_institutions())
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(findings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(findings["dept_statement_finding"]["headline"])
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
