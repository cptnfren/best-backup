#!/usr/bin/env python3
# Purpose: Ensure skill validation pattern file (fetch if missing, warn if stale); scan skill dir for content-safety (pattern hits + foreign-language heuristic); output references only (file, line, col, pattern, description from YAML). No skill content is sent to stdout; for safety, only references and pre-defined descriptions.
# Created: 2026-02-19
# Last updated: 2026-02-19

# Optional max file size for body/scripts to avoid DoS (bytes); skip files over this, do not treat as hit.
MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1 MiB
OUTPUT_MAX_FIELD_LEN = 2000  # truncate long fields in output

"""
Ensures SKILL_VALIDATION_PATTERNS.yaml exists (fetches from GitHub if missing).
If file is 7+ days old, prints warning and exits 2 (stale).
Scans a skill directory: SKILL.md body (skill_body/all patterns), scripts/assets (scripts_and_assets/all).
Outputs Content safety section with references only: file, line, column, pattern id, description from YAML.
Baseline: Agent Skills specification (no body format restrictions). We only flag potential hidden prompts:
substantial runs of non-Latin natural-language script (CJK, Cyrillic, Arabic, etc.), not extended Latin or symbols.
"""

import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# Canonical GitHub raw URL for the pattern file (documented in SKILL_VALIDATION_PATTERNS.md)
PATTERN_FILE_RAW_URL = "https://raw.githubusercontent.com/cptnfren/localsetup/main/_localsetup/docs/SKILL_VALIDATION_PATTERNS.yaml"

# Unicode code point ranges for non-Latin natural-language scripts (used to detect possible hidden prompts).
# We do NOT include Latin, Latin-1 supplement, or Latin extended (accents, n-tilde, etc.); those are allowed.
# Box-drawing, symbols, numbers, ASCII are allowed. Flag only substantial runs of e.g. CJK, Cyrillic, Arabic.
FOREIGN_SCRIPT_RANGES = (
    (0x0400, 0x04FF),   # Cyrillic
    (0x0590, 0x05FF),   # Hebrew
    (0x0600, 0x06FF),   # Arabic
    (0x0750, 0x077F),   # Arabic Supplement
    (0x0900, 0x097F),   # Devanagari
    (0x0E00, 0x0E7F),   # Thai
    (0x3040, 0x309F),   # Hiragana
    (0x30A0, 0x30FF),   # Katakana
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs (common)
    (0xAC00, 0xD7AF),   # Hangul Syllables
)


def _is_foreign_script_char(c: str) -> bool:
    """True if c is in a non-Latin natural-language script range (possible hidden prompt)."""
    o = ord(c)
    for lo, hi in FOREIGN_SCRIPT_RANGES:
        if lo <= o <= hi:
            return True
    return False


def has_substantial_foreign_language(text: str, min_run: int = 5) -> bool:
    """
    True if text contains a contiguous run of at least min_run characters from foreign-script ranges.
    Used to flag possible hidden prompts in another language; extended Latin and symbols are not flagged.
    """
    run = 0
    for c in text:
        if _is_foreign_script_char(c):
            run += 1
            if run >= min_run:
                return True
        else:
            run = 0
    return False


def _reject_null_byte(*paths: Path | None) -> None:
    """Raise ValueError if any path string contains null byte."""
    for p in paths:
        if p is not None and "\0" in str(p):
            raise ValueError("Path must not contain null byte")


def _skill_dir_under_scan_root(skill_dir: Path, scan_root: Path) -> bool:
    """True if skill_dir is scan_root or under it."""
    try:
        resolved_skill = skill_dir.resolve()
        resolved_root = scan_root.resolve()
        return resolved_skill == resolved_root or resolved_root in resolved_skill.parents
    except (OSError, RuntimeError):
        return False


def sanitize_for_output(s: str, max_len: int = OUTPUT_MAX_FIELD_LEN) -> str:
    """Replace control chars and DEL with space; truncate. Only for display, never for pattern matching."""
    if not s:
        return ""
    out = []
    for c in s:
        if ord(c) < 0x20 or c == "\x7f":
            out.append(" ")
        else:
            out.append(c)
    result = "".join(out).strip()
    if max_len and len(result) > max_len:
        return result[: max_len - 3] + "..."
    return result


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Localsetup-Skill-Validation/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def resolve_pattern_file_path(pattern_file: Path | None, scan_root: Path) -> Path:
    """Resolve path: explicit > _localsetup/docs/ (under scan_root) > _localsetup/docs/."""
    if pattern_file:
        p = Path(pattern_file)
        if p.is_absolute():
            return p
        return (scan_root / p).resolve()
    # Default: _localsetup/docs/ when running from client repo
    localsetup = scan_root / "_localsetup" / "docs" / "SKILL_VALIDATION_PATTERNS.yaml"
    if localsetup.exists():
        return localsetup
    # Fallback: framework from source (script lives in _localsetup/tools/)
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent / "docs" / "SKILL_VALIDATION_PATTERNS.yaml"


