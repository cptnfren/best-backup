---
status: ACTIVE
version: 2.8
---

# Skill validation pattern file

**Purpose:** Heuristic patterns used when scanning skills for potentially harmful content (e.g. prompt injection, exfiltration, dangerous code). The pattern file is updatable without pulling the whole repo. Results are advisory; user review is required. No auto-block.

## Location and how to get latest

- **Default path (client repo):** `_localsetup/docs/SKILL_VALIDATION_PATTERNS.yaml`
- **From framework source:** `_localsetup/docs/SKILL_VALIDATION_PATTERNS.yaml`
- **Canonical GitHub raw URL (for fetch):**  
  `https://raw.githubusercontent.com/cptnfren/localsetup/main/_localsetup/docs/SKILL_VALIDATION_PATTERNS.yaml`

If the file is missing, the scan tool fetches it from the URL above and writes it locally. If the file is older than 7 days, the tool reports that it may be outdated and offers three options: **(1) Pull latest from repo**, **(2) Do nothing**, **(3) Use existing file**. Choosing "Pull latest" overwrites the local file with the one from the URL. If you have customized the file, back it up first; "Pull latest" replaces your copy.

## Schema (summary)

- **Top-level:** `updated` (ISO8601), `version` (optional), `sources` (optional).
- **Pattern sets:** e.g. `prompt_injection`, `exfiltration`, `code_execution`, `scripts_and_assets`, `crypto_mining`.
- **Per-pattern:**  
  - `id` (optional), `description` (required; see below), `scope`: `skill_body` | `scripts_and_assets` | `all`.  
  - Either `keywords` (list of strings) or `regex` (string).  
  - Optional `severity` or `category`.

**Description field:** Up to a short paragraph, specific to the pattern. It should explain what the pattern could mean if it appears in a skill or is read by an AI. Use plain language for readers not deeply familiar with AI; avoid heavy jargon. This text is shown to the user when a hit occurs so they can make an informed decision.

## Content safety and Security sections

The scan tool outputs two kinds of checks:

- **Security: REVIEW (heuristic flags)**  - Existing code-focused checks (e.g. `eval(`, `curl | sh`) in scripts and assets. Lists file and line.
- **Content safety: REVIEW**  - New checks: (1) Pattern file matches in SKILL.md body and/or scripts/assets; (2) Possible hidden prompt in a foreign language: the scanner flags only **substantial runs** of non-Latin natural-language script (e.g. CJK, Cyrillic, Arabic, Hebrew, Thai, Devanagari, Hiragana/Katakana, Hangul) in the SKILL.md body. Extended Latin (accents, n-tilde, etc.), box-drawing, symbols, and ASCII are **not** flagged. The [Agent Skills specification](https://agentskills.io/specification) is the baseline (no body format restrictions); we only trigger manual review when the content looks like actual text in another script that could be a hidden prompt, not because of character encoding or extended character set. For pattern hits, the tool outputs **references only** (file, line, column, pattern id, and the pattern’s description from the YAML). For safety, the tool does not read or display the actual content at those positions; the user opens the file at the given line/column and reviews it themselves.

When "Content safety: REVIEW" appears, the agent should state that for safety reasons the content at those locations is not being read or displayed, and ask the user to open the file at the indicated position(s) and review. Then offer: (1) Do not import / skip this skill, (2) I have reviewed the file; proceed with import, (3) I will ignore and continue anyway.

## Custom patterns

You can edit the YAML file to add or change patterns. "Pull latest" from the repo overwrites your file. To keep customizations, back up the file or use a different path (future enhancement: configurable pattern file path).

## Adding patterns and false positives

Keywords and regexes are intentionally conservative. The goal is to widen the net and prompt manual review, not to block all risk. Prefer phrases over single words where possible. For `skill_body`, use patterns that are clearly dangerous in natural language (e.g. "ignore previous instructions", "send .env"). For `scripts_and_assets`, use patterns unlikely in legitimate code (e.g. `base64 -d ... | sh`, `/etc/shadow`). Document in the YAML or here that the list is heuristic and user review is required.

## Validation script hardening

The validation scripts (Python and Bash/PowerShell wrappers) are hardened for untrusted input. Paths are validated (no null byte; skill_dir must be under scan_root); symlinks that point outside the skill directory are not read. Pattern matching is performed on **raw file content** only; the matched text is never sanitized before scanning, so skills cannot evade detection by adding characters that would be stripped. Only the **output** (file path, line, column, pattern id, description) is sanitized for display so control characters cannot break parsing or inject into the LLM. On any exception, the script prints `VALIDATION_ERROR: <type>: <message>` to stderr and exits with code 1 so the workflow can treat it as failed validation.

## Reference

- OWASP LLM prompt injection guidance.  
- pr1m8/prompt-injections taxonomy and dataset.  
- [SKILL_IMPORTING.md](SKILL_IMPORTING.md) for the full import workflow and when content safety is shown.

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>
