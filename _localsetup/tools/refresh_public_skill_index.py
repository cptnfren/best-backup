#!/usr/bin/env python3
# Purpose: Refresh PUBLIC_SKILL_INDEX.yaml from PUBLIC_SKILL_REGISTRY.urls.
# Created: 2026-02-18
# Last Updated: 2026-02-27
# Requires: PyYAML, requests (see _localsetup/requirements.txt)

"""
Fetches each registry URL, parses skill entries (awesome-list markdown or
GitHub API), normalizes to index schema, and writes PUBLIC_SKILL_INDEX.yaml
with updated set to current ISO8601 time.
"""

import re
import sys
import os
import traceback
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# Resolve lib/ relative to this tool (tools/ -> lib/)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from deps import require_deps  # noqa: E402

require_deps(["yaml", "requests"])

import requests  # noqa: E402
import yaml  # noqa: E402

# Module-level session shared by all fetch operations in this process.
_SESSION = requests.Session()
_SESSION.headers["User-Agent"] = "Localsetup-Skill-Index/1.0"

# Awesome list: - [name](url) - description
AWESOME_LINE = re.compile(r"^\s*-\s*\[([^\]]+)\]\(([^)]+)\)\s*-\s*(.+)$")
# Optional category from ## Section Name (we capture current section while scanning)
SECTION_HEADER = re.compile(r"^##\s+(.+)$")

REGISTRY_AWESOME = "https://github.com/VoltAgent/awesome-openclaw-skills"
REGISTRY_ANTHROPICS = "https://github.com/anthropics/skills/tree/main/skills"
RAW_AWESOME = "https://raw.githubusercontent.com/VoltAgent/awesome-openclaw-skills/main/README.md"
API_ANTHROPICS = "https://api.github.com/repos/anthropics/skills/contents/skills"

DESC_MAX = 300  # cap description length for index
MAX_FIELD_LEN = 512

CAPABILITY_KEYWORDS = {
    "pdf": ["pdf", "ocr", "document conversion", "docx", "report"],
    "docs": ["markdown", "documentation", "docs", "wiki", "readme"],
    "search": ["search", "discover", "lookup", "index"],
    "github": ["github", "pull request", "pr", "issue", "workflow"],
    "automation": ["automation", "pipeline", "ci", "cd", "deploy"],
    "testing": ["test", "pytest", "jest", "coverage", "lint"],
    "security": ["security", "scan", "vulnerability", "threat", "redact"],
    "data": ["api", "json", "yaml", "dataset", "parse", "extract"],
}

REQUIREMENT_HINTS = {
    "api_key": ["api key", "token", "credential", "auth", "oauth"],
    "external_service": ["api", "service", "saas", "cloud"],
    "python": ["python", "pip", "pytest"],
    "node": ["node", "npm", "javascript", "typescript"],
}

RISK_HINTS = {
    "external_network": ["http", "api", "github.com", "service", "remote"],
    "credential_usage": ["token", "api key", "credential", "oauth", "secret"],
    "file_write": ["write", "create", "save", "export", "generate"],
    "command_execution": ["shell", "command", "run", "execute", "terminal"],
}


def fetch_text(url: str) -> str:
    try:
        resp = _SESSION.get(url, timeout=60)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        raise OSError(f"HTTP fetch failed for {url}: {exc}") from exc


def fetch_json(url: str):
    text = fetch_text(url)
    try:
        import json
        return json.loads(text)
    except Exception as exc:
        raise ValueError(f"Invalid JSON payload from {url}: {exc}") from exc


def report_error(context: str, exc: Exception) -> None:
    """Print actionable, non-silent errors for agent or human debugging."""
    print(f"[WARNING] {context}: {type(exc).__name__}: {exc}", file=sys.stderr)
    if os.environ.get("LOCALSETUP_DEBUG", "").strip() == "1":
        traceback.print_exc(file=sys.stderr)


def sanitize_text(value: str, max_len: int = MAX_FIELD_LEN) -> str:
    """
    Defensive normalization for hostile or malformed input:
    - strips control chars (except space)
    - collapses whitespace
    - truncates to prevent oversized fields
    """
    if not value:
        return ""
    cleaned = []
    for c in value:
        oc = ord(c)
        if c == "\n" or c == "\r" or c == "\t":
            cleaned.append(" ")
        elif oc < 0x20 or oc == 0x7F:
            continue
        else:
            cleaned.append(c)
    out = " ".join("".join(cleaned).split()).strip()
    if max_len and len(out) > max_len:
        return out[: max_len - 3] + "..."
    return out


def sanitize_url(value: str) -> str:
    """Allow only http/https URLs and strip control chars."""
    candidate = sanitize_text(value, max_len=2048)
    if not candidate:
        return ""
    parsed = urllib.parse.urlparse(candidate)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    return candidate


def parse_awesome_list(text: str, source_registry: str) -> list[dict]:
    skills = []
    current_category = ""
    for line in text.splitlines():
        m = SECTION_HEADER.match(line)
        if m:
            current_category = sanitize_text(m.group(1).strip(), max_len=120)
            continue
        m = AWESOME_LINE.match(line)
        if not m:
            continue
        name = sanitize_text(m.group(1).strip(), max_len=140)
        url = sanitize_url(m.group(2).strip())
        desc = sanitize_text(m.group(3).strip(), max_len=DESC_MAX)
        if not name or not url:
            continue
        if len(desc) > DESC_MAX:
            desc = desc[: DESC_MAX - 3] + "..."
        entry = {
            "name": name,
            "description": desc or name,
            "url": url,
            "source_registry": source_registry,
        }
        if current_category:
            entry["category"] = current_category
        skills.append(entry)
    return skills


