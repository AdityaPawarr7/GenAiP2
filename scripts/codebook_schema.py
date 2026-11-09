"""Codebook schema (specs/codebook.md) for data/processed/policies.json records."""
import csv
import json

from raw_format import ROOT, SOURCE_SECTIONS

POLICIES_PATH = ROOT / "data" / "processed" / "policies.json"
CSV_PATH = ROOT / "data" / "institutions.csv"

ENUMS = {
    "policy_level": ["dept", "university", "course_only", "none_found"],
    "default_rule": ["banned", "instructor_discretion", "allowed_with_disclosure", "allowed_encouraged", "unclear"],
    "disclosure_required": ["yes", "no", "unclear"],
    "se_course_policy": ["banned", "limited", "allowed", "integrated", "not_found"],
    "confidence": ["high", "medium", "low"],
}
STANCES = [-2, -1, 0, 1, 2]
THEMES = ["academic_integrity", "learning_outcomes", "career_readiness", "specific_tools",
          "equity_access", "privacy_security", "assessment_redesign", "ai_literacy"]
REQUIRED = ["slug", "policy_level", "default_rule", "stance", "collaboration_framing",
            "disclosure_required", "se_course_policy", "themes", "evidence", "source_date",
            "confidence", "notes"]
# Single-valued fields compared in human-vs-Claude agreement and summarised in findings.
CODED_FIELDS = ["policy_level", "default_rule", "stance", "collaboration_framing",
                "disclosure_required", "se_course_policy"]


def load_policies():
    return json.loads(POLICIES_PATH.read_text(encoding="utf-8"))


def load_institutions():
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def required_evidence_keys(record):
    """Evidence keys a record must carry: one per non-trivial code."""
    keys = ["default_rule", "stance"]
    if record.get("collaboration_framing") is True:
        keys.append("collaboration_framing")
    if record.get("disclosure_required") in ("yes", "no"):
        keys.append("disclosure_required")
    if record.get("se_course_policy") not in (None, "not_found"):
        keys.append("se_course_policy")
    keys.extend(f"themes:{t}" for t in record.get("themes", []))
    return keys


def schema_errors(record):
    """Return a list of human-readable schema problems for one record (empty if valid)."""
    slug = record.get("slug", "?")
    errors = [f"{slug}: missing field {f}" for f in REQUIRED if f not in record]
    if errors:
        return errors
    for field, allowed in ENUMS.items():
        if record[field] not in allowed:
            errors.append(f"{slug}: {field}={record[field]!r} not in {allowed}")
    if type(record["stance"]) is not int or record["stance"] not in STANCES:
        errors.append(f"{slug}: stance={record['stance']!r} not an int in -2..2")
    if type(record["collaboration_framing"]) is not bool:
        errors.append(f"{slug}: collaboration_framing must be a bool")
    themes = record["themes"]
    if not isinstance(themes, list) or len(set(themes)) != len(themes) or any(t not in THEMES for t in themes):
        errors.append(f"{slug}: themes {themes!r} must be a list of distinct codebook themes")
    if not isinstance(record["evidence"], dict) or not all(
            isinstance(v, str) and v.strip() for v in record["evidence"].values()):
        errors.append(f"{slug}: evidence must map keys to non-empty strings")
    else:
        missing = [k for k in required_evidence_keys(record) if k not in record["evidence"]]
        if missing:
            errors.append(f"{slug}: evidence missing for {missing}")
    sd = record["source_date"]
    if not isinstance(sd, dict) or sorted(sd) != sorted(SOURCE_SECTIONS):
        errors.append(f"{slug}: source_date must have exactly the keys {SOURCE_SECTIONS}")
    else:
        for sec, v in sd.items():
            if not (v is None or v == "undated" or (type(v) is int and 1990 <= v <= 2100)):
                errors.append(f"{slug}: source_date[{sec}]={v!r} invalid")
    if not isinstance(record["notes"], str):
        errors.append(f"{slug}: notes must be a string")
    return errors
