---
status: ACTIVE
version: 2.8
---

# Input hardening standard

Purpose: define mandatory defensive behavior for any script or tool that consumes external input.

## Scope

External input includes:
- CLI arguments and environment variables
- Filesystem data from user-provided paths
- Network payloads and API responses
- Imported skill/package content
- Text copied from unknown sources

## Mandatory controls

1) Hostile-by-default assumption
- Treat all external input as untrusted and potentially malicious.
- Do not execute or interpolate untrusted strings into shell commands.

2) Sanitization
- Normalize untrusted strings before parsing and before output:
  - remove control characters
  - normalize whitespace
  - enforce max-length limits
- Use safe decoding (`errors="replace"` or equivalent) for unknown encoding.

3) Validation
- Validate schema/type/range before use.
- Accept only expected URL schemes (`http`/`https`) and expected path boundaries.
- Reject invalid records explicitly, do not infer silently.

4) Error handling
- Do not hard-crash on malformed individual records when partial progress is possible.
- Emit actionable error output to STDERR with:
  - source context
  - exception type
  - exception message
- Exit non-zero when the task cannot continue.

5) No silent suppression
- Do not use silent failure patterns on critical paths (`except: pass`, swallowed errors).
- Partial-failure mode is allowed only when warnings are emitted and behavior is explicit.

6) Observability for AI and human operators
- Error text must be specific enough for an agent to repair inputs or retry with corrected parameters.
- Optional debug traces may be gated behind an env flag (example: `LOCALSETUP_DEBUG=1`).

## Enforcement

- Context-level invariant lives in platform context templates and master context rule.
- Baseline validator runs through `_localsetup/tools/verify_rules` and checks required hardening markers for external-input handlers.
- New external-input scripts must include sanitization and actionable error handling before merge.