def fetch_anthropics_skills(source_registry: str) -> list[dict]:
    data = fetch_json(API_ANTHROPICS)
    if not isinstance(data, list):
        raise ValueError("Anthropic API payload is not a list")
    skills = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "dir":
            continue
        name = sanitize_text(str(item.get("name", "")), max_len=140)
        url = sanitize_url(str(item.get("html_url", "")))
        if not name or not url:
            continue
        desc = name.replace("-", " ").title()
        skills.append({
            "name": name,
            "description": f"Anthropic skill: {desc}",
            "url": url,
            "source_registry": source_registry,
        })
    return skills


def _first_sentence(text: str) -> str:
    text = " ".join(text.split())
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
    return parts[0][:220]


def infer_capabilities(text: str) -> list[str]:
    t = text.lower()
    out = []
    for cap, words in CAPABILITY_KEYWORDS.items():
        if any(w in t for w in words):
            out.append(cap)
    return out


def infer_requirements(text: str) -> list[str]:
    t = text.lower()
    out = []
    for req, words in REQUIREMENT_HINTS.items():
        if any(w in t for w in words):
            out.append(req)
    return out


def infer_risks(text: str) -> list[str]:
    t = text.lower()
    out = []
    for risk, words in RISK_HINTS.items():
        if any(w in t for w in words):
            out.append(risk)
    return out


def enrich_entry(entry: dict) -> dict:
    name = sanitize_text(entry.get("name", "").strip(), max_len=140)
    desc = sanitize_text(entry.get("description", "").strip(), max_len=DESC_MAX)
    url = sanitize_url(entry.get("url", "").strip())
    category = sanitize_text(entry.get("category", "").strip(), max_len=120)
    source = sanitize_text(entry.get("source_registry", "").strip(), max_len=160)
    if not name:
        name = "unknown-skill"
    if not url:
        url = "https://example.invalid/unknown"

    short = _first_sentence(desc) or name
    capability_text = " ".join(x for x in [name, desc, category] if x)
    capabilities = infer_capabilities(capability_text)
    requirements = infer_requirements(capability_text)
    risks = infer_risks(" ".join([capability_text, url]))

    long_summary_parts = [short]
    if capabilities:
        long_summary_parts.append(f"Primary capabilities: {', '.join(capabilities)}.")
    if requirements:
        long_summary_parts.append(f"Likely requirements: {', '.join(requirements)}.")
    if "external_network" in risks:
        long_summary_parts.append("May require network access.")
    long_summary = " ".join(long_summary_parts)

    quality_signals = {
        "has_description": bool(desc),
        "description_length": len(desc),
        "has_category": bool(category),
        "source_registry": source,
        "url_domain_hint": "github" if "github.com" in url.lower() else "other",
    }

    out = dict(entry)
    out["summary_short"] = short
    out["summary_long"] = long_summary[:420]
    out["capabilities"] = capabilities
    out["requirements"] = requirements
    out["risk_flags"] = risks
    out["quality_signals"] = quality_signals
    return out


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    docs = repo_root / "_localsetup" / "docs"
    if not docs.is_dir():
        docs = repo_root / "docs"
    index_path = docs / "PUBLIC_SKILL_INDEX.yaml"
    registry_path = docs / "PUBLIC_SKILL_REGISTRY.urls"

    sources = [
        "https://github.com/VoltAgent/awesome-openclaw-skills",
        "https://github.com/anthropics/skills/tree/main/skills",
    ]
    if registry_path.exists():
        for line in registry_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = sanitize_text(line.strip(), max_len=2048)
            if line and not line.startswith("#"):
                safe_line = sanitize_url(line)
                if safe_line and safe_line not in sources:
                    sources.append(safe_line)

    all_skills = []
    seen_urls = set()

    # Awesome OpenClaw list
    try:
        text = fetch_text(RAW_AWESOME)
        for s in parse_awesome_list(text, REGISTRY_AWESOME):
            if s["url"] not in seen_urls:
                seen_urls.add(s["url"])
                all_skills.append(s)
    except Exception as e:
        report_error("awesome list fetch failed", e)

    # Anthropics skills
    try:
        for s in fetch_anthropics_skills(REGISTRY_ANTHROPICS):
            if s["url"] not in seen_urls:
                seen_urls.add(s["url"])
                all_skills.append(s)
    except Exception as e:
        report_error("anthropics fetch failed", e)

    enriched = [enrich_entry(s) for s in all_skills]
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = {
        "schema_version": 2,
        "sources": sources,
        "updated": updated,
        "skills": enriched,
    }

    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("# Public skill index - refresh periodically from PUBLIC_SKILL_REGISTRY.urls.\n")
        f.write("# Used by localsetup-skill-discovery to recommend similar public skills when\n")
        f.write("# the user is creating or importing a skill. Schema: sources, updated (ISO8601), skills.\n")
        yaml.dump(out, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000)

    print(f"Wrote {len(all_skills)} skills to {index_path} (updated={updated})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
