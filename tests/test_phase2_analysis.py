"""Phase 2 acceptance tests: coding and analysis (specs/phase-2-analysis.md, AC2.1-AC2.6).

Per-institution tests are parametrized by slug so the validation dashboard shows
which school fails. Extra tests (marked "extra" in the docstring) go beyond the
spec: evidence must come from quotes under URL sources (never notes), and
source_date must equal the value derived from the raw file.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import agreement  # noqa: E402
import analyze  # noqa: E402
import lexicon_check  # noqa: E402
import sample_for_human  # noqa: E402
from build_policies import evidence_problems, evidence_quotes, load_coded, source_dates  # noqa: E402
from codebook_schema import (CODED_FIELDS, POLICIES_PATH, THEMES, load_institutions,  # noqa: E402
                             load_policies, schema_errors)
from raw_format import RAW_DIR, SOURCE_SECTIONS, has_url, parse_raw  # noqa: E402

POLICIES = load_policies() if POLICIES_PATH.exists() else []
BY_SLUG = {p["slug"]: p for p in POLICIES}
INSTITUTIONS = load_institutions()
SLUGS = [r["slug"] for r in INSTITUTIONS]
TYPE = {r["slug"]: r["type"] for r in INSTITUTIONS}
FINDINGS_PATH = ROOT / "docs" / "data" / "findings.json"
FINDINGS = json.loads(FINDINGS_PATH.read_text(encoding="utf-8")) if FINDINGS_PATH.exists() else {}


def record(slug):
    if slug not in BY_SLUG:
        pytest.fail(f"no record for {slug}")
    return BY_SLUG[slug]


def key(v):
    return analyze.key(v)


# ---------------------------------------------------------------- AC2.1 schema

def test_AC2_1_policies_json_is_a_list_of_42_records():
    assert isinstance(POLICIES, list)
    assert len(POLICIES) == len(SLUGS)


@pytest.mark.parametrize("slug", SLUGS)
def test_AC2_1_record_validates_against_codebook_schema(slug):
    errors = schema_errors(record(slug))
    assert not errors, "\n".join(errors)


def test_AC2_1_schema_validator_rejects_bad_enum_stance_and_theme():
    bad = dict(POLICIES[0], default_rule="sometimes", stance=3, themes=["vibes"])
    errors = " ".join(schema_errors(bad))
    assert "default_rule" in errors and "stance" in errors and "themes" in errors


def test_AC2_1_schema_validator_rejects_missing_required_field():
    bad = {k: v for k, v in POLICIES[0].items() if k != "disclosure_required"}
    assert any("missing field disclosure_required" in e for e in schema_errors(bad))


@pytest.mark.parametrize("slug", SLUGS)
def test_AC2_1_source_date_is_copied_from_raw_file_not_inferred(slug):
    """extra: source_date per section must equal the value derived from data/raw/<slug>.md."""
    assert record(slug)["source_date"] == source_dates(slug)


@pytest.mark.parametrize("slug", SLUGS)
def test_AC2_1_policy_level_matches_highest_raw_section_with_url(slug):
    """extra: policy_level follows the convention in specs/codebook.md."""
    raw = parse_raw(RAW_DIR / f"{slug}.md")
    if has_url(raw.get("dept_statement", [])):
        expected = "dept"
    elif has_url(raw.get("university_guidance", [])):
        expected = "university"
    elif has_url(raw.get("intro_course", [])) or has_url(raw.get("se_course", [])):
        expected = "course_only"
    else:
        expected = "none_found"
    assert record(slug)["policy_level"] == expected


@pytest.mark.parametrize("slug", SLUGS)
def test_AC2_1_se_course_policy_is_not_found_when_raw_se_section_has_no_url(slug):
    raw = parse_raw(RAW_DIR / f"{slug}.md")
    if not has_url(raw.get("se_course", [])):
        assert record(slug)["se_course_policy"] == "not_found"


def test_AC2_1_policies_json_is_rebuilt_from_current_coding_batches():
    """policies.json must equal build_policies output (re-run scripts/build_policies.py if this fails)."""
    expected = {r["slug"]: dict(r, source_date=source_dates(r["slug"])) for r in load_coded()}
    assert {p["slug"]: p for p in POLICIES} == expected


# ---------------------------------------------------------------- AC2.2 evidence

@pytest.mark.parametrize("slug", SLUGS)
def test_AC2_2_every_evidence_string_is_exact_substring_of_raw_file(slug):
    text = (RAW_DIR / f"{slug}.md").read_text(encoding="utf-8")
    missing = {k: v for k, v in record(slug)["evidence"].items() if v not in text}
    assert not missing, f"evidence not found verbatim in data/raw/{slug}.md: {missing}"


@pytest.mark.parametrize("slug", SLUGS)
def test_AC2_2_evidence_comes_from_quote_under_url_source_not_notes(slug):
    """extra: notes, LIMITATION and Decision lines are context, never coding evidence."""
    quotes = evidence_quotes(slug)
    stray = {k: v for k, v in record(slug)["evidence"].items() if not any(v in q for q in quotes)}
    assert not stray, f"evidence not inside a URL-source quote: {stray}"


def test_AC2_2_evidence_check_rejects_fabricated_quote():
    fake = dict(POLICIES[0], evidence={"default_rule": "All AI use is mandatory in every course."})
    assert evidence_problems(fake)


def test_AC2_2_evidence_check_rejects_quote_taken_from_notes():
    """gatech's Joyner article sits in notes only (Adi decision), so it must not count as evidence."""
    notes_only = "We treat AI-based assistance, such as ChatGPT and Copilot, the same way we treat collaboration"
    assert notes_only in (RAW_DIR / "gatech.md").read_text(encoding="utf-8")
    fake = dict(BY_SLUG["gatech"], evidence={"collaboration_framing": notes_only})
    assert any("not inside a quote" in p for p in evidence_problems(fake))


