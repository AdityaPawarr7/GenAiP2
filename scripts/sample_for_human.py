"""Draw the blind human-coding sample (10 slugs, seed 42) and write a blank template.

The template carries no Claude codes. Adi copies it to data/processed/human_coding.csv,
fills it in from data/raw/<slug>.md and specs/codebook.md only, and must not open
policies.json for these slugs first.

Usage: python3 scripts/sample_for_human.py
"""
import csv
import random

from codebook_schema import CODED_FIELDS, load_institutions
from raw_format import ROOT

SEED = 42
SAMPLE_SIZE = 10
TEMPLATE_PATH = ROOT / "data" / "processed" / "human_coding_template.csv"
COLUMNS = ["slug", "name", "raw_file"] + CODED_FIELDS + ["themes", "notes"]


def draw_sample(slugs, seed=SEED, k=SAMPLE_SIZE):
    """Seeded sample from the sorted slug list, so the draw does not depend on CSV order."""
    return sorted(random.Random(seed).sample(sorted(slugs), k))


def main():
    rows = load_institutions()
    names = {r["slug"]: r["name"] for r in rows}
    sample = draw_sample(names)
    with TEMPLATE_PATH.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for slug in sample:
            w.writerow({"slug": slug, "name": names[slug], "raw_file": f"data/raw/{slug}.md"})
    print(f"sample (seed {SEED}): {', '.join(sample)}")
    print(f"wrote {TEMPLATE_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
