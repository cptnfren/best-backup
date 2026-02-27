# Installation guide

> All supported ways to install bbackup and register the `bbackup` and `bbman` commands.

---

## Recommended: pip install (editable mode)

```bash
cd best-backup
pip install -e .
```

Editable mode means any changes you make to the source take effect immediately without reinstalling. Both `bbackup` and `bbman` are registered as system commands.

```bash
# Verify
which bbackup
which bbman
bbackup --version
bbman --version
```

---

## Normal pip install (production / stable)

```bash
pip install .
```

Copies files to site-packages. Requires reinstall to pick up source changes.

---

## User install (no sudo required)

```bash
pip install --user -e .
```

Installs to `~/.local/bin`. If that directory is not on your PATH:

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc
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

If installed via pip:

```bash
pip uninstall bbackup
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
python3.10 -m pip install -e .
```

---

## Troubleshooting

**`bbackup: command not found` after pip install**

Check that pip's bin directory is on your PATH:

```bash
pip show bbackup | grep Location
# Add that location's ../bin to PATH if needed
```

Or try:

```bash
pip install --user -e .
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Permission denied**

```bash
pip install --user -e .   # No sudo needed
```

**Packages fail to install**

Make sure pip is up to date:

```bash
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
