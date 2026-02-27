#!/usr/bin/env python3
# Purpose: Automated GitHub PR code review (check, review, post, status, list-unreviewed). Replaces pr-review.sh.
# Created: 2026-02-20
# Last updated: 2026-02-20

"""
PR review CLI. Requires gh CLI. Uses PR_REVIEW_REPO, PR_REVIEW_DIR, PR_REVIEW_STATE, PR_REVIEW_OUTDIR.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

PATH_MAX = 4096
PR_NUM_MAX = 10
REPO_MAX = 256

# Pattern lists: (regex, category, message)
SECRET_PATTERNS = [
    (r"(?i)(password|passwd|secret|api[_-]?key|token|auth)\s*[:=]\s*[\"'][^\"']{8,}[\"']", "SECURITY", "Possible hardcoded credential/secret"),
    (r"(?i)AWS[_A-Z]*KEY\s*[:=]", "SECURITY", "Possible hardcoded AWS key"),
    (r"(?i)-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY", "SECURITY", "Private key in source code"),
]
GO_PATTERNS = [
    (r"^\+.*,\s*_\s*:?=.*\(", "ERROR_HANDLING", "Discarded error return value (Go)"),
    (r"^\+.*\.Close\(\)\s*$", "ERROR_HANDLING", "Unchecked Close()"),
    (r"^\+.*panic\(", "RISK", "Direct panic() call"),
    (r"^\+.*fmt\.Print", "STYLE", "fmt.Print in production code"),
    (r"^\+.*os\.Exit\(", "RISK", "Direct os.Exit()"),
]
PYTHON_PATTERNS = [
    (r"^\+.*except\s*:", "ERROR_HANDLING", "Bare except clause"),
    (r"^\+.*except Exception:", "ERROR_HANDLING", "Broad except Exception"),
    (r"^\+.*print\(", "STYLE", "print() in production code"),
    (r"^\+.*# type: ignore", "TYPING", "Type ignore comment"),
]
JS_PATTERNS = [
    (r"^\+.*console\.log\(", "STYLE", "console.log in production code"),
    (r"^\+.*debugger", "STYLE", "Debugger statement"),
    (r"^\+.*process\.exit\(", "RISK", "Direct process.exit()"),
    (r"^\+.*eval\(", "SECURITY", "eval() usage"),
    (r"^\+.*\bany\b", "TYPING", "TypeScript any type"),
]
GENERAL_PATTERNS = [
    (r"^\+.*TODO", "TODO", "TODO marker"),
    (r"^\+.*FIXME", "TODO", "FIXME marker"),
    (r"^\+.*HACK", "TODO", "HACK marker"),
    (r"^\+.*XXX", "TODO", "XXX marker"),
    (r"^\+.{200,}", "STYLE", "Very long line (>200 chars)"),
]

CAT_ICONS = {"SECURITY": "[FAIL]", "ERROR_HANDLING": "[WARNING]", "RISK": "[WARNING]", "STYLE": "[NOTE]", "TODO": "[NOTE]", "TYPING": "[NOTE]"}


def _sanitize(s: str, max_len: int, name: str) -> str:
    if not isinstance(s, str):
        raise ValueError(f"{name}: expected string")
    s = " ".join(s.split()).strip()
    if len(s) > max_len:
        raise ValueError(f"{name}: length exceeds {max_len}")
    return s


def _log(msg: str) -> None:
    print(f"[pr-review] {msg}", file=sys.stderr)


def _gh(repo: str, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    cmd = ["gh"] + list(args) + ["--repo", repo]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        input=stdin,
    )


def get_repo_and_dirs() -> tuple[str, Path | None, Path, Path]:
    repo = os.environ.get("PR_REVIEW_REPO", "").strip()
    if not repo:
        r = _gh(".", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner")
        if r.returncode == 0 and r.stdout:
            repo = r.stdout.strip()
        if not repo:
            print("Error: Could not detect repo. Set PR_REVIEW_REPO=owner/repo", file=sys.stderr)
            sys.exit(1)
    if len(repo) > REPO_MAX:
        print("Error: PR_REVIEW_REPO too long", file=sys.stderr)
        sys.exit(2)
    local_dir = os.environ.get("PR_REVIEW_DIR", "").strip()
    local_path = Path(local_dir).resolve() if local_dir else None
    if local_dir and (not local_path.exists() or not local_path.is_dir()):
        local_path = None
    if not local_path:
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout:
            local_path = Path(r.stdout.strip()).resolve()
    state_path = Path(os.environ.get("PR_REVIEW_STATE", "./data/pr-reviews.json")).resolve()
    outdir = Path(os.environ.get("PR_REVIEW_OUTDIR", "./data/pr-reviews")).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    if not state_path.exists():
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text("{}", encoding="utf-8")
    return repo, local_path, state_path, outdir


def get_open_prs(repo: str) -> list[dict]:
    r = _gh(repo, "pr", "list", "--state", "open", "--json",
            "number,title,author,createdAt,headRefName,additions,deletions,changedFiles,labels,baseRefName,headRefOid")
    if r.returncode != 0:
        return []
    try:
        return json.loads(r.stdout or "[]")
    except json.JSONDecodeError:
        return []


def get_pr_diff(repo: str, pr_num: int) -> str:
    r = _gh(repo, "pr", "diff", str(pr_num))
    return r.stdout or "" if r.returncode == 0 else ""


def get_pr_files(repo: str, pr_num: int) -> list[str]:
    r = _gh(repo, "pr", "view", str(pr_num), "--json", "files", "-q", ".files[].path")
    if r.returncode != 0:
        return []
    return [f.strip() for f in (r.stdout or "").splitlines() if f.strip()]


def get_pr_commits(repo: str, pr_num: int) -> str:
    r = _gh(repo, "pr", "view", str(pr_num), "--json", "commits")
    if r.returncode != 0:
        return ""
    try:
        data = json.loads(r.stdout or "{}")
        commits = data.get("commits", [])
        return "\n".join(f"{c.get('oid', '')[:8]} {c.get('messageHeadline', '')}" for c in commits)
    except (json.JSONDecodeError, TypeError):
        return ""


def get_pr_view(repo: str, pr_num: int) -> dict | None:
    r = _gh(repo, "pr", "view", str(pr_num), "--json",
            "title,author,headRefName,headRefOid,baseRefName,additions,deletions,body,createdAt,labels")
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        return None


def load_state(state_path: Path) -> dict:
    try:
        return json.loads(state_path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}


def save_state(state_path: Path, state: dict) -> None:
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8", errors="replace")


def is_reviewed(repo: str, pr_num: int, state_path: Path) -> bool:
    head_r = _gh(repo, "pr", "view", str(pr_num), "--json", "headRefOid", "-q", ".headRefOid")
    head_sha = (head_r.stdout or "").strip() if head_r.returncode == 0 else ""
    state = load_state(state_path)
    pr = state.get(str(pr_num), {})
    return pr.get("head_sha") == head_sha and pr.get("status") == "reviewed"


def categorize_files(files: list[str]) -> dict[str, list[str]]:
    from collections import defaultdict
    cats = defaultdict(list)
    for f in files:
        if not f:
            continue
        ext = f.rsplit(".", 1)[-1] if "." in f else ""
        if ext == "go":
            cats["go"].append(f)
        elif ext == "py":
            cats["python"].append(f)
        elif ext in ("ts", "tsx", "js", "jsx"):
            cats["frontend"].append(f)
        elif ext in ("yml", "yaml", "toml", "json", "env"):
            cats["config"].append(f)
        elif ext in ("md", "txt", "rst"):
            cats["docs"].append(f)
        elif ext == "sql":
            cats["sql"].append(f)
        elif "Dockerfile" in f or f == "docker-compose.yml":
            cats["docker"].append(f)
        elif f.startswith(".github/"):
            cats["ci"].append(f)
        else:
            cats["other"].append(f)
    return dict(cats)


def analyze_diff(diff_text: str) -> list[dict]:
    findings = []
    current_file = None
    line_num = 0
    for line in diff_text.split("\n"):
        m = re.match(r"^\+\+\+ b/(.*)", line)
        if m:
            current_file = m.group(1)
            continue
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)", line)
        if m:
            line_num = int(m.group(1))
            continue
        if line.startswith("+") and not line.startswith("+++"):
            line_num += 1
            all_p = SECRET_PATTERNS + GENERAL_PATTERNS
            if current_file:
                if current_file.endswith(".go"):
                    all_p = all_p + GO_PATTERNS
                elif current_file.endswith(".py"):
                    all_p = all_p + PYTHON_PATTERNS
                elif current_file.endswith((".js", ".jsx", ".ts", ".tsx")):
                    all_p = all_p + JS_PATTERNS
            for pat, cat, msg in all_p:
                if re.search(pat, line):
                    findings.append({
                        "file": current_file or "unknown",
                        "line": line_num,
                        "category": cat,
                        "message": msg,
                        "context": (line[1:].strip())[:120],
                    })
        elif not line.startswith("-"):
            line_num += 1
    return findings


def check_test_coverage(files: list[str]) -> str:
    src, tests = [], []
    for f in files:
        f = f.strip()
        if not f:
            continue
        name = f.split("/")[-1]
        if f.endswith("_test.go") or name.startswith("test_") or f.endswith("_test.py") or ".test." in f or ".spec." in f:
            tests.append(f)
        elif f.endswith((".go", ".py", ".ts", ".tsx", ".js", ".jsx")):
            src.append(f)
    missing = []
    for s in src:
        has_test = False
        s_dir = "/".join(s.split("/")[:-1])
        s_name = s.split("/")[-1].rsplit(".", 1)[0]
        for t in tests:
            t_dir = "/".join(t.split("/")[:-1])
            if t_dir == s_dir or f"test_{s_name}" in t or f"{s_name}_test" in t or f"{s_name}.test" in t or f"{s_name}.spec" in t:
                has_test = True
                break
        skip = any(k in s for k in ["__init__", "main.go", "main.py", "config", "types", "models", "schema", "index.ts", "index.js"])
        if not has_test and not skip:
            missing.append(s)
    if missing:
        return "Files without corresponding test changes:\n" + "\n".join(f"  - {f}" for f in missing)
    return "Test coverage looks adequate for changed files."


def run_local_lint(files: list[str], local_dir: Path | None) -> str:
    if not local_dir or not local_dir.is_dir():
        return ""
    out_parts = []
    go_files = [f for f in files if f.endswith(".go")]
    if go_files and _which("golangci-lint"):
        dirs = sorted(set("/".join(f.split("/")[:-1]) for f in go_files))
        for d in dirs:
            full = local_dir / d
            if full.is_dir():
                r = subprocess.run(
                    ["golangci-lint", "run", "--timeout", "2m", "--new-from-rev=HEAD~1"],
                    cwd=str(full),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if r.stdout or r.stderr:
                    out_parts.append(f"### golangci-lint ({d})\n```\n{r.stdout or r.stderr}\n```")
    py_files = [f for f in files if f.endswith(".py")]
    if py_files and _which("ruff"):
        paths = [str(local_dir / f) for f in py_files]
        r = subprocess.run(["ruff", "check"] + paths, capture_output=True, text=True, timeout=60, cwd=str(local_dir))
        if r.returncode != 0 and r.stdout and "All checks passed" not in r.stdout:
            out_parts.append("### ruff\n```\n" + (r.stdout or r.stderr or "") + "\n```")
    return "\n\n".join(out_parts) if out_parts else ""


def _which(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def generate_report(repo: str, pr_num: int, state_path: Path, outdir: Path, local_dir: Path | None, force: bool) -> Path | None:
    if not force and is_reviewed(repo, pr_num, state_path):
        _log(f"PR #{pr_num} already reviewed at current HEAD. Use 'review' to force.")
        return None
    _log(f"Reviewing PR #{pr_num}...")
    view = get_pr_view(repo, pr_num)
    if not view:
        print(f"Error: Could not load PR #{pr_num}", file=sys.stderr)
        return None
    title = view.get("title", "")
    author = (view.get("author") or {}).get("login", "")
    branch = view.get("headRefName", "")
    head_sha = view.get("headRefOid", "")[:8]
    additions = view.get("additions", 0)
    deletions = view.get("deletions", 0)
    body = view.get("body") or "_No description provided._"
    created = view.get("createdAt", "")
    files = get_pr_files(repo, pr_num)
    diff = get_pr_diff(repo, pr_num)
    commits = get_pr_commits(repo, pr_num)
    categories = categorize_files(files)
    findings = analyze_diff(diff)
    test_cov = check_test_coverage(files)
    lint_results = run_local_lint(files, local_dir)

    from collections import Counter
    counts = Counter(f["category"] for f in findings)
    findings_summary_lines = []
    for cat, count in sorted(counts.items()):
        icon = CAT_ICONS.get(cat, "[NOTE]")
        findings_summary_lines.append(f"{icon} {cat}: {count}")
    findings_summary = "\n".join(findings_summary_lines) if findings_summary_lines else "[OK] No issues found in diff analysis"

    cat_icons = {"go": "[GO]", "python": "[PY]", "frontend": "[FE]", "ci": "[CI]", "config": "[CFG]", "docs": "[DOC]", "docker": "[DOCKER]", "sql": "[SQL]", "other": "[OTHER]"}
    changed_files_md = []
    for cat, flist in sorted(categories.items()):
        changed_files_md.append(f"### {cat_icons.get(cat, '[F]')} {cat.title()} ({len(flist)} files)")
        for f in flist:
            changed_files_md.append(f"- `{f}`")
        changed_files_md.append("")
    changed_files_md = "\n".join(changed_files_md)

    findings_table = ""
    if findings:
        findings_table = "| File | Line | Category | Finding | Context |\n|------|------|----------|---------|--------|\n"
        for f in findings[:50]:
            ctx = (f["context"] or "").replace("|", "\\|")[:60]
            short_file = f["file"].split("/")[-1]
            findings_table += f"| `{short_file}` | {f['line']} | {f['category']} | {f['message']} | `{ctx}` |\n"

    sec = [x for x in findings if x["category"] == "SECURITY"]
    err = [x for x in findings if x["category"] in ("ERROR_HANDLING", "RISK")]
    sty = [x for x in findings if x["category"] in ("STYLE", "TODO", "TYPING")]
    if sec:
        summary_verdict = "[FAIL] **SECURITY CONCERNS** — Review security findings before merging."
    elif err:
        summary_verdict = "[WARNING] **NEEDS ATTENTION** — Error handling / risk items to review."
    elif sty:
        summary_verdict = "[NOTE] **MINOR STYLE NOTES** — Looks good overall, minor suggestions above."
    else:
        summary_verdict = "[OK] **LOOKS GOOD** — No automated issues found. Ready for human review."

    report = f"""# PR #{pr_num} Review: {title}

