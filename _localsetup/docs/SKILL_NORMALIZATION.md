---
status: ACTIVE
version: 2.8
---

# Skill normalization (spec compliance and platform-neutral)

**Purpose:** When importing skills or normalizing skills already in the tree, apply this doc so each skill is (1) compliant with the [Agent Skills specification](https://agentskills.io/specification), (2) document-normalized with a **user choice** when the skill is platform-specific (keep as is, keep platform-specific but normalized, or fully normalize for any platform), and (3) **tooling-normalized** so any bundled scripts match the framework's tooling standard. Normalization runs in order: **Phase 1 (SKILL.md and documents)**, then **Phase 2 (tooling)**. We do not force full platform-neutralization when the user works with one platform exclusively; Phase 1 offers options when the skill references a specific platform. The skill-importer and the standalone normalizer (localsetup-skill-normalizer) both use this doc as the single source of truth.

## When normalization runs

- **During import:** Normalization is **mandatory**. After security and content-safety are verified and the user has selected skills and duplicate/overlap is resolved, run Phase 1 (documents) and Phase 2 (tooling) per the flows below. Phase 1 offers a choice when the skill is platform-specific; we do not force full platform-neutralization when the user prefers to keep platform-specific content.
- **After the fact:** The standalone normalizer skill can run on any skill(s) already in the tree. Same rules and approval flow.

## Phase 1: Document normalization and platform handling

**Default (skill not platform-specific):** If the skill does not reference a specific platform or context (e.g. no "OpenClaw", "Cursor", product-named sections, or platform-specific metadata), apply the **spec-compliance checklist** and **platform-neutralization rules** below automatically. Produce a summary and key edits, get approval, then write the normalized SKILL.md. Then proceed to Phase 2 (tooling).

**When the skill is platform-specific:** If the skill references a specific platform or context (e.g. OpenClaw, a named agent product, platform-specific metadata or sections), **offer the user a choice**. Do not assume full normalization is desired; the user may work exclusively with that platform and have no need to generalize. Present the three options:

1. **Keep as is**  - No document changes for platform wording or structure. The skill stays exactly as written (e.g. "this skill references OpenClaw"). Only ensure frontmatter `name` matches the skill directory and `metadata.version` is present if missing; no platform-neutralization. Then proceed to Phase 2 (tooling). Use when the user wants the skill to remain tied to that platform with no edits.
2. **Keep platform-specific but normalized**  - Apply spec compliance and standardize to the skill-specific application: fix frontmatter (name, description length, metadata.version, optional compatibility), consistent heading and list style, and any structural cleanup, but **do not** remove or generalize platform references. Platform names, "Integration with X", and platform-specific examples stay; only wording is standardized and spec-compliant. Then proceed to Phase 2. Use when the user wants the skill to stay for that platform but in a consistent, spec-compliant form.
3. **Fully normalize**  - Apply the full spec-compliance checklist and platform-neutralization rules (generic snippets, remove platform-specific sections, generalize description and examples so the skill is adaptable for any platform). Then proceed to Phase 2. Use when the user wants the skill to be platform-agnostic.

Depending on the user's choice, perform only the corresponding action; then **Phase 2 (tooling) runs as normal**, with the user presented with tooling options (rewrite to framework standard vs keep original tooling) if the skill has scripts. Emphasis: we do not force one-size-fits-all; if they work with one platform exclusively, keeping the skill platform-specific may be the right choice.

## Spec-compliance checklist (frontmatter)

Apply these checks and fixes so SKILL.md frontmatter satisfies the Agent Skills spec:

1. **name** (required)
   - Must be 1–64 characters.
   - Only lowercase letters (a–z), numbers, and hyphens.
   - Must not start or end with a hyphen; no consecutive hyphens (`--`).
   - Must match the parent directory name (e.g. `localsetup-ansible-skill` for `_localsetup/skills/localsetup-ansible-skill/`).
   - If the skill is imported with a different dir name (e.g. `localsetup-<name>`), set `name` in frontmatter to that directory name.

2. **description** (required)
   - Must be 1–1024 characters, non-empty.
   - Should describe what the skill does and when to use it; include keywords that help agents match the task.
   - Remove or generalize platform-specific phrasing (e.g. "OpenClaw VPS setup" → "VPS setup (including optional agent-host examples)" or similar).

3. **compatibility** (optional)
   - Use for runtime or environment requirements (e.g. required binaries, system packages, network).
   - Max 500 characters if provided.
   - If the skill has platform-specific metadata (e.g. `metadata.openclaw` with `requires`/`install`), convert that into a generic `compatibility` string and remove the platform-specific block (see before/after below).

4. **metadata** (optional)
   - Keep `metadata.version` (e.g. `"1.0"`) so the framework versioning hook can bump it.
   - Remove or convert platform-only keys (e.g. `metadata.openclaw`) into `compatibility` or a short note in the body; do not leave product-specific metadata as the only record of requirements.

5. **license** (optional)
   - Leave as-is if present; no change required for normalization.

## Before/after frontmatter examples

### Platform-specific metadata → compatibility

**Before:**

```yaml
---
name: some-skill
description: "Does X. Use with OpenClaw."
metadata:
  version: "1.0"
  openclaw:
    requires: { bins: ["ansible", "ansible-playbook"] }
    install:
      - id: ansible
        kind: pip
        package: ansible
        bins: ["ansible", "ansible-playbook"]
        label: "Install Ansible (pip)"
---
```

**After:**

```yaml
---
name: localsetup-some-skill
description: "Does X. Use when you need Ansible for server provisioning and playbooks."
metadata:
  version: "1.0"
compatibility: "Requires ansible, ansible-playbook (e.g. pip install ansible or system package)."
---
```

Optional: in the body, add one line such as "Install Ansible via your package manager or `pip install ansible` if not present."

### Description: platform-specific → generic

**Before:** `"Includes playbooks for OpenClaw VPS setup, security hardening, and common server configurations."`

**After:** `"Includes example playbooks for VPS setup, security hardening, and common server configurations. Bundled examples may reference one platform; adapt paths and commands for your environment."`

## Platform-neutralization rules (body)

Apply these in order. Detection is **product-agnostic**: look for patterns like "Integration with …", "From … Agent", "Run via … exec/tool", regardless of which product name appears.

### 1. Integration / "From X Agent" sections

- **Detect:** A section whose title matches patterns such as:
  - "Integration with *" (e.g. "Integration with OpenClaw")
  - "From * Agent" (e.g. "From OpenClaw Agent")
  - "Using * with this skill"
  - Or a subsection that is entirely platform-specific commands (e.g. `exec command="..."`, product-named paths, product-named secret stores).
- **Replace with:** The generic snippet below (or equivalent). Remove the platform-specific section; do not keep product names in the replacement unless in an optional "Example: ProductName" note.

**Generic snippet: Running from an agent**

```markdown
## Running playbooks from an agent

Use your platform's command or terminal tool to run ansible-playbook (or the skill's main commands). Paths in examples are relative to the skill directory or repo root; adjust for your layout.

- **Running playbooks:** Invoke the playbook via your platform's shell/exec/run capability (e.g. terminal, exec tool, or run command). Example: `ansible-playbook -i inventory/hosts.yml playbooks/site.yml --limit <host>`.
- **Secrets:** Store credentials in your platform's secret store or use Ansible Vault; pass vault password via `--ask-vault-pass` or a vault password file. Do not hardcode secrets in the skill or inventory.
```

If the original section mentioned a specific product's secret integration (e.g. Vaultwarden), add one line: "Some platforms offer secret managers; use them if available, otherwise Ansible Vault is the standard approach."

### 2. Platform-specific command examples in body

- **Detect:** Inline or block examples that show a single platform's invocation (e.g. `exec command="..."`, or "Run in OpenClaw: …").
- **Replace with:** Generic wording. Use "Run via your platform's command or terminal:" followed by the underlying command (e.g. `ansible-playbook ...`) without the platform wrapper. If the example is valuable for one platform, keep it as a short "Example (PlatformName):" subsection after the generic version.

### 3. Product-named host groups, playbooks, roles in prose

- In the **body text** (not in bundled files), you may generalize references to product-named inventory groups or playbook names (e.g. "openclaw" host group, "openclaw-vps.yml") to "agent hosts" or "your playbook for agent hosts" with a note that the bundled files may use a specific name (e.g. "Bundled playbook `openclaw-vps.yml` is one example; adapt or rename for your setup."). Do not rename files on disk; only adjust explanatory text in SKILL.md so the skill reads as platform-neutral.

## Tooling normalization

**Order:** Run after SKILL.md (and any other markdown in the skill) has been normalized. Do not hardcode a specific language; use the **framework's current tooling standard** as defined in the framework's permanent rules and docs ([TOOLING_POLICY.md](TOOLING_POLICY.md) and [INPUT_HARDENING_STANDARD.md](INPUT_HARDENING_STANDARD.md)). If the framework later changes its standard (e.g. to another language), normalization follows whatever is specified there.

### Default: rewrite to framework standard

1. **Identify tooling**  - List all executable or script-like assets in the skill (e.g. `scripts/`, entrypoints, any file that implements behavior the skill relies on). Treat these as the skill's "tooling."
2. **Rewrite in full**  - Replace each with an equivalent implementation written in the **framework's designated tooling language** and meeting the **framework's tooling and hardening requirements**:
   - Input: hostile-by-default; sanitize and validate all external input (CLI, env, paths, network, imported content) per [INPUT_HARDENING_STANDARD.md](INPUT_HARDENING_STANDARD.md).
   - No silent failure: no swallowed exceptions or quiet suppression on critical paths; partial-failure only when warnings are emitted and behavior is explicit.
   - Verbose, actionable errors: emit to STDERR with source context, exception type, and message so an AI agent or operator can correct inputs and self-debug. Error text must support a self-healing workflow (agent can fix the problem and retry).
   - Observability: errors must be specific enough for an agent to repair or retry; optional debug traces may be gated (e.g. env flag).
3. **Replicate behavior**  - The new implementation must replicate all functionality of the original (argument handling, side effects, outputs). The framework's standard language is capable of replicating typical scripting capabilities; do not drop behavior unless it is unsafe or out of scope.
4. **Update all documents**  - After rewriting tooling, update **every** reference to how the tool works: SKILL.md body (invocation, options, examples), any file under `references/`, and any other markdown or docs in the skill so that commands, paths, and descriptions match the new implementation. No stale references to the old scripts or language.

### Exception: keep original tooling

- The **user** may request an exception: keep the skill's original tooling (e.g. JavaScript/TypeScript, shell) and skip tooling normalization.
- If the user requests this, **do not rewrite** scripts. The user is then **responsible for supporting** that tooling (e.g. runtime, dependencies, security, maintenance). Document that the skill uses non-framework tooling and that support is the user's responsibility (e.g. one line in SKILL.md compatibility or body).
- When exception is in effect, still complete SKILL.md and document normalization; only the tooling rewrite step is skipped.

### Summary for approval

- Before rewriting, produce a **tooling normalization plan**: list scripts to be replaced, target language and entrypoints (from TOOLING_POLICY), and the list of documents that will be updated. Present to the user; if they approve, perform the rewrite and document updates. If they request exception, skip rewrite and note responsibility.

## Scope

- **Phase 1:** SKILL.md (and any other skill markdown) is normalized according to the user's choice when the skill is platform-specific: **keep as is**, **keep platform-specific but normalized**, or **fully normalize**. When the skill is not platform-specific, apply spec compliance and platform-neutralization by default. Skill directory name and frontmatter `name` are aligned with framework convention where applicable.
- **Phase 2:** Tooling normalization. All skill-provided scripts are replaced by equivalents that follow the framework's tooling standard (see TOOLING_POLICY.md, INPUT_HARDENING_STANDARD.md); then all remaining documents (references, SKILL.md body) are updated so references to the tool are consistent. User may request an exception to keep original tooling, in which case they assume responsibility for supporting it.

## Approval flow

**Phase 1 (SKILL.md and documents)**

1. **Determine if the skill is platform-specific**  - Check for references to a specific platform or context (e.g. OpenClaw, Cursor, product-named sections, "Integration with X", platform-specific metadata). If **not** platform-specific, go to step 4 (apply full spec + platform-neutralization, then approve and write). If **platform-specific**, go to step 2.
2. **Offer the user a choice**  - Present: "This skill references [platform/context]. How would you like to handle it? (1) Keep as is – no platform wording changes; (2) Keep platform-specific but normalized – spec compliance and standardized wording, platform references stay; (3) Fully normalize – make it adaptable for any platform." Get the user's choice.
3. **Apply the chosen action**  - (1) Keep as is: only ensure `name` matches directory and `metadata.version` present if missing; no other edits. (2) Platform-specific but normalized: apply spec-compliance checklist only; do not apply platform-neutralization rules (leave platform names and sections). (3) Fully normalize: apply full spec-compliance checklist and platform-neutralization rules. Produce a **summary** and **concrete list of key edits** for (2) or (3); present and get approval; if approved, write the normalized SKILL.md. For (1), no summary needed; proceed to Phase 2.
4. **When skill is not platform-specific**  - Apply the spec-compliance checklist and platform-neutralization rules to SKILL.md (in memory or a temp copy). Produce a **summary** and **concrete list of key edits**; present to the user and get explicit approval. If approved, write the normalized SKILL.md. If not, skip (during import: copy as-is and warn; standalone: do not write).
5. Proceed to Phase 2.

**Phase 2 (tooling)**

6. If the skill has no scripts or tooling, skip to step 9. Otherwise, ask whether the user wants to **keep original tooling** (exception). If yes, skip rewrite; add a short note that the skill uses non-framework tooling and that support is the user's responsibility; then go to step 9.
7. Produce a **tooling normalization plan**: list scripts to replace, target language and standards (from TOOLING_POLICY.md, INPUT_HARDENING_STANDARD.md), and the list of documents that will be updated to reference the new tooling.
8. Present the plan; get explicit approval. If approved, rewrite each script to the framework standard (input hardening, verbose errors, no silent failure, observability for self-healing/self-debug), then update all references in SKILL.md and references/* (and any other docs) so they describe the new implementation. If not approved, stop or apply exception per step 6.
9. Confirm what was normalized (documents only, or documents + tooling).

## Reference

- [Agent Skills specification](https://agentskills.io/specification)
- [TOOLING_POLICY.md](TOOLING_POLICY.md)  - Framework tooling language and dependency rules; normalization uses this as the standard (do not hardcode a language).
- [INPUT_HARDENING_STANDARD.md](INPUT_HARDENING_STANDARD.md)  - Mandatory input sanitization, validation, error handling, and observability for tooling.
- [SKILL_IMPORTING.md](SKILL_IMPORTING.md) for the import workflow (normalization is mandatory after security is verified)
- [PLATFORM_REGISTRY.md](PLATFORM_REGISTRY.md) for supported platforms and skill registration

---

<p align="center">
<strong>Author:</strong> <a href="https://github.com/cptnfren">Slavic Kozyuk</a><br>
<strong>Copyright</strong> © 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> – Innovate, Automate, Dominate.
</p>
