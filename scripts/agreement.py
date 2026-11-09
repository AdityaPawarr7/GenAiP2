"""Inter-rater agreement with Claude's codes: percent agreement and Cohen's kappa per field.

Two comparisons, each against policies.json (Claude Code's codes):
  human_vs_claude: data/processed/human_coding.csv (Adi's blind codes)
  ai2_vs_claude:   data/processed/ai2_coding.csv (independent second Claude session)
Rows whose coded fields are all blank are skipped (not every sampled school is
hand-coded). Themes are compared as one yes/no field per theme. Stance also gets
a linearly weighted kappa because it is ordinal. A missing CSV gives a "pending"
comparison.

Usage: python3 scripts/agreement.py
"""
import csv
import json
from collections import Counter

from codebook_schema import CODED_FIELDS, STANCES, THEMES, load_policies
from raw_format import ROOT

PROCESSED = ROOT / "data" / "processed"
HUMAN_PATH = PROCESSED / "human_coding.csv"
AI2_PATH = PROCESSED / "ai2_coding.csv"
COMPARISONS = {
    "human_vs_claude": (HUMAN_PATH, "Adi's blind hand-coding vs. Claude Code"),
    "ai2_vs_claude": (AI2_PATH, "independent second Claude session (did not see policies.json) vs. Claude Code"),
}
OUT_PATH = PROCESSED / "agreement.json"


def percent_agreement(a, b):
    if len(a) != len(b) or not a:
        raise ValueError("need two equal-length, non-empty rating lists")
    return sum(x == y for x, y in zip(a, b)) / len(a)


def cohens_kappa(a, b):
    """Unweighted Cohen's kappa; None when chance agreement is 1 (kappa undefined)."""
    po = percent_agreement(a, b)
    n = len(a)
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[c] * cb[c] for c in set(ca) | set(cb)) / (n * n)
    if pe == 1:
        return None
    return (po - pe) / (1 - pe)


def weighted_kappa_linear(a, b, categories):
    """Linearly weighted kappa over ordered categories; None when undefined."""
    if len(a) != len(b) or not a:
        raise ValueError("need two equal-length, non-empty rating lists")
    idx = {c: i for i, c in enumerate(categories)}
    k, n = len(categories), len(a)

    def w(i, j):
        return 1 - abs(i - j) / (k - 1)

    po = sum(w(idx[x], idx[y]) for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(w(idx[x], idx[y]) * ca[x] * cb[y] for x in ca for y in cb) / (n * n)
    if pe == 1:
        return None
    return (po - pe) / (1 - pe)


def normalise(field, value):
    v = str(value).strip().lower()
    if field == "stance":
        return int(v)
    if field == "collaboration_framing":
        if v in ("true", "yes", "1"):
            return True
        if v in ("false", "no", "0"):
            return False
        raise ValueError(f"collaboration_framing value {value!r}")
    return v


def split_themes(value):
    return {t.strip() for t in str(value).replace(",", ";").split(";") if t.strip()}


def field_result(a, b, ordered=None):
    result = {"n": len(a), "percent_agreement": round(percent_agreement(a, b), 4)}
    kappa = cohens_kappa(a, b)
    result["cohens_kappa"] = None if kappa is None else round(kappa, 4)
    if kappa is None:
        result["note"] = "kappa undefined: both coders used one identical category"
    if ordered:
        wk = weighted_kappa_linear(a, b, ordered)
        result["weighted_kappa_linear"] = None if wk is None else round(wk, 4)
    return result


def is_coded(row):
    """A row counts only if at least one coded field or themes was filled in."""
    return any(str(row.get(f) or "").strip() for f in CODED_FIELDS + ["themes"])


def compute(rater_rows, policies):
    claude = {p["slug"]: p for p in policies}
    rows = [r for r in rater_rows if r.get("slug") in claude and is_coded(r)]
    fields = {}
    for field in CODED_FIELDS:
        pairs = [(normalise(field, r[field]), claude[r["slug"]][field])
                 for r in rows if str(r.get(field, "")).strip()]
        if pairs:
            a, b = zip(*pairs)
            fields[field] = field_result(list(a), list(b), STANCES if field == "stance" else None)
    themed = [r for r in rows if "themes" in r]
    themes = {}
    for t in THEMES:
        a = [t in split_themes(r["themes"]) for r in themed]
        b = [t in claude[r["slug"]]["themes"] for r in themed]
        if a:
            themes[t] = field_result(a, b)
    disagreements = [
        {"slug": r["slug"], "field": f, "rater": normalise(f, r[f]), "claude": claude[r["slug"]][f]}
        for r in rows for f in CODED_FIELDS
        if str(r.get(f, "")).strip() and normalise(f, r[f]) != claude[r["slug"]][f]]
    for r in themed:
        rater, mine = split_themes(r["themes"]), set(claude[r["slug"]]["themes"])
        if rater != mine:
            disagreements.append({"slug": r["slug"], "field": "themes",
                                  "rater_only": sorted(rater - mine), "claude_only": sorted(mine - rater)})
    return {"status": "complete", "n_institutions": len(rows), "slugs": [r["slug"] for r in rows],
            "fields": fields, "themes": themes, "disagreements": disagreements}


def compare(path, policies):
    if not path.exists():
        return {"status": "pending", "note": f"{path.relative_to(ROOT)} not found"}
    with path.open(encoding="utf-8", newline="") as f:
        return compute(list(csv.DictReader(f)), policies)


def main():
    policies = load_policies()
    result = {}
    for name, (path, description) in COMPARISONS.items():
        result[name] = dict(compare(path, policies), rater_file=str(path.relative_to(ROOT)),
                            description=description)
    OUT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for name, r in result.items():
        print(f"{name}: {r['status']}, n={r.get('n_institutions', 0)}")
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