**Author:** {author}
**Branch:** `{branch}`
**HEAD:** `{head_sha}`
**Created:** {created}
**Changes:** +{additions} / -{deletions}
**Reviewed:** {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}

## Description

{body}

## Commits

```
{commits}
```

## Changed Files

{changed_files_md}

## Automated Analysis

### Diff Findings

{findings_summary}

{findings_table}

### Test Coverage

{test_cov}

"""
    if lint_results:
        report += "### Local Lint Results\n\n" + lint_results + "\n\n"
    else:
        report += "### Local Lint\n\n_Skipped (repo not checked out locally or linters not found)._\n\n"
    report += f"## Summary\n\n{summary_verdict}\n\n---\n_Automated PR review • {time.strftime('%Y-%m-%d %H:%M')}_\n"

    report_file = outdir / f"{pr_num}.md"
    report_file.write_text(report, encoding="utf-8", errors="replace")
    state = load_state(state_path)
    state[str(pr_num)] = {
        "head_sha": view.get("headRefOid", ""),
        "status": "reviewed",
        "reviewed_at": int(time.time()),
        "report": str(report_file),
    }
    save_state(state_path, state)
    _log(f"Report saved to {report_file}")
    return report_file


def cmd_check(repo: str, state_path: Path, outdir: Path, local_dir: Path | None) -> int:
    prs = get_open_prs(repo)
    if not prs:
        _log("No open PRs.")
        print('{"reviewed": 0, "skipped": 0, "total": 0}')
        return 0
    reviewed = 0
    skipped = 0
    for pr in prs:
        num = pr["number"]
        if is_reviewed(repo, num, state_path):
            skipped += 1
            _log(f"PR #{num}: already reviewed, skipping.")
        else:
            generate_report(repo, num, state_path, outdir, local_dir, False)
            reviewed += 1
    print(json.dumps({"reviewed": reviewed, "skipped": skipped, "total": len(prs)}))
    return 0


def cmd_review(repo: str, pr_num: int, state_path: Path, outdir: Path, local_dir: Path | None) -> int:
    if pr_num < 1 or pr_num > 999999:
        print("Error: Invalid PR number", file=sys.stderr)
        return 2
    generate_report(repo, pr_num, state_path, outdir, local_dir, True)
    return 0


def cmd_post(repo: str, pr_num: int, outdir: Path) -> int:
    report_file = outdir / f"{pr_num}.md"
    if not report_file.is_file():
        _log(f"No review report for PR #{pr_num}. Run 'review {pr_num}' first.")
        return 1
    r = _gh(repo, "pr", "comment", str(pr_num), "--body-file", str(report_file))
    if r.returncode != 0:
        print(r.stderr or r.stdout or "gh pr comment failed", file=sys.stderr)
        return 1
    _log(f"Review posted to PR #{pr_num}")
    return 0


def cmd_status(repo: str, state_path: Path) -> int:
    prs = get_open_prs(repo)
    state = load_state(state_path)
    if not prs:
        print("No open PRs.")
        return 0
    print(f"Open PRs: {len(prs)}\n")
    for pr in prs:
        num = str(pr["number"])
        s = state.get(num, {})
        status = s.get("status", "unreviewed")
        icon = "[OK]" if status == "reviewed" else "[PENDING]"
        print(f"{icon} PR #{num}: {pr['title']} ({pr['author']['login']})")
        print(f"   +{pr['additions']}/-{pr['deletions']} | {pr['headRefName']}")
        if s:
            age = int(time.time()) - s.get("reviewed_at", 0)
            print(f"   Reviewed {age // 3600}h ago | SHA: {(s.get('head_sha') or '?')[:8]}")
        print()
    return 0


def cmd_list_unreviewed(repo: str, state_path: Path) -> int:
    prs = get_open_prs(repo)
    for pr in prs:
        num = pr["number"]
        if not is_reviewed(repo, num, state_path):
            print(num)
    return 0


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1].strip().lower() in ("--help", "-h"):
        print("Usage: pr_review.py {check|review <PR#>|post <PR#>|status|list-unreviewed}", file=sys.stderr)
        print("Environment: PR_REVIEW_REPO, PR_REVIEW_DIR, PR_REVIEW_STATE, PR_REVIEW_OUTDIR", file=sys.stderr)
        return 0 if (len(sys.argv) >= 2 and sys.argv[1].strip().lower() in ("--help", "-h")) else 1
    sub = sys.argv[1].strip().lower()
    try:
        repo, local_dir, state_path, outdir = get_repo_and_dirs()
    except SystemExit:
        raise
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    if sub == "check":
        return cmd_check(repo, state_path, outdir, local_dir)
    if sub == "review":
        if len(sys.argv) < 3:
            print("Error: PR number required", file=sys.stderr)
            return 2
        try:
            pr_num = int(sys.argv[2])
        except ValueError:
            print("Error: PR number must be an integer", file=sys.stderr)
            return 2
        return cmd_review(repo, pr_num, state_path, outdir, local_dir)
    if sub == "post":
        if len(sys.argv) < 3:
            print("Error: PR number required", file=sys.stderr)
            return 2
        try:
            pr_num = int(sys.argv[2])
        except ValueError:
            print("Error: PR number must be an integer", file=sys.stderr)
            return 2
        return cmd_post(repo, pr_num, outdir)
    if sub == "status":
        return cmd_status(repo, state_path)
    if sub == "list-unreviewed":
        return cmd_list_unreviewed(repo, state_path)
    print("Usage: pr_review.py {check|review <PR#>|post <PR#>|status|list-unreviewed}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
