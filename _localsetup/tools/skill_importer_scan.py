#!/usr/bin/env python3
# Purpose: Scan directory for Agent Skills; per-skill brief and security flags.
# Created: 2026-02-20

import argparse
import re
import subprocess
import sys
from pathlib import Path

SECURITY_PATTERNS = re.compile(
    r"eval\s*\(|curl\s+.*\|\s*sh\s|Invoke-Expression|/etc/shadow|NOPASSWD",
    re.IGNORECASE,
)


def extract_frontmatter(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    if "---" not in text:
        return ""
    parts = text.split("---", 2)
    return parts[1].strip() if len(parts) >= 2 else ""


def get_yaml(fm_block, key):
    for line in fm_block.splitlines():
        if line.strip().startswith(key + ":"):
            return line.split(":", 1)[1].strip().strip("'\"").strip()
    return ""


def skill_brief(skill_dir, scan_root, validation_script):
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return False
    fm = extract_frontmatter(skill_md)
    name = get_yaml(fm, "name")
    if not name:
        return False
    desc = get_yaml(fm, "description") or "(no description)"
    print("---")
    print("Skill:", name)
    print("Directory:", skill_dir.name)
    print("Description:", desc)
    for sub in ("scripts", "references", "assets"):
        subpath = skill_dir / sub
        if subpath.is_dir():
            print("Has %s:" % sub)
            for f in sorted(subpath.rglob("*")):
                if f.is_file():
                    print("  -", f.name)
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.is_dir():
        exts = set(f.suffix.lstrip(".") for f in scripts_dir.rglob("*") if f.is_file() and f.suffix)
        if exts:
            print("Code types:", " ".join(sorted(exts)))
    hits = []
    for subpath in [skill_dir / "scripts", skill_dir / "assets"]:
        if subpath.is_dir():
            for f in subpath.rglob("*"):
                if f.is_file():
                    try:
                        for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                            if SECURITY_PATTERNS.search(line):
                                hits.append("%s:%d" % (f, i))
                    except Exception:
                        pass
    if hits:
        print("Security: REVIEW (heuristic flags)")
        for h in hits[:5]:
            print(" ", h)
    else:
        print("Security: No heuristic concerns")
    if validation_script.exists():
        r = subprocess.run([sys.executable, str(validation_script), "--scan-root", str(scan_root), str(skill_dir)], capture_output=True, text=True, timeout=30)
        if r.returncode != 0 and r.stderr:
            sys.stderr.write("  Content safety: ERROR (validation script failed).\n")
    print("")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    args = ap.parse_args()
    scan_root = args.path.resolve()
    if not scan_root.is_dir():
        sys.stderr.write("Not a directory: %s\n" % scan_root)
        return 1
    engine_dir = Path(__file__).resolve().parents[1]
    validation_script = engine_dir / "tools" / "skill_validation_scan.py"
    if validation_script.exists():
        r = subprocess.run([sys.executable, str(validation_script), "--ensure-only", "--scan-root", str(scan_root)], capture_output=True, text=True, timeout=30)
        if r.returncode == 2:
            if r.stderr:
                sys.stderr.write(r.stderr)
            return 2
        if r.returncode != 0:
            if r.stderr:
                sys.stderr.write(r.stderr)
            return 1
    count = 0
    for skill_md in sorted(scan_root.rglob("SKILL.md")):
        if skill_md.is_file() and len(skill_md.relative_to(scan_root).parts) <= 6:
            fm = extract_frontmatter(skill_md)
            if get_yaml(fm, "name") and skill_brief(skill_md.parent, scan_root, validation_script):
                count += 1
    if count == 0:
        sys.stderr.write("No valid skills found (SKILL.md with name/description).\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