# ---------------------------------------------------------------- AC2.3 one record each

def test_AC2_3_every_institution_has_exactly_one_record():
    counts = Counter(p["slug"] for p in POLICIES)
    problems = {s: counts.get(s, 0) for s in SLUGS if counts.get(s, 0) != 1}
    assert not problems, f"slug -> record count: {problems}"


def test_AC2_3_no_record_for_a_slug_missing_from_institutions_csv():
    extra = [p["slug"] for p in POLICIES if p["slug"] not in SLUGS]
    assert not extra


# ---------------------------------------------------------------- AC2.4 kappa

def _from_2x2(yy, yn, ny, nn):
    a = ["yes"] * (yy + yn) + ["no"] * (ny + nn)
    b = ["yes"] * yy + ["no"] * yn + ["yes"] * ny + ["no"] * nn
    return a, b


def test_AC2_4_cohens_kappa_matches_textbook_example_kappa_0_40():
    """50 items: both yes 20, A yes/B no 5, A no/B yes 10, both no 15.
    po = 35/50 = 0.70; pe = 0.5*0.6 + 0.5*0.4 = 0.50; kappa = (0.70-0.50)/(1-0.50) = 0.40."""
    a, b = _from_2x2(20, 5, 10, 15)
    assert agreement.percent_agreement(a, b) == pytest.approx(0.70)
    assert agreement.cohens_kappa(a, b) == pytest.approx(0.40)


def test_AC2_4_cohens_kappa_matches_second_textbook_example_kappa_0_1304():
    """100 items: 45 / 15 / 25 / 15. po = 0.60; pe = 0.6*0.7 + 0.4*0.3 = 0.54;
    kappa = 0.06 / 0.46 = 0.1304."""
    a, b = _from_2x2(45, 15, 25, 15)
    assert agreement.cohens_kappa(a, b) == pytest.approx(0.06 / 0.46)
    assert round(agreement.cohens_kappa(a, b), 4) == 0.1304


def test_AC2_4_perfect_agreement_gives_kappa_1():
    a = ["banned", "instructor_discretion", "allowed_with_disclosure", "banned"]
    assert agreement.cohens_kappa(a, list(a)) == pytest.approx(1.0)


