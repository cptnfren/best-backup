#!/usr/bin/env python3
# Purpose: Generate public doc artifacts from canonical framework sources.
# Created: 2026-02-19
# Last updated: 2026-02-19

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


FRONTMATTER_BOUNDARY = re.compile(r"^---\s*$", re.MULTILINE)
VERSION_RE = re.compile(r'^\s*version:\s*["\']?([0-9.]+)["\']?\s*$')


def read_frontmatter(md_path: Path) -> dict[str, str]:
    text = md_path.read_text(encoding="utf-8")
    parts = FRONTMATTER_BOUNDARY.split(text, maxsplit=2)
    if len(parts) < 3:
        return {}
    block = parts[1].splitlines()

    name = ""
    desc = ""
    version = ""

    i = 0
    while i < len(block):
        line = block[i]
        stripped = line.strip()

        if stripped.startswith("name:"):
            name = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            i += 1
            continue

        if stripped.startswith("description:"):
            raw = stripped.split(":", 1)[1].strip()
            if raw in {"|", ">", "|-", ">-"}:
                desc_lines = []
                i += 1
                while i < len(block):
                    cont = block[i]
                    if cont.startswith("  ") or cont.startswith("\t"):
                        desc_lines.append(cont.strip())
                        i += 1
                        continue
                    if not cont.strip():
                        desc_lines.append("")
                        i += 1
                        continue
                    break
                desc = " ".join([s for s in desc_lines if s]).strip()
                continue
            desc = raw.strip().strip('"').strip("'")
            i += 1
            continue

        m = VERSION_RE.match(line)
        if m:
            version = m.group(1).strip()

        i += 1

    return {
        "name": name or "",
        "description": desc or "",
        "version": version or "",
    }


def collect_skills(skills_dir: Path) -> list[dict[str, str]]:
    skills = []
    for skill_md in sorted(skills_dir.glob("localsetup-*/SKILL.md")):
        fm = read_frontmatter(skill_md)
        skill_id = skill_md.parent.name
        name = fm.get("name", "") or skill_id
        description = fm.get("description", "").replace("\n", " ").strip()
        version = fm.get("version", "")
        skills.append(
            {
                "id": skill_id,
                "name": name,
                "description": description,
                "version": version,
                "path": str(skill_md.relative_to(skills_dir.parents[1])),
            }
        )
    return skills


def collect_platforms(platform_registry: Path) -> list[dict[str, str]]:
    rows = []
    for line in platform_registry.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        if line.startswith("| ID ") or line.startswith("|----"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) != 4:
            continue
        platform_id, display, context_loader, skills_path = parts
        if not platform_id:
            continue
        rows.append(
            {
                "id": platform_id,
                "display_name": display,
                "context_loader": context_loader,
                "skills_path": skills_path,
            }
        )
    return rows


