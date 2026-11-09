"""Phase 1 acceptance tests: sample list and raw primary-source excerpts (specs/phase-1-data.md).

AC1.2/AC1.5/AC1.6 aggregate tests cover the whole sample and are expected to
fail until every collection batch is done. AC1.7 is a manual spot check.
"""
import csv
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from raw_format import MISSING, RAW_DIR, SECTIONS, SOURCE_SECTIONS, has_url, parse_raw  # noqa: E402

CSV_PATH = ROOT / "data" / "institutions.csv"
VALID_TYPES = {"private_r1", "public_r1", "other"}


def load_rows():
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


ROWS = load_rows() if CSV_PATH.exists() else []
SLUGS = [r["slug"] for r in ROWS]
RAW_FILES = sorted(RAW_DIR.glob("*.md"))
RAW_IDS = [p.stem for p in RAW_FILES]


def test_AC1_1_institutions_csv_has_required_columns():
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        header = next(csv.reader(f))
    assert header == ["slug", "name", "type", "state", "cs_dept_url"]


def test_AC1_1_institutions_csv_has_at_least_35_rows():
    assert len(ROWS) >= 35, f"only {len(ROWS)} rows"


def test_AC1_1_institution_slugs_are_unique_and_lowercase():
    assert len(SLUGS) == len(set(SLUGS)), "duplicate slugs"
    bad = [s for s in SLUGS if not re.fullmatch(r"[a-z0-9_]+", s)]
    assert not bad, f"malformed slugs: {bad}"


def test_AC1_1_institution_types_are_valid():
    bad = {r["slug"]: r["type"] for r in ROWS if r["type"] not in VALID_TYPES}
    assert not bad, f"invalid types: {bad}"


def test_AC1_2_every_raw_file_matches_a_csv_slug():
    orphans = [s for s in RAW_IDS if s not in SLUGS]
    assert not orphans, f"raw files without a CSV row: {orphans}"


def test_AC1_2_every_institution_has_a_raw_file():
    missing = [s for s in SLUGS if not (RAW_DIR / f"{s}.md").exists()]
    assert not missing, f"{len(missing)}/{len(SLUGS)} institutions not collected yet: {missing}"


@pytest.mark.parametrize("path", RAW_FILES, ids=RAW_IDS)
def test_AC1_2_raw_file_has_title_retrieved_date_and_all_5_sections(path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# "), "missing '# <Name>' title"
    parsed = parse_raw(path)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", parsed["_meta"].get("retrieved", "")), "bad retrieved: line"
    assert parsed["_headers"] == SECTIONS, f"sections are {parsed['_headers']}"


@pytest.mark.parametrize("path", RAW_FILES, ids=RAW_IDS)
def test_AC1_3_every_source_section_has_url_or_not_found_or_blocked(path):
    parsed = parse_raw(path)
    for section in SOURCE_SECTIONS:
        sources = parsed[section]
        assert sources, f"{section} has no url: line"
        for src in sources:
            assert src["url"].startswith(("http://", "https://")) or src["url"] in MISSING, \
                f"{section} has invalid url value {src['url']!r}"


@pytest.mark.parametrize("path", RAW_FILES, ids=RAW_IDS)
def test_AC1_4_every_source_url_has_a_verbatim_quote_block(path):
    parsed = parse_raw(path)
    for section in SOURCE_SECTIONS:
        for src in parsed[section]:
            if src["url"].startswith("http"):
                assert src["quotes"], f"{section} url {src['url']} has no > quote"


@pytest.mark.parametrize("path", RAW_FILES, ids=RAW_IDS)
def test_AC1_4_course_sections_name_the_course(path):
    text = path.read_text(encoding="utf-8")
    for section in ("intro_course", "se_course"):
        body = text.split(f"## {section}", 1)[1].split("\n## ", 1)[0]
        if "url: http" in body:
            assert re.search(r"^course:\s*\S", body, re.M), f"{section} is missing a course: line"


def _share_with_url(sections):
    found = [s for s in SLUGS if (RAW_DIR / f"{s}.md").exists()
             and any(has_url(parse_raw(RAW_DIR / f"{s}.md")[sec]) for sec in sections)]
    return len(found) / len(SLUGS)


def test_AC1_5_at_least_70pct_have_dept_or_university_guidance_url():
    share = _share_with_url(["dept_statement", "university_guidance"])
    assert share >= 0.70, f"{share:.0%} of institutions"


def test_AC1_6_at_least_50pct_have_se_course_url():
    share = _share_with_url(["se_course"])
    assert share >= 0.50, f"{share:.0%} of institutions"