def test_AC2_4_kappa_is_undefined_when_both_coders_use_one_category():
    assert agreement.cohens_kappa(["x"] * 5, ["x"] * 5) is None


def test_AC2_4_linear_weighted_kappa_matches_hand_computed_ordinal_example():
    """a = [0,1,2], b = [0,2,2], w = 1 - |i-j|/2. po_w = (1 + 0.5 + 1)/3 = 5/6;
    pe_w = 4.5/9 = 0.5; kappa_w = (5/6 - 0.5)/0.5 = 2/3."""
    assert agreement.weighted_kappa_linear([0, 1, 2], [0, 2, 2], [0, 1, 2]) == pytest.approx(2 / 3)


def test_AC2_4_linear_weighted_kappa_equals_unweighted_for_two_categories():
    a, b = _from_2x2(20, 5, 10, 15)
    assert agreement.weighted_kappa_linear(a, b, ["yes", "no"]) == pytest.approx(agreement.cohens_kappa(a, b))


def test_AC2_4_agreement_compute_gives_full_agreement_when_human_copies_claude():
    rows = []
    for p in POLICIES[:5]:
        row = {f: str(p[f]) for f in CODED_FIELDS}
        row.update(slug=p["slug"], themes="; ".join(p["themes"]))
        rows.append(row)
    result = agreement.compute(rows, POLICIES)
    assert result["n_institutions"] == 5
    assert all(r["percent_agreement"] == 1.0 for r in result["fields"].values())
    assert all(r["percent_agreement"] == 1.0 for r in result["themes"].values())
    assert result["disagreements"] == []


def test_AC2_4_agreement_compute_lists_each_disagreement():
    p = POLICIES[0]
    row = {f: str(p[f]) for f in CODED_FIELDS}
    row.update(slug=p["slug"], themes="", stance=str(p["stance"] + 1 if p["stance"] < 2 else 1))
    result = agreement.compute([row], POLICIES)
    assert [d["field"] for d in result["disagreements"]] == ["stance"]


# ---------------------------------------------------------------- AC2.5 findings counts

def test_AC2_5_findings_json_n_equals_number_of_policy_records():
    assert FINDINGS["n"] == len(POLICIES)
    assert FINDINGS["n_by_type"] == dict(Counter(TYPE[p["slug"]] for p in POLICIES))


@pytest.mark.parametrize("field", CODED_FIELDS + ["confidence"])
def test_AC2_5_distribution_counts_equal_counts_from_policies(field):
    expected = Counter(key(p[field]) for p in POLICIES)
    got = {k: v for k, v in FINDINGS["distributions"][field].items() if v}
    assert got == dict(expected)


@pytest.mark.parametrize("field", CODED_FIELDS)
def test_AC2_5_crosstab_by_institution_type_equals_counts_from_policies(field):
    for t, dist in FINDINGS["crosstabs_by_type"][field].items():
        expected = Counter(key(p[field]) for p in POLICIES if TYPE[p["slug"]] == t)
        assert {k: v for k, v in dist.items() if v} == dict(expected), t


def test_AC2_5_theme_counts_equal_counts_from_policies():
    for t in THEMES:
        assert FINDINGS["themes"]["overall"][t] == sum(t in p["themes"] for p in POLICIES), t


def test_AC2_5_collaboration_framing_share_equals_share_from_policies():
    k = sum(p["collaboration_framing"] for p in POLICIES)
    assert FINDINGS["collaboration_framing"]["count"] == k
    assert FINDINGS["collaboration_framing"]["share"] == pytest.approx(k / len(POLICIES), abs=1e-4)


def test_AC2_5_se_course_summary_equals_counts_from_policies():
    found = [p for p in POLICIES if p["se_course_policy"] != "not_found"]
    se = FINDINGS["se_course"]
    assert se["n_with_policy"] == len(found)
    assert sorted(c["slug"] for c in se["courses"]) == sorted(p["slug"] for p in found)


