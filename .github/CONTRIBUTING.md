# Contributing

Thanks for taking the time to contribute. This document covers how to set up a development environment, the commit conventions the project uses, and what to expect from the review process.

---

## Development setup

Ubuntu 22.04+, Debian 12+, and other modern distros block bare `pip install` on the system Python (PEP 668). Use a virtual environment:

```bash
git clone https://github.com/cptnfren/best-backup.git
cd best-backup

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with all dependencies
pip install -e .

# Verify the commands are available
bbackup --version
bbman --version
```

You will need Docker running locally to test backup and restore operations. `rsync` is required for volume backups; install it with your system package manager if it is not already present.

---

## Making changes

Keep changes focused. A pull request that fixes one bug or adds one feature is easier to review than one that combines several concerns.

Run the syntax check before pushing:

```bash
python3 -m py_compile bbackup/*.py bbackup/management/*.py
```

---

## Commit messages

This project uses [conventional commits](https://www.conventionalcommits.org/). The prefix determines how the version is bumped on the next release:

| Prefix | Bump | When to use |
|---|---|---|
| `feat:` | minor | New user-visible feature |
| `fix:` | patch | Bug fix |
| `docs:` | patch | Documentation only |
| `refactor:` | patch | Code restructure, no behavior change |
| `perf:` | patch | Performance improvement |
| `test:` | patch | Test additions or changes |
| `chore:` | patch | Build, tooling, dependency updates |
| `feat!:` or `BREAKING CHANGE:` in body | major | Incompatible change |

One subject line, imperative mood, no trailing period. Example:

```
fix: handle missing Docker socket gracefully

Closes #12
```

---

## Pull requests

- Open a PR against `main`
- Fill in the PR template
- One feature or fix per PR
- CI must be green before merge

If you are fixing a reported issue, reference it in the PR description with `Closes #N` so it closes automatically on merge.

---

## Reporting bugs

Use the bug report issue template. The more detail you include (OS, Docker version, Python version, the exact command you ran, and the full error output), the faster it gets resolved.

---

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Treat everyone with respect.

<!-- project-footer:start -->

<br><br>

<p align="center">
Slavic Kozyuk<br>
&copy; 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> &mdash; <a href="https://github.com/cptnfren/best-backup/blob/main/LICENSE">MIT License</a>
</p>

<!-- project-footer:end -->
