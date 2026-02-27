---
status: ACTIVE
version: 2.8
---

# Tooling policy

Purpose: define project-wide tooling language and dependency rules.

## Core rule

- Python is the primary and only language for framework tooling after installation.
- Shell and PowerShell are limited to bootstrap and platform entrypoints:
  - install bootstrap (`install`, `install.ps1`)
  - minimal wrappers/delegation for host compatibility
  - environment orchestration outside framework runtime

## Python runtime target

- Minimum supported version: Python 3.10.
- Baseline rationale: Ubuntu 22.04 LTS default runtime and forward compatibility on newer LTS versions.

## Dependency policy

- Keep third-party libraries minimal.
- Add dependency only when it materially reduces complexity, risk, or maintenance cost.
- Prefer mature libraries with:
  - active maintenance
  - broad adoption
  - clear license
  - recent release activity
- Pin lower bounds in `requirements.txt` and document why each dependency exists.

## Approved libraries (mandatory use)

These libraries are pre-approved, listed in `requirements.txt`, and available after any framework install. When writing new tools or refactoring existing ones, **use these libraries** instead of reimplementing their functionality. Reinventing them (custom HTTP clients, bespoke YAML parsers, ad-hoc frontmatter splits) is explicitly prohibited when one of these covers the need.

| Library | Import name | pip package | Use for |
|---------|-------------|-------------|---------|
| PyYAML | `yaml` | `PyYAML>=6.0` | All YAML parsing and serialization. Never use `json` as a workaround or parse YAML by hand. |
| requests | `requests` | `requests>=2.28` | All outbound HTTP. Use `requests.Session` for multi-request tools. Never use `urllib.request` for new code. |
| python-frontmatter | `frontmatter` | `python-frontmatter>=1.1` | Parse YAML front matter from skill and PRD markdown files. Never split frontmatter by hand. |

**Shared dependency helper:** Import `lib.deps` at the top of every tool and call `require_deps()` before using any approved library. This gives users an actionable error message instead of a bare `ImportError` if the library is missing.

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from deps import require_deps
require_deps(["requests", "frontmatter"])  # list only the ones this tool uses
```

The `require_deps()` call always does a live `importlib` check. It never reads the `.deps-missing` sentinel file written by the install script, so a stale sentinel from an older install cannot block tools on a system where the packages are present.

**For AI agents:** When generating or refactoring framework Python tooling, check whether the task involves HTTP requests, YAML parsing, or frontmatter parsing. If yes, use the approved library from the table above. Do not generate custom implementations of these.

## Lint and quality

- Python tooling must be lint-clean before merge. Single source of truth for commands and expectations:
  - **Linter:** Run `ruff check` (or project-configured equivalent) from repo root or script directory. Fix all reported issues or document an explicit exception.
  - **Format:** Run `ruff format` for style; no trailing whitespace, consistent quotes.
  - **Types:** Use type hints for public functions and module boundaries. Use `pyright` or `mypy` in strict or standard mode if the project enables it; resolve type errors or add targeted ignores with a short comment.
  - **Best practice:** Prefer explicit error handling and small functions; avoid broad `except` and untyped `**kwargs` in public APIs. See [INPUT_HARDENING_STANDARD.md](INPUT_HARDENING_STANDARD.md) for input handling; this section covers static checks and style only.
- Audit and CI scripts may read this section to determine which commands to run for tooling/lint.

## Markdown output (reports and tool output)

All framework tooling that produces reports or structured output intended for human or agent consumption **must** emit markdown that is **GitHub Flavored Markdown (GFM) compatible**. This ensures output renders correctly in GitHub, in editor previews, and in any GFM-capable viewer. Apply these rules globally to every script or tool that writes a report, log summary, or formatted output to a file or stdout.

**Required:**

- **Sectioning:** Use heading levels to separate parts of the report. Use `#` for the document title, `##` for major sections, `###` for subsections, `####` for sub-subsections. Do not skip levels (e.g. do not go from `##` to `####`).
- **Code blocks:** Use fenced code blocks for any program or terminal output, log snippets, or code. Prefer `~~~text` / `~~~` (or ` ```text ` / ` ``` `) so that output containing backticks does not break the fence. Add a language hint when useful (e.g. `~~~text` for terminal output, `~~~python` for code). Do not rely on indented-only code blocks; use explicit fences.
- **Emphasis:** Use **bold** for labels and important terms (e.g. **stdout**, **Errors**, **Summary**). Use *italic* for secondary emphasis or "(no output)"-style notes where appropriate.
- **Lists:** Use `-` or `*` for unordered lists and `1.` for ordered lists so they render as proper list structure.
- **Tables:** Use GFM table syntax (`| col | col |` with a header separator row) when presenting tabular data so it renders in a readable table.

**Recommended:**

- Use horizontal rules (`---`) sparingly to separate major report sections if it improves scanability.
- Use inline `code` for file paths, command names, and literal values so they stand out.
- Keep line length and paragraph length reasonable so that diff and preview UIs remain readable.

**Avoid:**

- Raw triple backticks inside content that is inside a fenced block (use a different fence, e.g. `~~~`, for the outer block so inner backticks do not close it).
- Non-GFM or non–CommonMark markdown that GitHub does not render (e.g. custom HTML for layout; prefer standard markdown).
- Unstructured walls of text; break content into sections and use the formatting above so importance and hierarchy are visually clear.

Scripts and skills that generate reports (e.g. [framework audit](WORKFLOW_REGISTRY.md) including optional Deep Analysis, PR review, validation summaries) must follow this section. New tooling must adopt it by default.

## External input rule

- All Python tooling that consumes external input must follow:
  - hostile-by-default handling
  - input sanitization
  - schema and bounds validation
  - actionable STDERR error output
  - no silent failure
- See [INPUT_HARDENING_STANDARD.md](INPUT_HARDENING_STANDARD.md) for mandatory controls.

## Migration direction

- New tooling and significant refactors should be implemented in Python.
- Existing shell/PowerShell tooling may remain temporarily where needed for bootstrap and compatibility, but should not expand in scope.