def test_AC2_5_dept_statement_finding_matches_raw_files_and_is_reported():
    """Adi: only a handful of schools have a dept_statement; the analysis must report it."""
    raw_dept = [s for s in SLUGS if has_url(parse_raw(RAW_DIR / f"{s}.md").get("dept_statement", []))]
    finding = FINDINGS["dept_statement_finding"]
    assert sorted(finding["slugs"]) == sorted(raw_dept)
    assert finding["count"] == len(raw_dept) and finding["n"] == len(SLUGS)
    assert f"Only {len(raw_dept)} of {len(SLUGS)}" in finding["headline"]


@pytest.mark.parametrize("section", SOURCE_SECTIONS)
def test_AC2_5_source_coverage_equals_raw_sections_with_url(section):
    expected = [s for s in SLUGS if has_url(parse_raw(RAW_DIR / f"{s}.md").get(section, []))]
    assert sorted(FINDINGS["source_coverage"][section]["slugs"]) == sorted(expected)


@pytest.mark.parametrize("section", SOURCE_SECTIONS)
def test_AC2_5_recency_counts_equal_source_dates_in_policies(section):
    values = [p["source_date"][section] for p in POLICIES if p["source_date"][section] is not None]
    rec = FINDINGS["recency"][section]
    assert rec["undated"] == values.count("undated")
    assert rec["by_year"] == {str(y): values.count(y) for y in sorted(set(values) - {"undated"})}


def test_AC2_5_findings_json_is_up_to_date_with_policies():
    """Re-run scripts/analyze.py if this fails."""
    rebuilt = json.loads(json.dumps(analyze.build(POLICIES, INSTITUTIONS), ensure_ascii=False))
    assert FINDINGS == rebuilt


# ---------------------------------------------------------------- AC2.6 lexicon check

def test_AC2_6_lexicon_check_runs_and_writes_flags_json():
    result = lexicon_check.run()
    saved = json.loads(lexicon_check.OUT_PATH.read_text(encoding="utf-8"))
    assert saved == json.loads(json.dumps(result))
    assert set(saved["counts"]) == set(SLUGS)
    assert saved["n_flags"] == len(saved["flags"])


def test_AC2_6_every_flag_names_a_known_institution_and_rule():
    flags = json.loads(lexicon_check.OUT_PATH.read_text(encoding="utf-8"))["flags"]
    assert all(f["slug"] in SLUGS and f["rule"] and f["detail"] for f in flags)


def _synthetic(**codes):
    base = {"slug": "test", "stance": 0, "collaboration_framing": False,
            "disclosure_required": "yes", "se_course_policy": "not_found"}
    return dict(base, **codes)


def test_AC2_6_lexicon_flags_prohibit_word_when_stance_is_positive():
    hits = lexicon_check.lexicon_hits("AI use is strictly prohibited.")
    flags = lexicon_check.flags_for(_synthetic(stance=1), hits, lexicon_check.lexicon_hits(""))
    assert [f["rule"] for f in flags] == ["prohibit_words_but_positive_stance"]


def test_AC2_6_lexicon_flags_collaboration_word_when_framing_is_false():
    hits = lexicon_check.lexicon_hits("Use AI as a pair programmer and tutor.")
    flags = lexicon_check.flags_for(_synthetic(), hits, lexicon_check.lexicon_hits(""))
    assert [f["rule"] for f in flags] == ["collaboration_words_but_framing_false"]


def test_AC2_6_lexicon_does_not_count_discouraged_as_encourage():
    assert lexicon_check.lexicon_hits("Use is strongly discouraged.")["encourage"] == []


# ---------------------------------------------------------------- human sample

def test_human_sample_is_10_distinct_slugs_drawn_with_seed_42():
    sample = sample_for_human.draw_sample(SLUGS)
    assert len(sample) == len(set(sample)) == 10
    assert sample == sample_for_human.draw_sample(list(reversed(SLUGS)))


def test_human_coding_template_lists_the_seed_42_sample_with_no_claude_codes():
    with sample_for_human.TEMPLATE_PATH.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert [r["slug"] for r in rows] == sample_for_human.draw_sample(SLUGS)
    blank = CODED_FIELDS + ["themes", "notes"]
    assert all(not r[c] for r in rows for c in blank), "template must not leak Claude's codes"
