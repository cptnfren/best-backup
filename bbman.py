#!/usr/bin/env python3
"""
bbman - bbackup Management Wrapper
Universal wrapper script for managing bbackup application lifecycle.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

# Hard-coded default repository URL
# Can be overridden via BBACKUP_REPO_URL env var or config file
# Try to extract from Git remote, fallback to hard-coded value
try:
    import subprocess
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        timeout=2,
        cwd=Path(__file__).parent
    )
    if result.returncode == 0:
        DEFAULT_REPO_URL = result.stdout.strip().replace(".git", "")
    else:
        DEFAULT_REPO_URL = "https://github.com/cptnfren/best-backup"
except Exception:
    DEFAULT_REPO_URL = "https://github.com/cptnfren/best-backup"

# Add bbackup to path
sys.path.insert(0, str(Path(__file__).parent))

console = Console()


@click.group()
@click.version_option(version="1.0.0")
@click.pass_context
def cli(ctx):
    """bbman - bbackup Management Wrapper
    
    Comprehensive management tool for bbackup application.
    Provides first-run setup, version checking, health diagnostics, and more.
    """
    ctx.ensure_object(dict)
    ctx.obj["console"] = console
    
    # Get actual repo URL (with overrides)
    try:
        from bbackup.management.repo import get_repo_url
        ctx.obj["repo_url"] = get_repo_url()
    except Exception:
        ctx.obj["repo_url"] = DEFAULT_REPO_URL
    
    # Check for first run
    try:
        from bbackup.management.first_run import is_first_run
        if is_first_run():
            console.print("[yellow]⚠ First run detected. Run 'bbman setup' to configure.[/yellow]")
    except Exception:
        pass  # Continue if check fails


@cli.command()
@click.pass_context
def setup(ctx):
    """Run interactive setup wizard for first-time configuration."""
    try:
        from bbackup.management.setup_wizard import run_setup_wizard
        success = run_setup_wizard()
        sys.exit(0 if success else 1)
    except Exception as e:
        console.print(f"[red]Error running setup wizard: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def health(ctx):
    """Run comprehensive health check."""
    try:
        from bbackup.management.health import run_health_check, display_health_report
        
        results = run_health_check()
        display_health_report(results)
        
        sys.exit(0 if results.get("all_critical_ok") else 1)
    except Exception as e:
        console.print(f"[red]Error running health check: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@cli.command()
@click.option("--install", "-i", is_flag=True, help="Install missing packages")
@click.pass_context
def check_deps(ctx, install):
    """Check and install missing dependencies."""
    try:
        from bbackup.management.dependencies import check_and_install_dependencies, display_dependency_report
        
        results = check_and_install_dependencies(install_missing=install)
        display_dependency_report(results)
        
        all_ok = results.get("python_all_installed", False)
        sys.exit(0 if all_ok else 1)
    except Exception as e:
        console.print(f"[red]Error checking dependencies: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@cli.command()
@click.pass_context
def validate_config(ctx):
    """Validate configuration file."""
    try:
        from bbackup.config import Config
        from pathlib import Path
        
        config = Config()
        
        if not config.config_path:
            console.print("[yellow]⚠ No config file found, using defaults[/yellow]")
            console.print("[dim]Run 'bbman setup' to create a config file[/dim]")
            sys.exit(0)
        
        console.print(f"[green]✓ Config file valid: {config.config_path}[/green]")
        console.print(f"[dim]Backup sets: {len(config.backup_sets)}[/dim]")
        console.print(f"[dim]Enabled remotes: {len([r for r in config.remotes.values() if r.enabled])}[/dim]")
        console.print(f"[dim]Encryption: {'enabled' if config.encryption.enabled else 'disabled'}[/dim]")
        
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]✗ Config validation failed: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show backup status and history."""
    try:
        from bbackup.management.status import display_backup_status
        from bbackup.config import Config
        
        config = Config()
        display_backup_status(config)
    except Exception as e:
        console.print(f"[red]Error checking status: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@cli.command()
@click.option("--staging-days", default=7, help="Keep staging files newer than N days")
@click.option("--log-days", default=30, help="Keep log files newer than N days")
@click.option("--no-backups", is_flag=True, help="Don't cleanup old backups")
@click.option("--no-temp", is_flag=True, help="Don't cleanup temporary files")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.pass_context
def cleanup(ctx, staging_days, log_days, no_backups, no_temp, yes):
    """Cleanup old files and backups."""
    try:
        from bbackup.management.cleanup import run_cleanup
        from bbackup.config import Config
        
        config = Config()
        results = run_cleanup(
            config=config,
            staging_days=staging_days,
            log_days=log_days,
            cleanup_backups=not no_backups,
            cleanup_temp=not no_temp,
            confirm=not yes
        )
        
        total_removed = (
            results["staging_removed"] +
            results["logs_removed"] +
            results["backups_removed"] +
            results["temp_removed"]
        )
        
        console.print(f"\n[green]✓ Cleanup complete: {total_removed} items removed[/green]")
    except Exception as e:
        console.print(f"[red]Error during cleanup: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@cli.command()
@click.option("--output", "-o", type=click.Path(), help="Save report to file")
@click.pass_context
def diagnostics(ctx, output):
    """Run diagnostics and generate report."""
    try:
        from bbackup.management.diagnostics import run_diagnostics, display_diagnostics_report, generate_diagnostics_report
        from bbackup.config import Config
        from pathlib import Path
        
        config = Config()
        diagnostics_data = run_diagnostics(config)
        
        display_diagnostics_report(diagnostics_data)
        
        if output:
            output_path = Path(output)
            report_text = generate_diagnostics_report(diagnostics_data, output_path)
            console.print(f"\n[green]✓ Report saved to: {output_path}[/green]")
    except Exception as e:
        console.print(f"[red]Error running diagnostics: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@cli.command()
@click.option("--branch", default="main", help="Branch to check")
@click.pass_context
def check_updates(ctx, branch):
    """Check for updates (file-level with checksums)."""
    try:
        from bbackup.management.version import check_for_updates
        from pathlib import Path
        
        repo_root = Path(__file__).parent
        repo_url = ctx.obj.get("repo_url", DEFAULT_REPO_URL)
        
        console.print(f"[cyan]Checking for updates from {repo_url} (branch: {branch})...[/cyan]")
        
        result = check_for_updates(repo_root, repo_url, branch)
        
        if result.get("error"):
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)
        
        if result.get("has_updates"):
            console.print("[yellow]⚠ Updates available![/yellow]")
            console.print(f"[dim]Changed files: {len(result.get('changed', []))}[/dim]")
            console.print(f"[dim]New files: {len(result.get('new', []))}[/dim]")
            console.print(f"[dim]Removed files: {len(result.get('removed', []))}[/dim]")
            
            if result.get("changed"):
                console.print("\n[bold]Changed files:[/bold]")
                for file in result["changed"][:10]:  # Show first 10
                    console.print(f"  [yellow]• {file}[/yellow]")
                if len(result["changed"]) > 10:
                    console.print(f"  [dim]... and {len(result['changed']) - 10} more[/dim]")
            
            console.print("\n[cyan]Run 'bbman update' to update[/cyan]")
        else:
            console.print("[green]✓ No updates available[/green]")
            console.print(f"[dim]Local files: {result.get('local_count', 0)}, Remote files: {result.get('remote_count', 0)}[/dim]")
    except Exception as e:
        console.print(f"[red]Error checking updates: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@cli.command()
@click.option("--branch", default="main", help="Branch to update from")
@click.option("--method", type=click.Choice(["git", "download"]), default="git", help="Update method")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.pass_context
def update(ctx, branch, method, yes):
    """Update application files."""
    try:
        from bbackup.management.updater import perform_update
        from bbackup.management.version import check_for_updates
        from pathlib import Path
        
        repo_root = Path(__file__).parent
        repo_url = ctx.obj.get("repo_url", DEFAULT_REPO_URL)
        
        # Check for updates first
        console.print(f"[cyan]Checking for updates from {repo_url} (branch: {branch})...[/cyan]")
        update_info = check_for_updates(repo_root, repo_url, branch)
        
        if not update_info.get("has_updates"):
            console.print("[green]✓ No updates available[/green]")
            return
        
        # Show what will be updated
        console.print(f"[yellow]⚠ Updates available:[/yellow]")
        console.print(f"  [dim]Changed: {len(update_info.get('changed', []))} files[/dim]")
        console.print(f"  [dim]New: {len(update_info.get('new', []))} files[/dim]")
        console.print(f"  [dim]Removed: {len(update_info.get('removed', []))} files[/dim]")
        
        if not yes:
            from rich.prompt import Confirm
            if not Confirm.ask("Proceed with update?", default=True):
                console.print("[dim]Update cancelled[/dim]")
                return
        
        # Perform update
        console.print(f"[cyan]Updating using {method} method...[/cyan]")
        result = perform_update(repo_root, repo_url, branch, method)
        
        if result.get("success"):
            console.print(f"[green]✓ Update completed successfully![/green]")
            console.print(f"[dim]Files updated: {result.get('files_updated', 0)}[/dim]")
            if result.get("backup_dir"):
                console.print(f"[dim]Backup saved to: {result['backup_dir']}[/dim]")
        else:
            console.print(f"[red]✗ Update failed: {result.get('message', 'Unknown error')}[/red]")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error during update: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@cli.command()
@click.option("--url", help="Set repository URL override")
@click.pass_context
def repo_url(ctx, url):
    """Show or set repository URL override."""
    try:
        from bbackup.management.repo import get_repo_url, set_repo_url, parse_repo_url
        
        if url:
            if set_repo_url(url):
                console.print(f"[green]✓ Repository URL set to: {url}[/green]")
                parsed = parse_repo_url(url)
                console.print(f"[dim]Type: {parsed['type']}, Owner: {parsed['owner']}, Repo: {parsed['repo']}[/dim]")
            else:
                console.print(f"[red]✗ Failed to set repository URL[/red]")
                sys.exit(1)
        else:
            current_url = get_repo_url()
            console.print(f"[cyan]Current repository URL: {current_url}[/cyan]")
            parsed = parse_repo_url(current_url)
            if parsed['type'] != 'unknown':
                console.print(f"[dim]Type: {parsed['type']}, Owner: {parsed['owner']}, Repo: {parsed['repo']}[/dim]")
            console.print("[dim]Override via: BBACKUP_REPO_URL env var or config file[/dim]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument("command", nargs=-1)
@click.pass_context
def run(ctx, command):
    """Launch main bbackup application.
    
    Pass any bbackup command and arguments after 'run'.
    Example: bbman run backup --containers my_container
    """
    # Import and run bbackup CLI
    try:
        from bbackup.cli import cli as bbackup_cli
        
        # Reconstruct sys.argv for bbackup
        # Remove 'bbman' and 'run', keep everything else
        original_argv = sys.argv[:]
        try:
            # Find 'run' in argv and replace with bbackup command
            if 'run' in sys.argv:
                run_idx = sys.argv.index('run')
                sys.argv = ["bbackup"] + sys.argv[run_idx + 1:]
            else:
                # Fallback: use command tuple
                sys.argv = ["bbackup"] + list(command) if command else ["bbackup"]
            
            bbackup_cli()
        finally:
            sys.argv = original_argv
    except ImportError as e:
        console.print(f"[red]Error importing bbackup: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error running bbackup: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
