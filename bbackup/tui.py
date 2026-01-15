"""
Rich TUI interface for bbackup.
Provides BTOP-like graphical interface for backup operations with live updates.
"""

import time
import threading
from typing import List, Dict, Optional, Set, Callable
from pathlib import Path
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn, 
    TimeElapsedColumn, TimeRemainingColumn, MofNCompleteColumn
)
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.prompt import Confirm, Prompt
from rich.align import Align
from rich import box
from rich.live import Live
from rich.console import Group

from .config import Config, BackupSet


class BackupStatus:
    """Thread-safe status tracker for backup operations."""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.current_action = "Initializing..."
        self.current_item = ""
        self.total_items = 0
        self.completed_items = 0
        self.start_time = None
        self.eta = None
        self.errors = []
        self.warnings = []
        self.status = "idle"  # idle, running, paused, cancelled, completed, error
        self.containers_status = {}
        self.volumes_status = {}
        self.networks_status = {}
        self.remote_status = {}
    
    def update(self, action: str = None, item: str = None, 
               completed: int = None, total: int = None):
        """Update status (thread-safe)."""
        with self.lock:
            if action:
                self.current_action = action
            if item:
                self.current_item = item
            if completed is not None:
                self.completed_items = completed
            if total is not None:
                self.total_items = total
            
            # Calculate ETA
            if self.start_time and self.completed_items > 0 and self.total_items > 0:
                elapsed = time.time() - self.start_time
                rate = self.completed_items / elapsed
                remaining = self.total_items - self.completed_items
                if rate > 0:
                    self.eta = timedelta(seconds=int(remaining / rate))
                else:
                    self.eta = None
    
    def start(self):
        """Start timing."""
        with self.lock:
            self.start_time = time.time()
            self.status = "running"
    
    def cancel(self):
        """Cancel operation."""
        with self.lock:
            self.status = "cancelled"
    
    def add_error(self, error: str):
        """Add error message."""
        with self.lock:
            self.errors.append(error)
    
    def add_warning(self, warning: str):
        """Add warning message."""
        with self.lock:
            self.warnings.append(warning)


