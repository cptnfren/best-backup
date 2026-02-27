"""
Filesystem backup using host-direct rsync.
Backs up local file paths and directory trees without Docker involvement.
Purpose: Provide rsync-based backup for arbitrary host filesystem paths.
Created: 2026-02-26
Last Updated: 2026-02-26
"""

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, List, Optional

from .config import Config, FilesystemTarget
from .logging import get_logger

logger = get_logger("filesystem_backup")


class FilesystemBackup:
    """Back up host filesystem paths using rsync directly."""

    def __init__(self, config: Config):
        self.config = config

    def backup_path(
        self,
        target: FilesystemTarget,
        backup_dir: Path,
        incremental: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        Back up a single filesystem target using rsync.

        Args:
            target: FilesystemTarget describing the source path and excludes.
            backup_dir: Root backup directory for this run (e.g. staging/backup_YYYYMMDD_HHMMSS).
            incremental: Whether to use --link-dest for hard-linked incremental backup.
            progress_callback: Optional line-by-line rsync output handler.

        Returns:
            True on success, False on any failure.
        """
        dest = backup_dir / "filesystems" / target.name
        dest.mkdir(parents=True, exist_ok=True)

        exclude_file: Optional[Path] = None
        try:
            if target.excludes:
                tmp = Path(tempfile.mktemp(suffix=".excludes"))
                tmp.write_text("\n".join(target.excludes))
                exclude_file = tmp

            cmd = self._build_rsync_cmd(target, dest, incremental, exclude_file)
            return self._run_rsync(cmd, progress_callback)
        except Exception as e:
            logger.error(f"Filesystem backup failed for '{target.name}': {e}")
            return False
        finally:
            if exclude_file and exclude_file.exists():
                exclude_file.unlink()

    def _build_rsync_cmd(
        self,
        target: FilesystemTarget,
        dest: Path,
        incremental: bool,
        exclude_file_path: Optional[Path],
    ) -> List[str]:
        """Build the rsync command list for a filesystem target."""
        src = str(target.path).rstrip("/") + "/"
        cmd = [
            "rsync", "-av", "--delete",
            "--progress", "--info=progress2",
        ]

        if exclude_file_path:
            cmd += ["--exclude-from", str(exclude_file_path)]

        if incremental:
            prev = self._find_previous_backup(target.name, dest.parent.parent)
            if prev:
                cmd += ["--link-dest", str(prev)]

        cmd += [src, str(dest) + "/"]
        return cmd

    def _find_previous_backup(self, target_name: str, staging_dir: Path) -> Optional[Path]:
        """
        Find the most recent previous backup dir that contains this target.

        Scans siblings of the current run dir for backup_YYYYMMDD_HHMMSS pattern,
        sorted newest-first, returning the first that has a filesystems/name subdir.
        """
        if not staging_dir.exists():
            return None

        pattern = re.compile(r"^backup_\d{8}_\d{6}$")
        candidates = sorted(
            [d for d in staging_dir.iterdir() if d.is_dir() and pattern.match(d.name)],
            key=lambda d: d.name,
            reverse=True,
        )
        for candidate in candidates:
            candidate_path = candidate / "filesystems" / target_name
            if candidate_path.exists():
                return candidate_path
        return None

    def _run_rsync(
        self,
        cmd: List[str],
        progress_callback: Optional[Callable[[str], None]],
    ) -> bool:
        """
        Execute rsync, streaming output to progress_callback if provided.

        Returns True if rsync exits with code 0.
        """
        if progress_callback:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            for line in process.stdout:
                progress_callback(line)
            process.wait()
            return process.returncode == 0

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"rsync failed (rc={result.returncode}): {result.stderr.strip()}")
        return result.returncode == 0
