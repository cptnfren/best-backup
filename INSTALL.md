# Installation guide

> All supported ways to install bbackup and register the `bbackup` and `bbman` commands.

---

## Recommended: pipx

`pipx` installs bbackup into an isolated virtual environment it manages itself and puts `bbackup` and `bbman` on your PATH. You never have to activate anything.

```bash
# Install pipx (Ubuntu/Debian)
sudo apt install pipx
pipx ensurepath   # adds ~/.local/bin to PATH — one-time setup
```

Open a new shell (or run `source ~/.bashrc`), then:

```bash
pipx install git+https://github.com/cptnfren/best-backup.git
```

```bash
# Verify
bbackup --version
bbman --version
```

**Updating later:**

```bash
pipx upgrade bbackup
```

**Uninstalling:**

```bash
pipx uninstall bbackup
```

---

## Manual virtual environment install (development / editable mode)

Use this if you want to edit the source code and have changes take effect immediately without reinstalling.

```bash
git clone https://github.com/cptnfren/best-backup.git
cd best-backup

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

To make the commands available in every new shell without activating the venv each time:

```bash
echo 'export PATH="$HOME/best-backup/.venv/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

## Production install (stable, from local clone, no editable mode)

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

If installed via pipx:

```bash
pipx uninstall bbackup
```

If installed into a manual venv:

```bash
source .venv/bin/activate
pip uninstall bbackup
# or remove the whole venv:
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

These distros block `pip install` on the system Python (PEP 668). The fix is `pipx`, which handles isolation automatically:

```bash
sudo apt install pipx && pipx ensurepath
pipx install git+https://github.com/cptnfren/best-backup.git
```

Do not pass `--break-system-packages`; that flag bypasses OS safeguards and can corrupt tools that depend on the system Python.

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