class BackupTUI:
    """Terminal UI for backup operations with BTOP-like interface."""
    
    def __init__(self, config: Config):
        self.config = config
        self.console = Console()
        self.status = BackupStatus()
        self.cancelled = False
    
    def show_header(self, title: str = "bbackup - Docker Backup Tool"):
        """Display header panel."""
        header = Panel(
            f"[bold cyan]{title}[/bold cyan]\n"
            f"[dim]Version 1.0.0 - Docker Backup & Restore[/dim]",
            box=box.ROUNDED,
            border_style="cyan",
        )
        self.console.print(header)
    
    def create_live_dashboard(self) -> Callable:
        """Create live-updating dashboard (BTOP-like)."""
        def generate_layout() -> Layout:
            layout = Layout()
            layout.split_column(
                Layout(name="header", size=5),
                Layout(name="main", ratio=2),
                Layout(name="progress", size=8),
                Layout(name="status", size=6),
                Layout(name="footer", size=3),
            )
            
            layout["main"].split_row(
                Layout(name="containers", ratio=1),
                Layout(name="volumes", ratio=1),
            )
            
            # Header
            elapsed = ""
            if self.status.start_time:
                elapsed_seconds = int(time.time() - self.status.start_time)
                elapsed = f" | Elapsed: {timedelta(seconds=elapsed_seconds)}"
            
            eta_str = ""
            if self.status.eta:
                eta_str = f" | ETA: {self.status.eta}"
            
            status_color = {
                "idle": "yellow",
                "running": "green",
                "paused": "yellow",
                "cancelled": "red",
                "completed": "green",
                "error": "red",
            }.get(self.status.status, "white")
            
            header_content = f"""
[bold cyan]bbackup[/bold cyan] - Docker Backup Tool  [dim]v1.0.0[/dim]
Status: [{status_color}]{self.status.status.upper()}[/{status_color}]{elapsed}{eta_str}

[bold]Current:[/bold] {self.status.current_action}
[bold]Item:[/bold] {self.status.current_item if self.status.current_item else 'N/A'}
"""
            layout["header"].update(Panel(header_content.strip(), border_style="cyan", box=box.ROUNDED))
            
            # Progress bar
            progress_bar = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=50),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("•"),
                MofNCompleteColumn(),
                TextColumn("•"),
                TimeElapsedColumn(),
            )
            
            # Add TimeRemainingColumn only if we have progress
            if self.status.total_items > 0 and self.status.completed_items > 0:
                progress_bar.columns = (
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(bar_width=50),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TextColumn("•"),
                    MofNCompleteColumn(),
                    TextColumn("•"),
                    TimeElapsedColumn(),
                    TextColumn("•"),
                    TimeRemainingColumn(),
                )
            
            total = self.status.total_items if self.status.total_items > 0 else None
            task = progress_bar.add_task(
                self.status.current_action[:60] if self.status.current_action else "Processing...",
                total=total,
                completed=self.status.completed_items,
            )
            
            layout["progress"].update(
                Panel(progress_bar, title="Progress", border_style="blue", box=box.ROUNDED)
            )
            
            # Containers panel
            containers_table = Table(show_header=True, box=box.SIMPLE, show_edge=False)
            containers_table.add_column("Container", style="cyan", width=25)
            containers_table.add_column("Status", width=12)
            containers_table.add_column("Size", style="dim", width=10)
            
            for name, status in list(self.status.containers_status.items())[:10]:
                status_color = "green" if status == "success" else "red" if status == "failed" else "yellow"
                containers_table.add_row(
                    name[:25],
                    f"[{status_color}]{status}[/{status_color}]",
                    "-",
                )
            
            if len(self.status.containers_status) == 0:
                containers_table.add_row("[dim]No containers backed up yet[/dim]", "", "")
            
            layout["containers"].update(
                Panel(containers_table, title="Containers", border_style="green", box=box.ROUNDED)
            )
            
            # Volumes panel
            volumes_table = Table(show_header=True, box=box.SIMPLE, show_edge=False)
            volumes_table.add_column("Volume", style="cyan", width=25)
            volumes_table.add_column("Status", width=12)
            volumes_table.add_column("Size", style="dim", width=10)
            
            for name, status in list(self.status.volumes_status.items())[:10]:
                status_color = "green" if status == "success" else "red" if status == "failed" else "yellow"
                volumes_table.add_row(
                    name[:25],
                    f"[{status_color}]{status}[/{status_color}]",
                    "-",
                )
            
            if len(self.status.volumes_status) == 0:
                volumes_table.add_row("[dim]No volumes backed up yet[/dim]", "", "")
            
            layout["volumes"].update(
                Panel(volumes_table, title="Volumes", border_style="yellow", box=box.ROUNDED)
            )
            
            # Status panel
            status_lines = []
            if self.status.errors:
                status_lines.append(f"[red]Errors: {len(self.status.errors)}[/red]")
                for error in self.status.errors[-3:]:  # Show last 3 errors
                    status_lines.append(f"  [red]•[/red] {error[:60]}")
            if self.status.warnings:
                status_lines.append(f"[yellow]Warnings: {len(self.status.warnings)}[/yellow]")
                for warning in self.status.warnings[-2:]:  # Show last 2 warnings
                    status_lines.append(f"  [yellow]•[/yellow] {warning[:60]}")
            if not status_lines:
                status_lines.append("[green]No errors or warnings[/green]")
            
            layout["status"].update(
                Panel("\n".join(status_lines), title="Status", border_style="magenta", box=box.ROUNDED)
            )
            
            # Footer with controls
            footer_content = """
[dim]Controls:[/dim] [bold]Q[/bold] = Quit/Cancel  [bold]P[/bold] = Pause  [bold]S[/bold] = Skip Current  [bold]H[/bold] = Help
"""
            layout["footer"].update(
                Panel(footer_content.strip(), border_style="dim", box=box.SIMPLE)
            )
            
            return layout
        
        return generate_layout
    
    def run_with_live_dashboard(self, operation: Callable, *args, **kwargs):
        """Run operation with live dashboard."""
        import sys
        import select
        
        # Run operation in background
        operation_thread = threading.Thread(target=operation, args=args, kwargs=kwargs, daemon=True)
        operation_thread.start()
        
        # Update dashboard with keyboard handling
        try:
            with Live(self.create_live_dashboard(), refresh_per_second=4, screen=True) as live:
                while operation_thread.is_alive() and self.status.status not in ["cancelled", "completed", "error"]:
                    # Check for keyboard input (non-blocking)
                    if sys.stdin.isatty():
                        if select.select([sys.stdin], [], [], 0.1)[0]:
                            try:
                                import termios
                                import tty
                                old_settings = termios.tcgetattr(sys.stdin)
                                tty.setcbreak(sys.stdin.fileno())
                                key = sys.stdin.read(1)
                                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                                
                                if key.lower() == 'q':
                                    self.status.cancel()
                                    self.cancelled = True
                                    break
                                elif key.lower() == 'p':
                                    if self.status.status == "running":
                                        self.status.status = "paused"
                                    elif self.status.status == "paused":
                                        self.status.status = "running"
                            except (ImportError, OSError, AttributeError):
                                # Fallback if termios not available (Windows, etc.)
                                pass
                    
                    live.update(self.create_live_dashboard())
                    time.sleep(0.25)
                
                # Final update
                live.update(self.create_live_dashboard())
        except KeyboardInterrupt:
            self.status.cancel()
            self.cancelled = True
        
        # Wait for operation to complete
        operation_thread.join(timeout=2)
        
        return self.status.status == "completed"
    
    def select_containers(self, containers: List[Dict]) -> Set[str]:
        """Interactive container selection."""
        self.console.print("\n[bold]Select Containers to Backup:[/bold]\n")
        
        # Create selection table
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("ID", style="dim", width=12)
        table.add_column("Name", style="cyan", width=30)
        table.add_column("Status", width=12)
        table.add_column("Image", style="dim", width=30)
        
        for i, container in enumerate(containers, 1):
            status_color = "green" if container["status"] == "running" else "yellow"
            table.add_row(
                str(i),
                container["name"],
                f"[{status_color}]{container['status']}[/{status_color}]",
                container["image"][:30],
            )
        
        self.console.print(table)
        
        # Get selection
        self.console.print("\n[dim]Enter container numbers (comma-separated) or 'all' for all containers:[/dim]")
        selection = Prompt.ask("Selection", default="all")
        
        if selection.lower() == "all":
            return {c["name"] for c in containers}
        
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(",")]
            selected = {containers[i]["name"] for i in indices if 0 <= i < len(containers)}
            return selected
        except (ValueError, IndexError):
            self.console.print("[red]Invalid selection, using all containers[/red]")
            return {c["name"] for c in containers}
    
    def select_backup_set(self) -> Optional[BackupSet]:
        """Select backup set from configuration."""
        if not self.config.backup_sets:
            return None
        
        self.console.print("\n[bold]Available Backup Sets:[/bold]\n")
        
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("Name", style="cyan", width=20)
        table.add_column("Description", width=40)
        table.add_column("Containers", style="dim", width=30)
        
        sets_list = list(self.config.backup_sets.values())
        for i, backup_set in enumerate(sets_list, 1):
            containers_str = ", ".join(backup_set.containers[:3])
            if len(backup_set.containers) > 3:
                containers_str += f" (+{len(backup_set.containers) - 3} more)"
            table.add_row(
                str(i),
                backup_set.description or backup_set.name,
                containers_str,
            )
        
        self.console.print(table)
        
        self.console.print("\n[dim]Select backup set number, or press Enter to skip:[/dim]")
        selection = Prompt.ask("Selection", default="")
        
        if not selection:
            return None
        
        try:
            index = int(selection.strip()) - 1
            if 0 <= index < len(sets_list):
                return sets_list[index]
        except ValueError:
            pass
        
        return None
    
    def select_scope(self) -> Dict[str, bool]:
        """Select backup scope."""
        self.console.print("\n[bold]Select Backup Scope:[/bold]\n")
        
        scope = {
            "containers": Confirm.ask("Backup container configurations?", default=True),
            "volumes": Confirm.ask("Backup data volumes?", default=True),
            "networks": Confirm.ask("Backup network configurations?", default=True),
            "configs": Confirm.ask("Backup container configs/metadata?", default=True),
        }
        
        return scope
    
    def show_backup_status(self, results: Dict, errors: List[str]):
        """Display backup results."""
        self.console.print("\n[bold]Backup Results:[/bold]\n")
        
        # Success summary
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
        
        table.add_row("Containers", str(containers_success), str(containers_failed))
        table.add_row("Volumes", str(volumes_success), str(volumes_failed))
        table.add_row("Networks", str(networks_success), str(networks_failed))
        
        self.console.print(table)
        
        # Errors
        if errors:
            self.console.print("\n[bold red]Errors:[/bold red]")
            for error in errors:
                self.console.print(f"  [red]•[/red] {error}")
