# Installation guide

> All supported ways to install bbackup and register the `bbackup` and `bbman` commands.

---

## Recommended: virtual environment install

Ubuntu 22.04+ and Debian 12+ enforce PEP 668, which blocks `pip install` on the system Python to protect OS-managed packages. A virtual environment sidesteps this cleanly and is the safest approach on any modern Linux server.

```bash
git clone https://github.com/cptnfren/best-backup.git
cd best-backup

# Create and activate the venv (one-time)
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode (source changes take effect immediately)
pip install -e .
```

After activation, both `bbackup` and `bbman` are available for the lifetime of that shell session.

To make the commands available in every new shell without manually activating the venv, add wrapper entries to your PATH:

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/best-backup/.venv/bin:$PATH"
```

```bash
# Verify
which bbackup
which bbman
bbackup --version
bbman --version
```

If you prefer the venv to live outside the repo (e.g. under `~/.venvs/`):

```bash
python3 -m venv ~/.venvs/bbackup
source ~/.venvs/bbackup/bin/activate
pip install -e /path/to/best-backup
```

---

## Production install (stable, no source edits needed)

Same venv pattern, without editable mode:

```bash
python3 -m venv ~/.venvs/bbackup
source ~/.venvs/bbackup/bin/activate
pip install /path/to/best-backup
```

---

## Symlinks (no install, quick)

If you want to run from the repo directory without `pip`:

```bash
chmod +x bbackup.py bbman.py

sudo ln -s $(pwd)/bbackup.py /usr/local/bin/bbackup
sudo ln -s $(pwd)/bbman.py /usr/local/bin/bbman
```

For a user-only version without `sudo`:

```bash
mkdir -p ~/bin
ln -s $(pwd)/bbackup.py ~/bin/bbackup
ln -s $(pwd)/bbman.py ~/bin/bbman

# Add ~/bin to PATH if not already there
export PATH="$HOME/bin:$PATH"
```

---

## Add to PATH (run directly from repo)

```bash
export PATH="$PATH:/path/to/best-backup"
chmod +x /path/to/best-backup/bbackup.py
chmod +x /path/to/best-backup/bbman.py
```

Add that export line to your shell profile to make it permanent.

---

## Uninstall

If installed into a venv, activate it first then uninstall:

```bash
source .venv/bin/activate
pip uninstall bbackup
```

To remove the entire venv:

```bash
rm -rf .venv
```

If installed via symlinks:

```bash
sudo rm /usr/local/bin/bbackup /usr/local/bin/bbman
# or for user symlinks:
rm ~/bin/bbackup ~/bin/bbman
```

---

## Python version

Python 3.10+ is required. Check with:

```bash
python3 --version
```

If you have multiple Python versions and need to target a specific one:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## Troubleshooting

**`bbackup: command not found` after install**

If you installed into a venv, make sure the venv is active (or its `bin/` directory is on your PATH):

```bash
source .venv/bin/activate
which bbackup   # should now resolve
```

Alternatively, add the venv bin dir to your shell profile permanently:

```bash
echo 'export PATH="$HOME/best-backup/.venv/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Permission denied**

Use a virtual environment (no sudo required):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

**`error: externally-managed-environment` on Ubuntu 22.04+ / Debian 12+**

These distros block `pip install` on the system Python (PEP 668). Use a virtual environment as shown in the recommended install section above. Do not pass `--break-system-packages`; that flag bypasses OS safeguards and can corrupt system tools that depend on Python.

**Packages fail to install**

Make sure pip is up to date inside your venv:

```bash
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

---

## Post-install setup

Once the commands are available, run the setup wizard:

```bash
bbman setup
```

See [QUICKSTART.md](QUICKSTART.md) for what to do next.

<!-- project-footer:start -->

<br><br>

<p align="center">
Slavic Kozyuk<br>
&copy; 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> &mdash; <a href="https://github.com/cptnfren/best-backup/blob/main/LICENSE">MIT License</a>
</p>

<!-- project-footer:end -->
