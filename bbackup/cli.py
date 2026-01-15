"""
Main CLI entry point for bbackup.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Set
import click
from rich.console import Console
from rich.table import Table
from rich import box

from .config import Config, BackupScope
from .docker_backup import DockerBackup
from .tui import BackupTUI, BackupStatus
from .remote import RemoteStorageManager
from .rotation import BackupRotation
from .backup_runner import BackupRunner
from .restore import DockerRestore


@click.group()
@click.version_option(version="1.0.0")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file",
)
@click.pass_context
def cli(ctx, config):
    """bbackup - Docker Backup Tool with Rich TUI"""
    ctx.ensure_object(dict)
    ctx.obj["config"] = Config(config_path=config)
    ctx.obj["console"] = Console()


@cli.command()
@click.option(
    "--containers",
    "-C",
    multiple=True,
    help="Container names to backup (can specify multiple)",
)
@click.option(
    "--backup-set",
    "-s",
    help="Use predefined backup set from config",
)
@click.option(
    "--config-only",
    is_flag=True,
    help="Backup only configurations (no volumes)",
)
@click.option(
    "--volumes-only",
    is_flag=True,
    help="Backup only volumes (no configs)",
)
@click.option(
    "--no-networks",
    is_flag=True,
    help="Skip network backups",
)
@click.option(
    "--incremental",
    "-i",
    is_flag=True,
    help="Use incremental backup (rsync link-dest)",
)
@click.option(
    "--interactive",
    "-I",
    is_flag=True,
    default=True,
    help="Use interactive TUI (default: True)",
)
@click.option(
    "--no-interactive",
    is_flag=True,
    help="Disable interactive mode (use config/CLI only)",
)
@click.option(
    "--remote",
    "-r",
    multiple=True,
    help="Remote storage destinations (can specify multiple)",
)
@click.pass_context
def backup(
    ctx,
    containers,
    backup_set,
    config_only,
    volumes_only,
    no_networks,
    incremental,
    interactive,
    no_interactive,
    remote,
):
    """Create Docker backup"""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    tui = BackupTUI(config)
    
    # Show header
    tui.show_header()
    
    # Determine backup scope
    scope = BackupScope()
    if config_only:
        scope.volumes = False
        scope.networks = False
    elif volumes_only:
        scope.containers = False
        scope.configs = False
        scope.networks = False
    
    if no_networks:
        scope.networks = False
    
    # Determine containers to backup
    containers_to_backup: Optional[List[str]] = None
    
    if backup_set:
        # Use backup set from config
        backup_set_obj = config.get_backup_set(backup_set)
        if backup_set_obj:
            containers_to_backup = backup_set_obj.containers
            scope = backup_set_obj.scope
            console.print(f"[green]Using backup set: {backup_set}[/green]")
        else:
            console.print(f"[red]Backup set '{backup_set}' not found in config[/red]")
            sys.exit(1)
    elif containers:
        # Use CLI-specified containers
        containers_to_backup = list(containers)
    elif interactive and not no_interactive:
        # Interactive selection
        docker_backup = DockerBackup(config)
        all_containers = docker_backup.get_all_containers()
        selected = tui.select_containers(all_containers)
        containers_to_backup = list(selected)
        
        # Also allow scope selection
        scope_dict = tui.select_scope()
        scope.containers = scope_dict.get("containers", True)
        scope.volumes = scope_dict.get("volumes", True)
        scope.networks = scope_dict.get("networks", True)
        scope.configs = scope_dict.get("configs", True)
    
    if not containers_to_backup:
        console.print("[red]No containers selected for backup[/red]")
        sys.exit(1)
    
    # Determine remotes
    remotes_to_use = []
    if remote:
        # Use CLI-specified remotes
        for r_name in remote:
            if r_name in config.remotes:
                remotes_to_use.append(config.remotes[r_name])
            else:
                console.print(f"[yellow]Warning: Remote '{r_name}' not found in config[/yellow]")
    else:
        # Use all enabled remotes from config
        remotes_to_use = config.get_enabled_remotes()
    
    if not remotes_to_use:
        console.print("[yellow]Warning: No remote storage destinations configured[/yellow]")
        console.print("[dim]Backup will be created locally only[/dim]")
    
    # Create backup with live dashboard
    staging_dir = Path(config.get_staging_dir())
    backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{backup_timestamp}"
    backup_dir = staging_dir / backup_name
    
    # Initialize status and runner
    status = BackupStatus()
    tui.status = status
    runner = BackupRunner(config, status)
    
    # Define backup operation
    def backup_operation():
        try:
            status.status = "running"
            results = runner.run_backup(
                backup_dir=backup_dir,
                containers=containers_to_backup,
                scope=scope,
                incremental=incremental or config.incremental.enabled,
            )
            
            # Upload to remotes
            if remotes_to_use and status.status != "cancelled":
                runner.upload_to_remotes(backup_dir, backup_name, remotes_to_use)
            
            if status.status != "cancelled":
                status.status = "completed"
        except Exception as e:
            status.status = "error"
            status.add_error(str(e))
    
    # Run with live dashboard
    try:
        tui.run_with_live_dashboard(backup_operation)
    except KeyboardInterrupt:
        status.cancel()
        console.print("\n[yellow]Backup cancelled by user[/yellow]")
        sys.exit(1)
    
    # Show final results
    if status.status == "completed":
        console.print(f"\n[green]✓ Backup completed: {backup_dir}[/green]")
        tui.show_backup_status(
            {
                "containers": status.containers_status,
                "volumes": status.volumes_status,
                "networks": status.networks_status,
            },
            status.errors,
        )
    elif status.status == "cancelled":
        console.print("\n[yellow]Backup was cancelled[/yellow]")
        sys.exit(1)
    else:
        console.print("\n[red]Backup failed or was interrupted[/red]")
        if status.errors:
            for error in status.errors:
                console.print(f"  [red]•[/red] {error}")
        sys.exit(1)


@cli.command()
@click.pass_context
def list_containers(ctx):
    """List all Docker containers"""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    tui = BackupTUI(config)
    
    tui.show_header("Container List")
    
    docker_backup = DockerBackup(config)
    containers = docker_backup.get_all_containers()
    
    # Create table
    from rich.table import Table
    from rich import box
    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("Status", width=12)
    table.add_column("Name", style="cyan", width=30)
    table.add_column("Image", style="dim", width=40)
    
    for container in containers:
        status_color = "green" if container["status"] == "running" else "yellow"
        table.add_row(
            f"[{status_color}]{container['status']}[/{status_color}]",
            container["name"],
            container["image"][:40],
        )
    
    console.print(table)


@cli.command()
@click.pass_context
def list_backup_sets(ctx):
    """List available backup sets"""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    tui = BackupTUI(config)
    
    tui.show_header("Backup Sets")
    
    if not config.backup_sets:
        console.print("[yellow]No backup sets configured[/yellow]")
        return
    
    for name, backup_set in config.backup_sets.items():
        console.print(f"\n[bold cyan]{name}[/bold cyan]")
        console.print(f"  Description: {backup_set.description}")
        console.print(f"  Containers: {', '.join(backup_set.containers)}")


@cli.command()
@click.pass_context
def init_config(ctx):
    """Initialize configuration file"""
    config_path = os.path.expanduser("~/.config/bbackup/config.yaml")
    config_dir = os.path.dirname(config_path)
    
    os.makedirs(config_dir, exist_ok=True)
    
    # Copy example config
    example_config = Path(__file__).parent.parent / "config.yaml.example"
    if example_config.exists():
        import shutil
        shutil.copy(example_config, config_path)
        console: Console = ctx.obj["console"]
        console.print(f"[green]Configuration file created: {config_path}[/green]")
        console.print("[dim]Please edit the file to configure your backup settings.[/dim]")
    else:
        console.print("[red]Example config not found[/red]")


@cli.command()
@click.option(
    "--backup-path",
    "-p",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to backup directory",
)
@click.option(
    "--containers",
    "-C",
    multiple=True,
    help="Container names to restore (can specify multiple)",
)
@click.option(
    "--volumes",
    "-V",
    multiple=True,
    help="Volume names to restore (can specify multiple)",
)
@click.option(
    "--networks",
    "-N",
    multiple=True,
    help="Network names to restore (can specify multiple)",
)
@click.option(
    "--rename",
    "-r",
    multiple=True,
    help="Rename mapping (format: old_name:new_name, can specify multiple)",
)
@click.option(
    "--all",
    is_flag=True,
    help="Restore all containers, volumes, and networks from backup",
)
@click.pass_context
def restore(
    ctx,
    backup_path,
    containers,
    volumes,
    networks,
    rename,
    all,
):
    """Restore Docker backup"""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    backup_path = Path(backup_path)
    if not backup_path.exists():
        console.print(f"[red]Backup path does not exist: {backup_path}[/red]")
        sys.exit(1)
    
    restore_mgr = DockerRestore(config)
    
    # Parse rename mappings
    rename_map = {}
    if rename:
        for mapping in rename:
            if ":" in mapping:
                old_name, new_name = mapping.split(":", 1)
                rename_map[old_name.strip()] = new_name.strip()
    
    # Determine what to restore
    containers_to_restore = None
    volumes_to_restore = None
    networks_to_restore = None
    
    if all:
        # Restore everything from backup
        configs_dir = backup_path / "configs"
        volumes_dir = backup_path / "volumes"
        networks_dir = backup_path / "networks"
        
        if configs_dir.exists():
            containers_to_restore = [f.stem.replace("_config", "") for f in configs_dir.glob("*_config.json")]
        if volumes_dir.exists():
            volumes_to_restore = [d.name for d in volumes_dir.iterdir() if d.is_dir()]
        if networks_dir.exists():
            networks_to_restore = [f.stem for f in networks_dir.glob("*.json")]
    else:
        if containers:
            containers_to_restore = list(containers)
        if volumes:
            volumes_to_restore = list(volumes)
        if networks:
            networks_to_restore = list(networks)
    
    if not containers_to_restore and not volumes_to_restore and not networks_to_restore:
        console.print("[red]No containers, volumes, or networks specified to restore[/red]")
        console.print("[dim]Use --all to restore everything, or specify --containers, --volumes, or --networks[/dim]")
        sys.exit(1)
    
    console.print(f"[bold]Restoring from backup: {backup_path}[/bold]\n")
    
    # Perform restore
    results = restore_mgr.restore_backup(
        backup_path=backup_path,
        containers=containers_to_restore,
        volumes=volumes_to_restore,
        networks=networks_to_restore,
        rename_map=rename_map,
    )
    
    # Show results
    console.print("\n[bold]Restore Results:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold green", box=box.ROUNDED)
    table.add_column("Type", style="cyan", width=15)
    table.add_column("Success", style="green", width=10)
    table.add_column("Failed", style="red", width=10)
    
    containers_success = sum(1 for v in results.get("containers", {}).values() if v == "success")
    containers_failed = sum(1 for v in results.get("containers", {}).values() if v == "failed")
    volumes_success = sum(1 for v in results.get("volumes", {}).values() if v == "success")
    volumes_failed = sum(1 for v in results.get("volumes", {}).values() if v == "failed")
    networks_success = sum(1 for v in results.get("networks", {}).values() if v == "success")
    networks_failed = sum(1 for v in results.get("networks", {}).values() if v == "failed")
    
    if containers_to_restore:
        table.add_row("Containers", str(containers_success), str(containers_failed))
    if volumes_to_restore:
        table.add_row("Volumes", str(volumes_success), str(volumes_failed))
    if networks_to_restore:
        table.add_row("Networks", str(networks_success), str(networks_failed))
    
    console.print(table)
    
    # Errors
    if results.get("errors"):
        console.print("\n[bold red]Errors:[/bold red]")
        for error in results["errors"]:
            console.print(f"  [red]•[/red] {error}")
    
    if results.get("errors") and len(results["errors"]) > 0:
        sys.exit(1)
    else:
        console.print(f"\n[green]✓ Restore completed successfully[/green]")


@cli.command()
@click.option(
    "--backup-dir",
    "-d",
    type=click.Path(exists=True, path_type=Path),
    help="Backup directory to list (default: staging directory)",
)
@click.pass_context
def list_backups(ctx, backup_dir):
    """List available backups"""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    if backup_dir:
        backup_path = Path(backup_dir)
    else:
        backup_path = Path(config.get_staging_dir())
    
    restore_mgr = DockerRestore(config)
    backups = restore_mgr.list_backups(backup_path)
    
    if not backups:
        console.print(f"[yellow]No backups found in {backup_path}[/yellow]")
        return
    
    console.print(f"\n[bold]Available Backups in {backup_path}:[/bold]\n")
    
    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("Backup Name", style="cyan", width=30)
    table.add_column("Timestamp", style="dim", width=25)
    table.add_column("Path", style="dim", width=40)
    
    for backup in backups:
        table.add_row(
            backup["name"],
            backup["timestamp"],
            str(backup["path"]),
        )
    
    console.print(table)


if __name__ == "__main__":
    cli()