def write_skills_md(path: Path, major_minor: str, skills: list[dict[str, str]]) -> None:
    lines = [
        "---",
        "status: ACTIVE",
        f"version: {major_minor}",
        "---",
        "",
        "# Shipped skills catalog",
        "",
        "This page is generated from `_localsetup/skills/*/SKILL.md`.",
        "",
        f"Total shipped skills: {len(skills)}",
        "",
        "| Skill ID | Name | Version | Description |",
        "|---|---|---|---|",
    ]

    for skill in skills:
        desc = (skill["description"] or "").replace("|", "\\|")
        if not desc:
            desc = "No description in frontmatter."
        lines.append(
            f"| `{skill['id']}` | `{skill['name']}` | `{skill['version'] or 'n/a'}` | {desc} |"
        )

    year = datetime.now(timezone.utc).year
    lines.extend(
        [
            "",
            "---",
            "",
            '<p align="center">',
            "<strong>Author:</strong> <a href=\"https://github.com/cptnfren\">Slavic Kozyuk</a><br>",
            f"<strong>Copyright</strong> © {year} <a href=\"https://www.cruxexperts.com/\">Crux Experts LLC</a> – Innovate, Automate, Dominate.",
            "</p>",
            "",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_facts_json(path: Path, facts: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")


def write_internal_snapshot(path: Path, facts: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Internal docs snapshot",
        "",
        "Local-only generated report. Do not commit.",
        "",
        f"- generated_at: {facts['generated_at']}",
        f"- version: {facts['version']}",
        f"- platform_count: {facts['platform_count']}",
        f"- skill_count: {facts['skill_count']}",
        "",
        "## Platforms",
    ]
    for p in facts["platforms"]:
        lines.append(f"- {p['id']}: {p['display_name']}")
    lines.append("")
    lines.append("## Skills")
    for skill in facts["skills"]:
        lines.append(f"- {skill['id']}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def replace_managed_block(path: Path, marker: str, content: str) -> None:
    start = f"<!-- {marker}:start -->"
    end = f"<!-- {marker}:end -->"
    text = path.read_text(encoding="utf-8")
    if start not in text or end not in text:
        return
    pre, rest = text.split(start, 1)
    _, post = rest.split(end, 1)
    new_text = f"{pre}{start}\n{content}\n{end}{post}"
    path.write_text(new_text, encoding="utf-8")


def update_facts_blocks(repo_root: Path, facts: dict) -> None:
    platforms = ", ".join([p["id"] for p in facts["platforms"]])

    readme_block = "\n".join(
        [
            "| Fact | Value |",
            "|---|---|",
            f"| Current version | `{facts['version']}` |",
            f"| Supported platforms | `{platforms}` |",
            f"| Shipped skills | `{facts['skill_count']}` |",
            "| Source | `_localsetup/docs/_generated/facts.json` |",
        ]
    )
    docs_index_block = "\n".join(
        [
            f"- Current version: `{facts['version']}`",
            f"- Supported platforms: `{platforms}`",
            f"- Shipped skills: `{facts['skill_count']}`",
            "- Source: `_localsetup/docs/_generated/facts.json`",
        ]
    )

    replace_managed_block(repo_root / "README.md", "facts-block", readme_block)
    replace_managed_block(repo_root / "_localsetup" / "docs" / "README.md", "facts-block", docs_index_block)
    replace_managed_block(repo_root / "_localsetup" / "docs" / "FEATURES.md", "facts-block", docs_index_block)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Localsetup documentation artifacts.")
    parser.add_argument("--repo-root", default=None, help="Repository root path.")
    parser.add_argument(
        "--internal-output",
        default="",
        help="Optional path for local-only internal snapshot report. Disabled by default.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[2]

    version = (repo_root / "VERSION").read_text(encoding="utf-8").strip()
    major_minor = ".".join(version.split(".")[:2]) if "." in version else version

    skills_dir = repo_root / "_localsetup" / "skills"
    docs_dir = repo_root / "_localsetup" / "docs"
    platform_registry = docs_dir / "PLATFORM_REGISTRY.md"

    skills = collect_skills(skills_dir)
    platforms = collect_platforms(platform_registry)

    facts = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": version,
        "major_minor": major_minor,
        "platform_count": len(platforms),
        "skill_count": len(skills),
        "platforms": platforms,
        "skills": [
            {"id": s["id"], "name": s["name"], "version": s["version"], "path": s["path"]}
            for s in skills
        ],
    }

    write_skills_md(docs_dir / "SKILLS.md", major_minor, skills)
    write_facts_json(docs_dir / "_generated" / "facts.json", facts)
    if args.internal_output:
        write_internal_snapshot(repo_root / args.internal_output, facts)
    update_facts_blocks(repo_root, facts)

    print("Generated: _localsetup/docs/SKILLS.md")
    print("Generated: _localsetup/docs/_generated/facts.json")
    if args.internal_output:
        print(f"Generated: {args.internal_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
