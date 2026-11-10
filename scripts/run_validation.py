"""Phase 4 validation pipeline.

Runs the pytest suite with junit XML output, converts it to JSON, and writes the data
behind docs/validation.html:

  docs/data/tests.json                 one record per test of this run (+ a run summary)
  docs/data/test_runs.json             run summaries, appended each run (history)
  docs/data/acceptance_criteria.json   every AC parsed from specs/phase-*.md
  docs/data/agreement.json             copy of data/processed/agreement.json

Test -> AC mapping: a name starting test_ACx_y_ maps to ACx.y; otherwise an
@pytest.mark.ac("ACx.y") marker (see tests/conftest.py); otherwise the test is an
"extra" with no AC. The phase comes from the file name (test_phaseN_*.py).

Usage: python scripts/run_validation.py [--note "canary run"] [--no-history] [pytest targets ...]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS = ROOT / "specs"
OUT = ROOT / "docs" / "data"
AGREEMENT = ROOT / "data" / "processed" / "agreement.json"
REVIEWS = OUT / "reviews.json"

# AC4.1 coverage is enforced for phases up to this one (Adi, Phase 4 "go"). ACs of later
# phases are listed as "planned" on the dashboard. Bump this as each phase ships.
ENFORCED_THROUGH_PHASE = 6

MESSAGE_LIMIT = 4000
AC_LINE = re.compile(r"^- (AC(\d+)\.(\d+))\b[^:]*:\s*(.+)$")
AC_NAME = re.compile(r"^test_ac(\d+)_(\d+)(?:_|$|\[)", re.IGNORECASE)
PHASE_FILE = re.compile(r"test_phase(\d+)")


# ---------- acceptance criteria ----------

def spec_acs(specs_dir=SPECS):
    """Every AC line in specs/phase-*.md, in spec order."""
    acs = []
    for path in sorted(specs_dir.glob("phase-*.md"), key=lambda p: int(re.search(r"phase-(\d+)", p.name).group(1))):
        for line in path.read_text(encoding="utf-8").splitlines():
            m = AC_LINE.match(line.strip())
            if not m:
                continue
            phase = int(m.group(2))
            text = m.group(4).strip()
            acs.append({
                "id": m.group(1),
                "phase": phase,
                "text": text,
                "manual": "manual" in line[:line.index(":")].lower() if ":" in line else False,
                "enforced": phase <= ENFORCED_THROUGH_PHASE,
                "spec": "specs/" + path.name,
            })
    return acs


def ac_for(name, properties):
    """AC id for a test: marker property first, then the test name."""
    if properties.get("ac"):
        return properties["ac"]
    m = AC_NAME.match(name)
    return "AC%s.%s" % (m.group(1), m.group(2)) if m else None


def coverage(acs, tests, reviews):
    """Map each AC id to the test ids and review ids that cover it."""
    cov = {a["id"]: {"tests": [], "reviews": []} for a in acs}
    for t in tests:
        if t["acceptance_criterion"] in cov:
            cov[t["acceptance_criterion"]]["tests"].append(t["id"])
    for r in reviews:
        for ac in r.get("acs", []):
            if ac in cov:
                cov[ac]["reviews"].append(r["id"])
    return cov


# ---------- junit XML -> records ----------

def parse_junit(xml_path, run_id, timestamp, rootdir=ROOT):
    root = ET.parse(xml_path).getroot()
    prefix = str(Path(rootdir).resolve()) + os.sep
    records = []
    for case in root.iter("testcase"):
        name = case.get("name")
        file = case.get("file") or (case.get("classname", "").replace(".", "/") + ".py")
        props = {p.get("name"): p.get("value") for p in case.iter("property")}
        status, message = "passed", ""
        for tag in ("failure", "error", "skipped"):
            node = case.find(tag)
            if node is not None:
                status = {"failure": "failed", "error": "error", "skipped": "skipped"}[tag]
                parts = [node.get("message") or "", (node.text or "").strip()]
                message = "\n\n".join(p for p in parts if p).replace(prefix, "")[:MESSAGE_LIMIT]  # repo-relative paths only
                break
        pm = PHASE_FILE.search(file)
        records.append({
            "id": file + "::" + name,
            "phase": int(pm.group(1)) if pm else None,
            "acceptance_criterion": ac_for(name, props),
            "name": name,
            "file": file,
            "status": status,
            "duration": round(float(case.get("time") or 0), 3),
            "message": message,
            "timestamp": timestamp,
            "run_id": run_id,
        })
    return records


def summarize(records, run_id, timestamp, duration, note=None):
    count = lambda s: sum(1 for r in records if r["status"] == s)
    passed, failed, errors, skipped = count("passed"), count("failed"), count("error"), count("skipped")
    ran = passed + failed + errors
    return {
        "run_id": run_id,
        "timestamp": timestamp,
        "total": len(records),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "pass_rate": round(passed / ran, 4) if ran else None,
        "duration": round(duration, 2),
        "failed_tests": [r["id"] for r in records if r["status"] in ("failed", "error")],
        "note": note or "",
    }


# ---------- pipeline ----------

def run(targets=None, rootdir=ROOT, out_dir=OUT, note=None, history=True):
    """Run pytest on `targets` (default: the tests/ folder) and write the JSON files to out_dir."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    run_id = "run-" + now.strftime("%Y%m%d-%H%M%S")
    timestamp = now.astimezone().isoformat(timespec="seconds")
    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "junit.xml"
        cmd = [sys.executable, "-m", "pytest", *(targets or ["tests"]), "-q", "-p", "no:cacheprovider",
               "--rootdir", str(rootdir), "-o", "junit_family=xunit1", "--junitxml", str(xml_path)]
        env = dict(os.environ, VALIDATION_RUN="1")
        started = datetime.now(timezone.utc)
        proc = subprocess.run(cmd, cwd=str(rootdir), env=env, capture_output=True, text=True)
        duration = (datetime.now(timezone.utc) - started).total_seconds()
        if not xml_path.exists():
            raise RuntimeError("pytest wrote no junit XML (exit %s):\n%s%s" % (proc.returncode, proc.stdout[-2000:], proc.stderr[-2000:]))
        records = parse_junit(xml_path, run_id, timestamp, rootdir)

    summary = summarize(records, run_id, timestamp, duration, note)
    write_json(out_dir / "tests.json", {"run": summary, "tests": records})

    runs_path = out_dir / "test_runs.json"
    runs = json.loads(runs_path.read_text(encoding="utf-8")) if runs_path.exists() else []
    if history:
        runs.append(summary)
    write_json(runs_path, runs)
    return summary, proc


def write_dashboard_data(out_dir=OUT):
    """AC list and agreement copy: data the dashboard reads besides the test run."""
    write_json(Path(out_dir) / "acceptance_criteria.json",
               {"enforced_through_phase": ENFORCED_THROUGH_PHASE, "acs": spec_acs()})
    write_json(Path(out_dir) / "agreement.json", json.loads(AGREEMENT.read_text(encoding="utf-8")))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("targets", nargs="*", help="pytest targets (default: tests/)")
    ap.add_argument("--note", help="label for this run in the history, e.g. 'canary run'")
    ap.add_argument("--no-history", action="store_true", help="write tests.json but do not append to test_runs.json (development runs)")
    args = ap.parse_args(argv)
    write_dashboard_data()
    summary, proc = run(args.targets or None, note=args.note, history=not args.no_history)
    print("%s: %d tests, %d passed, %d failed, %d errors, %d skipped (%.1fs)" % (
        summary["run_id"], summary["total"], summary["passed"], summary["failed"],
        summary["errors"], summary["skipped"], summary["duration"]))
    for t in summary["failed_tests"]:
        print("  FAILED " + t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
