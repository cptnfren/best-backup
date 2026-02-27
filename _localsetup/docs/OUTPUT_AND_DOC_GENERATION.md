---
status: ACTIVE
version: 2.8
last_updated: "2026-02-20"
---

# Output and doc generation (platform default)

**Purpose:** Default behavior for all generated content (reports, context, user-facing docs, tool output). Applies to framework tooling and to agent-produced markdown. Every user of the platform gets rich, readable output by default.

## Default behavior for any generated docs or output

When the framework or an agent generates markdown, reports, or documentation (for any project, not only this repo):

- **Code and copy-paste:** Use fenced code blocks for commands, snippets, and terminal output. Use a language hint when useful (`bash`, `python`, `text`). Make sections that are meant to be copied clearly scannable (e.g. a short heading like "Run this" or "Copy-paste").
- **Lists:** Use `-` or `*` for unordered lists and `1.` for ordered lists so structure is clear. Break long prose into bullets where it helps.
- **Typography:** Use heading levels for sections, **bold** for labels and important terms, *italic* for secondary emphasis, and inline `code` for paths, commands, and literals.
- **Links:** In-repo references to docs or config (e.g. other `.md` files, `.yaml` indexes) should be markdown links, not bare paths, so they work in GitHub and previews.
- **Glyphs and icons:** Use symbols or icons where they improve scanability (e.g. [OK], [FAIL], checkmarks, bullets). Prefer glyphs that render in common editors and GFM. Avoid relying on glyphs for critical meaning when plain text is clearer.
- **Humanized prose:** Default to natural, specific language. Avoid template-y or inflated phrasing; vary sentence length; be concrete. Use the humanizer skill when refining existing text.

Tooling that writes reports or output (audit, PR review, validation summaries, generated context) must follow this by default. See [TOOLING_POLICY.md](TOOLING_POLICY.md) (Markdown output) for GFM compatibility and script output rules.

## Scope

This is the **platform** default. It applies to any content the framework or its agents produce, in any repo. Repo-specific maintenance checklists (e.g. link verification for a single codebase) stay in that repo and are not part of the shipped framework.