def ensure_pattern_file(path: Path, fetch_if_missing: bool = True) -> tuple[bool, str]:
    """
    Ensure pattern file exists. If missing and fetch_if_missing, fetch and write.
    Returns (ok, message). If file is stale (7+ days), returns (False, "stale") and caller should exit 2.
    """
    if path.exists():
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace")) or {}
        except Exception:
            return False, "read_failed"
        updated_str = data.get("updated") or ""
        if not updated_str:
            return True, "ok"
        try:
            # ISO8601
            updated = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - updated
            if age >= timedelta(days=7):
                return False, "stale"
        except Exception:
            pass
        return True, "ok"
    if not fetch_if_missing:
        return False, "missing"
    try:
        text = fetch_text(PATTERN_FILE_RAW_URL)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Update 'updated' to now in the YAML we write
        data = yaml.safe_load(text) or {}
        data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True), encoding="utf-8")
        return True, "fetched"
    except Exception as e:
        print(f"Failed to fetch pattern file: {e}", file=sys.stderr)
        return False, "fetch_failed"


def load_patterns(path: Path) -> list[dict]:
    """Load YAML and return flat list of patterns with scope, id, description, keywords and/or regex."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace")) or {}
    except Exception:
        raise
    out = []
    for category in ("prompt_injection", "exfiltration", "code_execution", "scripts_and_assets", "crypto_mining", "obfuscation"):
        items = data.get(category)
        if not isinstance(items, list):
            continue
        for p in items:
            if not isinstance(p, dict):
                continue
            scope = p.get("scope") or "all"
            pid = p.get("id") or ""
            desc = p.get("description") or ""
            keywords = p.get("keywords") if isinstance(p.get("keywords"), list) else None
            regex = p.get("regex") if p.get("regex") else None
            if keywords or regex:
                out.append({"scope": scope, "id": pid, "description": desc, "keywords": keywords, "regex": regex})
    return out


def strip_frontmatter(text: str) -> str:
    """Return body after first ---...--- block."""
    if "---" not in text:
        return text
    parts = text.split("---", 2)
    if len(parts) >= 3:
        return parts[2].lstrip("\n")
    return text


def find_matches_in_text(
    text: str, patterns: list[dict], scope_filter: str
) -> list[tuple[str, int, int, str, str]]:
    """
    Search text with patterns whose scope is scope_filter or 'all'.
    Returns list of (pattern_id, line_1based, col_1based, matched_keyword_or_regex, description).
    """
    results = []
    for p in patterns:
        if p["scope"] not in (scope_filter, "all"):
            continue
        line_num = 0
        for line in text.splitlines():
            line_num += 1
            if p.get("keywords"):
                for kw in p["keywords"]:
                    pos = line.lower().find(kw.lower())
                    if pos >= 0:
                        results.append((p["id"] or kw, line_num, pos + 1, kw, p["description"]))
                        break
            if p.get("regex"):
                try:
                    m = re.search(p["regex"], line)
                    if m:
                        results.append((p["id"] or p["regex"], line_num, m.start() + 1, p["regex"], p["description"]))
                except re.error:
                    pass
    return results


def _resolved_under(base: Path, path: Path) -> bool:
    """True if path resolves to a location under base (symlink escape check)."""
    try:
        r_base = base.resolve()
        r_path = path.resolve()
        return r_path == r_base or r_base in r_path.parents
    except (OSError, RuntimeError):
        return False


def scan_skill_dir(skill_dir: Path, pattern_file_path: Path, patterns: list[dict]) -> tuple[list[dict], bool]:
    """
    Scan skill dir: body (skill_body/all), scripts/assets (scripts_and_assets/all).
    Returns (list of hit dicts with file, line, col, pattern_id, matched, description), non_english_flag.
    Symlink escape: only read files whose resolved path is under skill_dir. Skip files over MAX_FILE_SIZE_BYTES.
    """
    hits = []
    non_english = False
    skill_dir_resolved = skill_dir.resolve()

    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists() and _resolved_under(skill_dir_resolved, skill_md):
        try:
            stat = skill_md.stat()
            if stat.st_size > MAX_FILE_SIZE_BYTES:
                pass  # skip; do not treat as hit
            else:
                body = strip_frontmatter(skill_md.read_text(encoding="utf-8", errors="replace"))
                if has_substantial_foreign_language(body):
                    non_english = True
                for pid, line, col, matched, desc in find_matches_in_text(body, patterns, "skill_body"):
                    hits.append({
                        "file": str(skill_md),
                        "line": line,
                        "col": col,
                        "pattern_id": pid,
                        "matched": matched,
                        "description": desc,
                    })
        except Exception:
            pass

    for sub in ("scripts", "assets"):
        d = skill_dir / sub
        if not d.is_dir():
            continue
        for f in d.rglob("*"):
            if not f.is_file():
                continue
            if not _resolved_under(skill_dir_resolved, f):
                continue
            try:
                stat = f.stat()
                if stat.st_size > MAX_FILE_SIZE_BYTES:
                    continue
                text = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for pid, line, col, matched, desc in find_matches_in_text(text, patterns, "scripts_and_assets"):
                hits.append({
                    "file": str(f),
                    "line": line,
                    "col": col,
                    "pattern_id": pid,
                    "matched": matched,
                    "description": desc,
                })

    return hits, non_english


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Ensure pattern file; scan skill dir for content safety (references only).")
    ap.add_argument("skill_dir", type=Path, nargs="?", help="Path to skill directory (omit for ensure-only)")
    ap.add_argument("--scan-root", type=Path, default=None, help="Root path for resolving _localsetup/docs (default: parent of skill_dir or cwd)")
    ap.add_argument("--pattern-file", type=Path, default=None, help="Override path to SKILL_VALIDATION_PATTERNS.yaml")
    ap.add_argument("--no-fetch", action="store_true", help="Do not fetch pattern file if missing")
    ap.add_argument("--ensure-only", action="store_true", help="Only ensure pattern file exists and is fresh; exit 0 ok, 1 missing, 2 stale")
    args = ap.parse_args()

    try:
        _reject_null_byte(args.skill_dir, args.scan_root, args.pattern_file)
    except ValueError as e:
        print(f"VALIDATION_ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    try:
        if args.ensure_only:
            scan_root = args.scan_root.resolve() if args.scan_root else Path.cwd()
            pattern_path = resolve_pattern_file_path(args.pattern_file, scan_root)
            ok, msg = ensure_pattern_file(pattern_path, fetch_if_missing=not args.no_fetch)
            if not ok:
                if msg == "stale":
                    updated = ""
                    try:
                        data = yaml.safe_load(pattern_path.read_text(encoding="utf-8", errors="replace")) or {}
                        updated = data.get("updated", "")
                    except Exception:
                        pass
                    print("Skill validation pattern file is stale.", file=sys.stderr)
                    print(f"Last updated: {updated}. It may be outdated.", file=sys.stderr)
                    print("Options: (1) Pull latest from repo, (2) Do nothing, (3) Use existing file.", file=sys.stderr)
                    return 2
                print(f"Pattern file missing or failed: {msg}", file=sys.stderr)
                return 1
            return 0

        if not args.skill_dir:
            ap.error("skill_dir required unless --ensure-only")
        skill_dir = args.skill_dir.resolve()
        if not skill_dir.is_dir():
            print("VALIDATION_ERROR: not a directory", file=sys.stderr)
            return 1
        scan_root = args.scan_root.resolve() if args.scan_root else skill_dir.parent
        if not _skill_dir_under_scan_root(skill_dir, scan_root):
            print("VALIDATION_ERROR: skill_dir must be under scan_root", file=sys.stderr)
            return 1
        pattern_path = resolve_pattern_file_path(args.pattern_file, scan_root)
        ok, msg = ensure_pattern_file(pattern_path, fetch_if_missing=not args.no_fetch)
        if not ok:
            if msg == "stale":
                updated = ""
                try:
                    data = yaml.safe_load(pattern_path.read_text(encoding="utf-8", errors="replace")) or {}
                    updated = data.get("updated", "")
                except Exception:
                    pass
                print("Skill validation pattern file is stale.", file=sys.stderr)
                print(f"Last updated: {updated}. It may be outdated.", file=sys.stderr)
                print("Options: (1) Pull latest from repo, (2) Do nothing, (3) Use existing file.", file=sys.stderr)
                return 2
            print(f"Pattern file missing or failed: {msg}", file=sys.stderr)
            return 1

        patterns = load_patterns(pattern_path)
        hits, non_english = scan_skill_dir(skill_dir, pattern_path, patterns)

        # Output: references only; sanitize all printed fields
        if not hits and not non_english:
            print("Content safety: No concerns")
            return 0
        print("Content safety: REVIEW")
        if non_english:
            print("  Possible non-Latin language content (e.g. CJK, Cyrillic, Arabic). Manual review for hidden prompts.")
        for h in hits:
            fp = sanitize_for_output(h["file"])
            pid = sanitize_for_output(str(h["pattern_id"]))
            mat = sanitize_for_output(str(h["matched"]))
            desc = sanitize_for_output(h["description"] or "")
            print(f"  file:{fp} line:{h['line']} col:{h['col']} pattern:{pid} matched:{mat!r} description:{desc}")
        return 0
    except Exception as e:
        err_msg = str(e)
        if len(err_msg) > 200:
            err_msg = err_msg[:197] + "..."
        print(f"VALIDATION_ERROR: {type(e).__name__}: {err_msg}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
