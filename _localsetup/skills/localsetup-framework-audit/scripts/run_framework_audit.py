#!/usr/bin/env python3
# Purpose: Run framework audit (doc, link, skill matrix, version/facts); output to user path only.
# Created: 2026-02-20
# Last updated: 2026-02-20

"""
Single entrypoint for pre-release audit. Phases: doc checks, link checks, skill matrix
(sandbox), version/facts, maintainer refs. Output path from --output or LOCALSETUP_AUDIT_OUTPUT;
no in-repo default. Exit 0 only when zero errors. Follows INPUT_HARDENING_STANDARD.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

# Limits and patterns (INPUT_HARDENING)
OUTPUT_PATH_MAX = 4096
PATH_COMPONENT_MAX = 256
# Plain "see docs/..." or "See _localsetup/..." that should be markdown links
PLAIN_SEE_DOCS = re.compile(r"\b[Ss]ee\s+docs/[^\s\]\)\"']+")
PLAIN_SEE_LOCALSETUP = re.compile(r"\b[Ss]ee\s+_localsetup/[^\s\]\)\"']+")
MAINTAINER_PATTERN = re.compile(r"scripts/maintain|localsetup-maintainer")
VERSION_LINE = re.compile(r"^\*\*Version:\*\*\s*([\d.]+)", re.MULTILINE)


def _script_dir() -> Path:
    return Path(__file__).resolve().parent


def _framework_root() -> Path:
    # scripts/ -> skill dir -> skills/ -> _localsetup/
    return _script_dir().parent.parent.parent


def _repo_root() -> Path:
    return _framework_root().parent


def _sanitize_output_path(s: str | None) -> Path | None:
    if s is None or (isinstance(s, str) and not s.strip()):
        return None
    s = s.strip().strip("\x00")[:OUTPUT_PATH_MAX]
    if not s:
        return None
    p = Path(s).resolve()
    for part in p.parts:
        if len(part) > PATH_COMPONENT_MAX:
            raise ValueError(f"path component too long: {part[:32]}...")
    return p


def _read_version_file(root: Path) -> str | None:
    vf = root / "VERSION"
    if not vf.is_file():
        return None
    try:
        line = vf.read_text(encoding="utf-8", errors="replace").strip().split("\n")[0].strip()
        return line[:64] if line else None
    except OSError:
        return None


def _read_readme_version(root: Path) -> str | None:
    readme = root / "README.md"
    if not readme.is_file():
        return None
    try:
        text = readme.read_text(encoding="utf-8", errors="replace")
        m = VERSION_LINE.search(text)
        return m.group(1).strip() if m else None
    except OSError:
        return None


def _read_facts_version(root: Path) -> str | None:
    facts = root / "_localsetup" / "docs" / "_generated" / "facts.json"
    if not facts.is_file():
        return None
    try:
        text = facts.read_text(encoding="utf-8", errors="replace")
        if '"version"' in text:
            m = re.search(r'"version"\s*:\s*"([^"]+)"', text)
            return m.group(1).strip() if m else None
    except OSError:
        pass
    return None


def phase_doc_checks(root: Path, fw: Path) -> list[str]:
    errors: list[str] = []
    required = [
        root / "VERSION",
        root / "README.md",
        root / "docs" / "VERSIONING.md",
        fw / "README.md",
        fw / "docs" / "README.md",
        fw / "tests" / "skill_smoke_commands.yaml",
    ]
    for p in required:
        if not p.exists():
            errors.append(f"Missing required doc/path: {p.relative_to(root)}")
    return errors


def phase_link_checks(root: Path) -> list[tuple[str, int, str]]:
    """Return list of (file, line_no, snippet) for plain 'see docs/...' or 'See _localsetup/...'."""
    findings: list[tuple[str, int, str]] = []
    for md in root.rglob("*.md"):
        try:
            rel = md.relative_to(root)
            if "_generated" in rel.parts or "node_modules" in rel.parts:
                continue
            text = md.read_text(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue
        for i, line in enumerate(text.split("\n"), 1):
            if "](docs/" in line or "](_localsetup/" in line:
                continue
            if PLAIN_SEE_DOCS.search(line) or PLAIN_SEE_LOCALSETUP.search(line):
                findings.append((str(rel), i, line.strip()[:80]))
    return findings


def phase_skill_matrix(root: Path, fw: Path) -> tuple[list[str], list[str]]:
    """Run sandbox smoke for each skill with a command. Return (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []
    smoke_file = fw / "tests" / "skill_smoke_commands.yaml"
    if not smoke_file.is_file():
        errors.append("Missing skill_smoke_commands.yaml")
        return (errors, warnings)
    if yaml is None:
        errors.append("PyYAML required for skill matrix")
        return (errors, warnings)
    try:
        data = yaml.safe_load(smoke_file.read_text(encoding="utf-8", errors="replace"))
    except (OSError, yaml.YAMLError) as e:
        errors.append(f"Could not load smoke list: {e}")
        return (errors, warnings)
    if not isinstance(data, dict):
        errors.append("skill_smoke_commands.yaml must be a YAML map")
        return (errors, warnings)
    skills_dir = fw / "skills"
    create_sandbox = fw / "skills" / "localsetup-skill-sandbox-tester" / "scripts" / "create_sandbox.py"
    run_smoke = fw / "skills" / "localsetup-skill-sandbox-tester" / "scripts" / "run_smoke.py"
    if not create_sandbox.is_file() or not run_smoke.is_file():
        errors.append("Sandbox tooling (create_sandbox.py, run_smoke.py) not found")
        return (errors, warnings)
    for skill_id, cmd in data.items():
        if not isinstance(cmd, str) or cmd.strip().upper() == "N/A":
            continue
        skill_path = skills_dir / skill_id
        if not skill_path.is_dir():
            warnings.append(f"Smoke list references missing skill dir: {skill_id}")
            continue
        try:
            cp = subprocess.run(
                [sys.executable, str(create_sandbox), "--skill-path", str(skill_path)],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if cp.returncode != 0:
                errors.append(f"Skill matrix {skill_id}: create_sandbox failed: {cp.stderr or cp.stdout}")
                continue
            sandbox_dir = cp.stdout.strip().split("\n")[-1].strip()
            if not sandbox_dir:
                errors.append(f"Skill matrix {skill_id}: empty sandbox path")
                continue
            cp2 = subprocess.run(
                [sys.executable, str(run_smoke), "--sandbox-dir", sandbox_dir, "--command", cmd],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if cp2.returncode != 0:
                errors.append(f"Skill matrix {skill_id}: smoke failed (exit {cp2.returncode})")
        except subprocess.TimeoutExpired:
            errors.append(f"Skill matrix {skill_id}: timeout")
        except Exception as e:
            errors.append(f"Skill matrix {skill_id}: {e}")
    return (errors, warnings)


def phase_version_facts(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    v = _read_version_file(root)
    rv = _read_readme_version(root)
    fv = _read_facts_version(root)
    if not v:
        errors.append("VERSION file missing or unreadable")
    if not rv:
        errors.append("README.md version line (**Version:** X.Y.Z) missing or unreadable")
    if v and rv and v != rv:
        errors.append(f"VERSION ({v}) != README version ({rv})")
    if v and fv and v != fv:
        errors.append(f"VERSION ({v}) != facts.json version ({fv})")
    if not (root / "_localsetup" / "docs" / "_generated" / "facts.json").is_file():
        warnings.append("facts.json missing; version/facts comparison partial")
    return (errors, warnings)


def phase_maintainer_refs(root: Path) -> list[str]:
    findings: list[str] = []
    for md in root.rglob("*.md"):
        try:
            rel = md.relative_to(root)
            if "_generated" in rel.parts:
                continue
            text = md.read_text(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue
        for i, line in enumerate(text.split("\n"), 1):
            if MAINTAINER_PATTERN.search(line):
                findings.append(f"{rel}:{i}: {line.strip()[:72]}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run framework audit (doc, link, skill matrix, version/facts). Output to --output or LOCALSETUP_AUDIT_OUTPUT; no file written if unset."
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="PATH",
        help="Write full report to this path (or set LOCALSETUP_AUDIT_OUTPUT)",
    )
    args = parser.parse_args()
    out_path = args.output or os.environ.get("LOCALSETUP_AUDIT_OUTPUT")
    try:
        out_resolved = _sanitize_output_path(out_path) if out_path else None
    except ValueError as e:
        print(f"run_framework_audit: {e}", file=sys.stderr)
        return 2
    root = _repo_root()
    fw = _framework_root()
    all_errors: list[str] = []
    all_warnings: list[str] = []
    link_findings: list[tuple[str, int, str]] = []
    maintainer_findings: list[str] = []

    # Phase 1: doc checks
    all_errors.extend(phase_doc_checks(root, fw))
    # Phase 2: link checks
    link_findings = phase_link_checks(root)
    for f, ln, snip in link_findings:
        all_warnings.append(f"Plain link candidate {f}:{ln}: {snip}")
    # Phase 3: skill matrix
    em, wm = phase_skill_matrix(root, fw)
    all_errors.extend(em)
    all_warnings.extend(wm)
    # Phase 4: version/facts
    ev, wv = phase_version_facts(root)
    all_errors.extend(ev)
    all_warnings.extend(wv)
    # Phase 5: maintainer refs
    maintainer_findings = phase_maintainer_refs(root)
    if maintainer_findings:
        all_warnings.extend([f"Maintainer ref: {x}" for x in maintainer_findings[:20]])

    # Report
    report_lines: list[str] = []
    report_lines.append("# Framework audit report")
    report_lines.append("")
    report_lines.append(f"Repo root: {root}")
    report_lines.append("")
    report_lines.append("## Summary")
    report_lines.append(f"- Errors: {len(all_errors)}")
    report_lines.append(f"- Warnings: {len(all_warnings)}")
    report_lines.append("")
    if all_errors:
        report_lines.append("## Errors")
        for e in all_errors:
            report_lines.append(f"- {e}")
        report_lines.append("")
    if all_warnings:
        report_lines.append("## Warnings")
        for w in all_warnings:
            report_lines.append(f"- {w}")
        report_lines.append("")
    report_lines.append("## requires_review / human_decision")
    report_lines.append("Review errors and warnings above. Fix errors before release; accept or fix warnings.")
    report_lines.append("Doc-only skills: agent produces step summary and logic-gap notes per SKILL.md; no script run.")
    report_lines.append("")

    summary = f"Errors: {len(all_errors)}, Warnings: {len(all_warnings)}"
    if out_resolved:
        try:
            out_resolved.parent.mkdir(parents=True, exist_ok=True)
            out_resolved.write_text("\n".join(report_lines), encoding="utf-8")
        except OSError as e:
            print(f"run_framework_audit: could not write report: {e}", file=sys.stderr)
            return 1
    print(summary)
    return 0 if not all_errors else 1


if __name__ == "__main__":
    sys.exit(main())
