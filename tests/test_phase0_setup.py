"""Phase 0 acceptance tests: project scaffold and logging hooks (specs/phase-0-setup.md)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "logs" / "events.jsonl"
SETTINGS = ROOT / ".claude" / "settings.json"

REQUIRED_DIRS = [
    "data/raw", "data/processed", "scripts", "tests",
    "docs", "docs/data", "logs", "specs", ".claude/hooks",
]
REQUIRED_FILES = [
    "CLAUDE.md", "SPEC.md", "PROGRESS.md", "specs/codebook.md",
    ".claude/hooks/log_event.py", "requirements.txt", ".gitignore",
]
REQUIRED_HOOKS = ["UserPromptSubmit", "Stop", "PreCompact", "SessionStart"]


def load_events():
    return [json.loads(line) for line in EVENTS.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_AC0_1_architecture_directories_exist():
    missing = [d for d in REQUIRED_DIRS if not (ROOT / d).is_dir()]
    assert not missing, f"missing directories: {missing}"


def test_AC0_1_core_docs_and_setup_files_exist():
    missing = [f for f in REQUIRED_FILES if not (ROOT / f).is_file()]
    assert not missing, f"missing files: {missing}"


def test_AC0_1_every_phase_spec_referenced_in_SPEC_md_exists():
    specs = re.findall(r"specs/phase-\d+-[\w-]+\.md", (ROOT / "SPEC.md").read_text(encoding="utf-8"))
    assert len(set(specs)) == 9, f"expected 9 phase specs (0-8) in SPEC.md, found {sorted(set(specs))}"
    missing = [s for s in specs if not (ROOT / s).is_file()]
    assert not missing, f"phase specs referenced but missing: {missing}"


def test_AC0_2_events_log_lines_are_valid_json_with_ts_and_event():
    assert EVENTS.is_file(), "logs/events.jsonl does not exist"
    lines = [l for l in EVENTS.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert lines, "logs/events.jsonl is empty"
    for i, line in enumerate(lines, 1):
        rec = json.loads(line)  # raises on invalid JSON
        assert "ts" in rec and "event" in rec, f"line {i} missing ts/event: {line[:120]}"


def test_AC0_3_at_least_one_user_prompt_event_logged():
    prompts = [e for e in load_events() if e["event"] == "UserPromptSubmit"]
    assert prompts, "no UserPromptSubmit event in logs/events.jsonl"
    assert any(e.get("prompt") for e in prompts), "UserPromptSubmit events have no prompt text"


def test_AC0_4_settings_registers_all_four_logging_hooks():
    hooks = json.loads(SETTINGS.read_text(encoding="utf-8")).get("hooks", {})
    for name in REQUIRED_HOOKS:
        commands = [h.get("command", "") for entry in hooks.get(name, []) for h in entry.get("hooks", [])]
        assert any("log_event.py" in c for c in commands), f"{name} hook does not run log_event.py"
