"""Keyword cross-check of Claude's codes against the raw quotes (SPEC analysis step 5).

Counts lexicon hits per institution over all quotes under URL sources (notes
excluded) and flags records where the words and the assigned codes disagree.
Flags are prompts for Adi's review, not errors: stance is coded from the
governing official text, while the lexicon sees every section.

Usage: python3 scripts/lexicon_check.py   -> data/processed/flags.json
"""
import json
import re

from build_policies import evidence_quotes
from codebook_schema import load_policies
from raw_format import ROOT

OUT_PATH = ROOT / "data" / "processed" / "flags.json"

LEXICON = {
    "prohibit": r"\bprohibit\w*|\bforbid\w*|\bforbidden\b|\bbann?(ed|s)?\b|\bnot (be )?(allowed|permitted)\b|\bmay not use\b",
    "encourage": r"\bencourag\w*|\bwelcome\b|\bembrac\w*",
    "collaborat": r"\bcollaborat\w*|\bpartner\w*|\btutor\w*|\bpair[- ]?program\w*|\bpeer programming\b|\bteammate\w*",
    "disclose": r"\bdisclos\w*|\bcite\b|\bciting\b|\bcitation\w*|\backnowledg\w*|\battribut\w*",
    "require": r"\brequired?\b|\brequires\b",
}
COMPILED = {k: re.compile(v, re.IGNORECASE) for k, v in LEXICON.items()}


def lexicon_hits(text):
    return {k: [m.group(0) for m in rx.finditer(text)] for k, rx in COMPILED.items()}


def flags_for(record, hits, se_hits):
    """Disagreement rules between lexicon hits and codes; returns a list of flag dicts."""
    out = []

    def flag(rule, detail, words):
        out.append({"slug": record["slug"], "rule": rule, "detail": detail,
                    "matched": sorted(set(w.lower() for w in words))})

    if hits["prohibit"] and record["stance"] >= 1:
        flag("prohibit_words_but_positive_stance",
             f"prohibition words appear but stance is {record['stance']:+d}", hits["prohibit"])
    if hits["encourage"] and record["stance"] <= -1:
        flag("encourage_words_but_negative_stance",
             f"encouragement words appear but stance is {record['stance']:+d}", hits["encourage"])
    if hits["collaborat"] and not record["collaboration_framing"]:
        flag("collaboration_words_but_framing_false",
             "collaboration/tutor words appear but collaboration_framing is false", hits["collaborat"])
    if record["collaboration_framing"] and not hits["collaborat"]:
        flag("framing_true_without_collaboration_words",
             "collaboration_framing is true but no collaboration/tutor word appears", [])
    if hits["disclose"] and record["disclosure_required"] == "unclear":
        flag("disclosure_words_but_disclosure_unclear",
             "disclosure/citation words appear but disclosure_required is unclear", hits["disclose"])
    if se_hits["prohibit"] and record["se_course_policy"] in ("allowed", "integrated"):
        flag("se_prohibit_words_but_se_permissive",
             f"SE-course quotes contain prohibition words but se_course_policy is {record['se_course_policy']}",
             se_hits["prohibit"])
    if se_hits["require"] and record["se_course_policy"] in ("banned", "limited", "allowed"):
        flag("se_require_words_but_not_integrated",
             f"SE-course quotes contain 'require' but se_course_policy is {record['se_course_policy']}",
             se_hits["require"])
    return out


def run():
    from raw_format import RAW_DIR, parse_raw
    counts, flags = {}, []
    for record in load_policies():
        slug = record["slug"]
        hits = lexicon_hits("\n".join(evidence_quotes(slug)))
        raw = parse_raw(RAW_DIR / f"{slug}.md")
        se_text = "\n".join(q for s in raw.get("se_course", []) for q in s["quotes"])
        se_hits = lexicon_hits(se_text)
        counts[slug] = {k: len(v) for k, v in hits.items()}
        flags.extend(flags_for(record, hits, se_hits))
    result = {"lexicon": LEXICON, "counts": counts, "n_flags": len(flags), "flags": flags}
    OUT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main():
    result = run()
    print(f"{result['n_flags']} flags written to {OUT_PATH.relative_to(ROOT)}")
    for f in result["flags"]:
        print(f"  {f['slug']:<13} {f['rule']:<42} {', '.join(f['matched'])}")


if __name__ == "__main__":
    main()
