#!/usr/bin/env python3
# Purpose: Validate enriched public skill index schema and output-contract markers across skills/templates.
# Created Date: 2026-02-20
# Last Updated Date: 2026-02-20

from pathlib import Path
import sys

try:
    import yaml
except ImportError:
    print("[FAIL] PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)


REQUIRED_INDEX_FIELDS = (
    "name",
    "description",
    "url",
    "source_registry",
    "summary_short",
    "summary_long",
    "capabilities",
    "requirements",
    "risk_flags",
    "quality_signals",
)

HARDENING_RULES = {
    "refresh_public_skill_index.py": (
        "def sanitize_text(",
        "def sanitize_url(",
        "def report_error(",
        "errors=\"replace\"",
        "file=sys.stderr",
    ),
    "skill_validation_scan.py": (
        "sanitize_for_output(",
        "errors=\"replace\"",
        "file=sys.stderr",
        "try:",
    ),
}

TOOLING_POLICY_MARKERS = {
    "context_rule": (
        Path(".cursor/rules/localsetup-context.mdc"),
        "Python-first tooling:",
    ),
    "tooling_doc": (
        Path("_localsetup/docs/TOOLING_POLICY.md"),
        "Minimum supported version: Python 3.10.",
    ),
    "install_bash": (
        Path("install"),
        'MIN_PYTHON_VERSION="3.10.0"',
    ),
    "install_ps1": (
        Path("install.ps1"),
        "$MinPythonVersion = [Version]'3.10.0'",
    ),
}


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)


def validate_index(index_path: Path, errors: list[str]) -> None:
    if not index_path.exists():
        fail(f"Missing file: {index_path}", errors)
        return
    try:
        data = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        fail(f"Failed to parse YAML: {index_path} ({exc})", errors)
        return

    schema_version = data.get("schema_version")
    if not isinstance(schema_version, int) or schema_version < 2:
        fail(f"Invalid schema_version in {index_path}: expected int >= 2", errors)

    skills = data.get("skills")
    if not isinstance(skills, list) or not skills:
        fail(f"Missing or empty skills list in {index_path}", errors)
        return

    for idx, skill in enumerate(skills, start=1):
        if not isinstance(skill, dict):
            fail(f"skills[{idx}] is not a mapping", errors)
            continue
        for field in REQUIRED_INDEX_FIELDS:
            if field not in skill:
                fail(f"skills[{idx}] missing field: {field}", errors)


def validate_markers(engine_dir: Path, errors: list[str]) -> None:
    required_markers = {
        engine_dir / "skills" / "localsetup-context" / "SKILL.md": "## Output contract (low token, always apply)",
        engine_dir / "skills" / "localsetup-communication-and-tools" / "SKILL.md": "**Output contract (always):**",
        engine_dir / "skills" / "localsetup-skill-discovery" / "SKILL.md": "Presentation fallback by platform capability:",
        engine_dir / "templates" / "cursor" / "localsetup-context.mdc": "## Output contract (low token, always apply)",
        engine_dir / "templates" / "claude-code" / "CLAUDE.md": "## Output contract (low token, always apply)",
        engine_dir / "templates" / "codex" / "AGENTS.md": "## Output contract (low token, always apply)",
        engine_dir / "templates" / "openclaw" / "OPENCLAW_CONTEXT.md": "## Output contract (low token, always apply)",
    }
    for file_path, marker in required_markers.items():
        if not file_path.exists():
            fail(f"Missing file: {file_path}", errors)
            continue
        text = file_path.read_text(encoding="utf-8", errors="replace")
        if marker not in text:
            fail(f"Missing marker in {file_path}: {marker}", errors)


def validate_external_input_hardening(engine_dir: Path, errors: list[str]) -> None:
    tools_dir = engine_dir / "tools"
    for filename, required_tokens in HARDENING_RULES.items():
        file_path = tools_dir / filename
        if not file_path.exists():
            fail(f"Missing file for hardening check: {file_path}", errors)
            continue
        text = file_path.read_text(encoding="utf-8", errors="replace")
        for token in required_tokens:
            if token not in text:
                fail(f"Hardening token missing in {file_path}: {token}", errors)


def validate_tooling_policy(repo_root: Path, errors: list[str]) -> None:
    for name, (rel_path, marker) in TOOLING_POLICY_MARKERS.items():
        file_path = repo_root / rel_path
        if not file_path.exists():
            fail(f"Missing tooling policy file ({name}): {file_path}", errors)
            continue
        text = file_path.read_text(encoding="utf-8", errors="replace")
        if marker not in text:
            fail(f"Missing tooling policy marker in {file_path}: {marker}", errors)


def main() -> int:
    engine_dir = Path(__file__).resolve().parents[1]
    repo_root = engine_dir.parent
    errors: list[str] = []

    validate_index(engine_dir / "docs" / "PUBLIC_SKILL_INDEX.yaml", errors)
    validate_markers(engine_dir, errors)
    validate_external_input_hardening(engine_dir, errors)
    validate_tooling_policy(repo_root, errors)

    if errors:
        print("[FAIL] Output contract and hardening validation failed")
        for e in errors[:200]:
            print(f" - {e}")
        if len(errors) > 200:
            print(f" - ... and {len(errors) - 200} more")
        return 1

    print("[OK] Output contract, enriched index, and hardening validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
