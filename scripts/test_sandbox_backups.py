#!/usr/bin/env python3
"""
Comprehensive Backup Testing Script for Sandbox

Tests various backup scenarios using the sandbox filesystem and logs
all issues, errors, and observations for debugging.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

console = Console()


class BackupTester:
    """Test backup operations and log issues."""
    
    def __init__(self, sandbox_path: str = "/tmp/bbackup_sandbox"):
        self.sandbox_path = Path(sandbox_path)
        self.test_results = []
        self.issues = []
        self.test_volume = "test_sandbox_volume"
        self.test_container = "test_sandbox_container"
        self.backup_staging = Path("/tmp/bbackup_test_staging")
        self.backup_staging.mkdir(parents=True, exist_ok=True)
        
    def log_issue(self, test_name: str, severity: str, issue: str, context: Dict[str, Any]):
        """Log an issue with context."""
        issue_entry = {
            'test': test_name,
            'severity': severity,  # error, warning, info
            'issue': issue,
            'context': context,
            'timestamp': datetime.now().isoformat(),
        }
        self.issues.append(issue_entry)
        console.print(f"[{'red' if severity == 'error' else 'yellow' if severity == 'warning' else 'blue'}]{severity.upper()}[/{severity == 'error' and 'red' or severity == 'warning' and 'yellow' or 'blue'}]: [{test_name}] {issue}")
    
    def log_result(self, test_name: str, success: bool, details: Dict[str, Any]):
        """Log test result."""
        result = {
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat(),
        }
        self.test_results.append(result)
    
    def run_command(self, cmd: List[str], capture_output: bool = True) -> tuple[bool, str, str]:
        """Run a command and return success, stdout, stderr."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                timeout=300,
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out after 300 seconds"
        except Exception as e:
            return False, "", str(e)
    
    def setup_test_environment(self) -> bool:
        """Set up Docker volume with sandbox data."""
        console.print("\n[bold cyan]Setting up test environment...[/bold cyan]")
        
        # Check if sandbox exists
        if not self.sandbox_path.exists():
            self.log_issue(
                "setup",
                "error",
                f"Sandbox not found at {self.sandbox_path}",
                {'sandbox_path': str(self.sandbox_path)}
            )
            return False
        
        # Check Docker
        success, stdout, stderr = self.run_command(["docker", "--version"])
        if not success:
            self.log_issue(
                "setup",
                "error",
                "Docker not available",
                {'stderr': stderr}
            )
            return False
        
        # Remove existing test volume if exists
        self.run_command(["docker", "volume", "rm", self.test_volume], capture_output=False)
        
        # Create test volume
        success, stdout, stderr = self.run_command(["docker", "volume", "create", self.test_volume])
        if not success:
            self.log_issue(
                "setup",
                "error",
                "Failed to create Docker volume",
                {'stderr': stderr}
            )
            return False
        
        # Copy sandbox data to volume
        console.print(f"Copying sandbox data to Docker volume...")
        copy_cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.sandbox_path}:/source:ro",
            "-v", f"{self.test_volume}:/data",
            "alpine",
            "sh", "-c", "cp -r /source/* /data/ && ls -la /data | head -20"
        ]
        success, stdout, stderr = self.run_command(copy_cmd)
        if not success:
            self.log_issue(
                "setup",
                "error",
                "Failed to copy sandbox data to volume",
                {'stderr': stderr, 'stdout': stdout}
            )
            return False
        
        # Create a test container with the volume
        self.run_command(["docker", "rm", "-f", self.test_container], capture_output=False)
        success, stdout, stderr = self.run_command([
            "docker", "run", "-d",
            "--name", self.test_container,
            "-v", f"{self.test_volume}:/data",
            "alpine", "sleep", "3600"
        ])
        if not success:
            self.log_issue(
                "setup",
                "error",
                "Failed to create test container",
                {'stderr': stderr}
            )
            return False
        
        console.print("[green]✓ Test environment ready[/green]")
        return True
    
    def test_full_backup(self) -> bool:
        """Test full backup (containers + volumes + networks)."""
        console.print("\n[bold cyan]Test 1: Full Backup[/bold cyan]")
        test_name = "full_backup"
        
        try:
            # Run backup command
            cmd = [
                "python3", "-m", "bbackup.cli",
                "backup",
                "--containers", self.test_container,
                "--no-interactive",
            ]
            
            success, stdout, stderr = self.run_command(cmd)
            
            context = {
                'command': ' '.join(cmd),
                'stdout': stdout[:1000] if stdout else '',
                'stderr': stderr[:1000] if stderr else '',
                'returncode': 0 if success else 1,
            }
            
            if not success:
                self.log_issue(
                    test_name,
                    "error",
                    "Full backup failed",
                    context
                )
                self.log_result(test_name, False, context)
                return False
            
            # Check if backup directory was created
            backup_dirs = list(self.backup_staging.glob("backup_*"))
            if not backup_dirs:
                self.log_issue(
                    test_name,
                    "error",
                    "No backup directory created",
                    context
                )
                self.log_result(test_name, False, context)
                return False
            
            # Analyze backup contents
            backup_dir = backup_dirs[-1]
            context['backup_dir'] = str(backup_dir)
            context['backup_size'] = sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())
            
            # Check for expected files
            expected_dirs = ['containers', 'volumes', 'networks']
            missing_dirs = [d for d in expected_dirs if not (backup_dir / d).exists()]
            if missing_dirs:
                self.log_issue(
                    test_name,
                    "warning",
                    f"Missing backup directories: {missing_dirs}",
                    context
                )
            
            self.log_result(test_name, True, context)
            return True
            
        except Exception as e:
            self.log_issue(
                test_name,
                "error",
                f"Exception during full backup: {str(e)}",
                {'exception': str(e), 'type': type(e).__name__}
            )
            self.log_result(test_name, False, {'exception': str(e)})
            return False
    
    def test_volumes_only_backup(self) -> bool:
        """Test volumes-only backup."""
        console.print("\n[bold cyan]Test 2: Volumes-Only Backup[/bold cyan]")
        test_name = "volumes_only_backup"
        
        try:
            cmd = [
                "python3", "-m", "bbackup.cli",
                "backup",
                "--containers", self.test_container,
                "--volumes-only",
                "--no-interactive",
            ]
            
            success, stdout, stderr = self.run_command(cmd)
            
            context = {
                'command': ' '.join(cmd),
                'stdout': stdout[:1000] if stdout else '',
                'stderr': stderr[:1000] if stderr else '',
            }
            
            if not success:
                self.log_issue(
                    test_name,
                    "error",
                    "Volumes-only backup failed",
                    context
                )
                self.log_result(test_name, False, context)
                return False
            
            # Check backup contents
            backup_dirs = list(self.backup_staging.glob("backup_*"))
            if backup_dirs:
                backup_dir = backup_dirs[-1]
                has_volumes = (backup_dir / "volumes").exists()
                has_containers = (backup_dir / "containers").exists()
                
                if has_containers:
                    self.log_issue(
                        test_name,
                        "warning",
                        "Backup contains containers directory despite --volumes-only",
                        context
                    )
                
                if not has_volumes:
                    self.log_issue(
                        test_name,
                        "error",
                        "Backup missing volumes directory",
                        context
                    )
                    self.log_result(test_name, False, context)
                    return False
            
            self.log_result(test_name, True, context)
            return True
            
        except Exception as e:
            self.log_issue(
                test_name,
                "error",
                f"Exception during volumes-only backup: {str(e)}",
                {'exception': str(e)}
            )
            self.log_result(test_name, False, {'exception': str(e)})
            return False
    
    def test_config_only_backup(self) -> bool:
        """Test config-only backup."""
        console.print("\n[bold cyan]Test 3: Config-Only Backup[/bold cyan]")
        test_name = "config_only_backup"
        
        try:
            cmd = [
                "python3", "-m", "bbackup.cli",
                "backup",
                "--containers", self.test_container,
                "--config-only",
                "--no-interactive",
            ]
            
            success, stdout, stderr = self.run_command(cmd)
            
            context = {
                'command': ' '.join(cmd),
                'stdout': stdout[:1000] if stdout else '',
                'stderr': stderr[:1000] if stderr else '',
            }
            
            if not success:
                self.log_issue(
                    test_name,
                    "error",
                    "Config-only backup failed",
                    context
                )
                self.log_result(test_name, False, context)
                return False
            
            # Check backup contents
            backup_dirs = list(self.backup_staging.glob("backup_*"))
            if backup_dirs:
                backup_dir = backup_dirs[-1]
                has_volumes = (backup_dir / "volumes").exists()
                has_containers = (backup_dir / "containers").exists()
                
                if has_volumes:
                    self.log_issue(
                        test_name,
                        "warning",
                        "Backup contains volumes directory despite --config-only",
                        context
                    )
                
                if not has_containers:
                    self.log_issue(
                        test_name,
                        "error",
                        "Backup missing containers directory",
                        context
                    )
                    self.log_result(test_name, False, context)
                    return False
            
            self.log_result(test_name, True, context)
            return True
            
        except Exception as e:
            self.log_issue(
                test_name,
                "error",
                f"Exception during config-only backup: {str(e)}",
                {'exception': str(e)}
            )
            self.log_result(test_name, False, {'exception': str(e)})
            return False
    
    def test_incremental_backup(self) -> bool:
        """Test incremental backup."""
        console.print("\n[bold cyan]Test 4: Incremental Backup[/bold cyan]")
        test_name = "incremental_backup"
        
        try:
            # First backup
            cmd1 = [
                "python3", "-m", "bbackup.cli",
                "backup",
                "--containers", self.test_container,
                "--volumes-only",
                "--incremental",
                "--no-interactive",
            ]
            
            success1, stdout1, stderr1 = self.run_command(cmd1)
            
            if not success1:
                self.log_issue(
                    test_name,
                    "error",
                    "First incremental backup failed",
                    {'stdout': stdout1[:500], 'stderr': stderr1[:500]}
                )
                self.log_result(test_name, False, {'first_backup_failed': True})
                return False
            
            # Modify a file in the volume
            modify_cmd = [
                "docker", "exec", self.test_container,
                "sh", "-c", "echo 'test modification' >> /data/test_modification.txt"
            ]
            self.run_command(modify_cmd)
            
            # Second backup (should be incremental)
            cmd2 = [
                "python3", "-m", "bbackup.cli",
                "backup",
                "--containers", self.test_container,
                "--volumes-only",
                "--incremental",
                "--no-interactive",
            ]
            
            success2, stdout2, stderr2 = self.run_command(cmd2)
            
            context = {
                'first_backup': {'stdout': stdout1[:500], 'stderr': stderr1[:500]},
                'second_backup': {'stdout': stdout2[:500], 'stderr': stderr2[:500]},
            }
            
            if not success2:
                self.log_issue(
                    test_name,
                    "error",
                    "Second incremental backup failed",
                    context
                )
                self.log_result(test_name, False, context)
                return False
            
            # Check if incremental backup used --link-dest
            if 'link-dest' not in stdout2.lower() and 'link-dest' not in stderr2.lower():
                self.log_issue(
                    test_name,
                    "warning",
                    "Incremental backup may not be using --link-dest",
                    context
                )
            
            # Compare backup sizes (incremental should be smaller)
            backup_dirs = sorted(self.backup_staging.glob("backup_*"), key=lambda x: x.stat().st_mtime)
            if len(backup_dirs) >= 2:
                first_size = sum(f.stat().st_size for f in backup_dirs[-2].rglob('*') if f.is_file())
                second_size = sum(f.stat().st_size for f in backup_dirs[-1].rglob('*') if f.is_file())
                context['first_backup_size'] = first_size
                context['second_backup_size'] = second_size
                context['size_reduction'] = ((first_size - second_size) / first_size * 100) if first_size > 0 else 0
                
                if second_size >= first_size:
                    self.log_issue(
                        test_name,
                        "warning",
                        f"Incremental backup size ({second_size}) not smaller than first ({first_size})",
                        context
                    )
            
            self.log_result(test_name, True, context)
            return True
            
        except Exception as e:
            self.log_issue(
                test_name,
                "error",
                f"Exception during incremental backup: {str(e)}",
                {'exception': str(e)}
            )
            self.log_result(test_name, False, {'exception': str(e)})
            return False
    
    def test_backup_with_encryption(self) -> bool:
        """Test backup with encryption."""
        console.print("\n[bold cyan]Test 5: Backup with Encryption[/bold cyan]")
        test_name = "encrypted_backup"
        
        try:
            # Check if encryption is configured
            config_path = Path.home() / ".config" / "bbackup" / "config.yaml"
            if not config_path.exists():
                self.log_issue(
                    test_name,
                    "info",
                    "Config file not found, skipping encryption test",
                    {'config_path': str(config_path)}
                )
                self.log_result(test_name, False, {'skipped': True, 'reason': 'no_config'})
                return False
            
            # Check if encryption is enabled in config
            import yaml
            with open(config_path) as f:
                config = yaml.safe_load(f)
            
            encryption_enabled = config.get('encryption', {}).get('enabled', False)
            if not encryption_enabled:
                self.log_issue(
                    test_name,
                    "info",
                    "Encryption not enabled in config, skipping test",
                    {}
                )
                self.log_result(test_name, False, {'skipped': True, 'reason': 'encryption_disabled'})
                return False
            
            # Run encrypted backup
            cmd = [
                "python3", "-m", "bbackup.cli",
                "backup",
                "--containers", self.test_container,
                "--volumes-only",
                "--no-interactive",
            ]
            
            success, stdout, stderr = self.run_command(cmd)
            
            context = {
                'command': ' '.join(cmd),
                'stdout': stdout[:1000] if stdout else '',
                'stderr': stderr[:1000] if stderr else '',
            }
            
            if not success:
                self.log_issue(
                    test_name,
                    "error",
                    "Encrypted backup failed",
                    context
                )
                self.log_result(test_name, False, context)
                return False
            
            # Check if encrypted files exist
            backup_dirs = list(self.backup_staging.glob("backup_*"))
            if backup_dirs:
                backup_dir = backup_dirs[-1]
                # Look for encrypted files or encryption metadata
                encrypted_files = list(backup_dir.rglob("*.encrypted"))
                encryption_metadata = list(backup_dir.rglob("*encryption*"))
                
                context['encrypted_files_found'] = len(encrypted_files)
                context['encryption_metadata_found'] = len(encryption_metadata)
                
                if not encrypted_files and not encryption_metadata:
                    self.log_issue(
                        test_name,
                        "warning",
                        "No encrypted files or encryption metadata found",
                        context
                    )
            
            self.log_result(test_name, True, context)
            return True
            
        except Exception as e:
            self.log_issue(
                test_name,
                "error",
                f"Exception during encrypted backup: {str(e)}",
                {'exception': str(e)}
            )
            self.log_result(test_name, False, {'exception': str(e)})
            return False
    
    def test_restore_operation(self) -> bool:
        """Test restore operation."""
        console.print("\n[bold cyan]Test 6: Restore Operation[/bold cyan]")
        test_name = "restore_operation"
        
        try:
            # Find latest backup
            backup_dirs = sorted(self.backup_staging.glob("backup_*"), key=lambda x: x.stat().st_mtime)
            if not backup_dirs:
                self.log_issue(
                    test_name,
                    "error",
                    "No backups found for restore test",
                    {}
                )
                self.log_result(test_name, False, {'reason': 'no_backups'})
                return False
            
            latest_backup = backup_dirs[-1]
            
            # Create restore destination
            restore_dest = Path("/tmp/bbackup_restore_test")
            restore_dest.mkdir(parents=True, exist_ok=True)
            
            # Run restore
            cmd = [
                "python3", "-m", "bbackup.cli",
                "restore",
                "--backup-path", str(latest_backup),
                "--volumes", f"{self.test_volume}_restored",
                "--no-interactive",
            ]
            
            success, stdout, stderr = self.run_command(cmd)
            
            context = {
                'command': ' '.join(cmd),
                'backup_path': str(latest_backup),
                'stdout': stdout[:1000] if stdout else '',
                'stderr': stderr[:1000] if stderr else '',
            }
            
            if not success:
                self.log_issue(
                    test_name,
                    "error",
                    "Restore operation failed",
                    context
                )
                self.log_result(test_name, False, context)
                return False
            
            # Verify restore
            # Check if restored volume exists
            success, stdout, stderr = self.run_command(["docker", "volume", "ls"])
            if f"{self.test_volume}_restored" not in stdout:
                self.log_issue(
                    test_name,
                    "warning",
                    "Restored volume not found",
                    context
                )
            
            self.log_result(test_name, True, context)
            return True
            
        except Exception as e:
            self.log_issue(
                test_name,
                "error",
                f"Exception during restore: {str(e)}",
                {'exception': str(e)}
            )
            self.log_result(test_name, False, {'exception': str(e)})
            return False
    
    def cleanup(self):
        """Clean up test environment."""
        console.print("\n[bold cyan]Cleaning up test environment...[/bold cyan]")
        
        # Remove test container
        self.run_command(["docker", "rm", "-f", self.test_container], capture_output=False)
        
        # Remove test volume
        self.run_command(["docker", "volume", "rm", self.test_volume], capture_output=False)
        
        console.print("[green]✓ Cleanup complete[/green]")
    
    def generate_report(self) -> str:
        """Generate comprehensive test report."""
        report_path = Path("/tmp/bbackup_test_report.json")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'sandbox_path': str(self.sandbox_path),
            'test_results': self.test_results,
            'issues': self.issues,
            'summary': {
                'total_tests': len(self.test_results),
                'passed_tests': sum(1 for r in self.test_results if r['success']),
                'failed_tests': sum(1 for r in self.test_results if not r['success']),
                'total_issues': len(self.issues),
                'errors': sum(1 for i in self.issues if i['severity'] == 'error'),
                'warnings': sum(1 for i in self.issues if i['severity'] == 'warning'),
                'info': sum(1 for i in self.issues if i['severity'] == 'info'),
            }
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return str(report_path)
    
    def display_summary(self):
        """Display test summary."""
        console.print("\n" + "=" * 70)
        console.print("[bold cyan]BACKUP TEST SUMMARY[/bold cyan]")
        console.print("=" * 70)
        
        # Test results table
        table = Table(title="Test Results", box=box.ROUNDED)
        table.add_column("Test", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="yellow")
        
        for result in self.test_results:
            status = "[green]✓ PASS[/green]" if result['success'] else "[red]✗ FAIL[/red]"
            details = str(result['details'].get('exception', 'N/A'))[:50] if not result['success'] else "OK"
            table.add_row(result['test'], status, details)
        
        console.print(table)
        
        # Issues summary
        if self.issues:
            console.print("\n[bold yellow]Issues Found:[/bold yellow]")
            for issue in self.issues:
                severity_color = {
                    'error': 'red',
                    'warning': 'yellow',
                    'info': 'blue',
                }.get(issue['severity'], 'white')
                
                console.print(f"[{severity_color}]{issue['severity'].upper()}[/{severity_color}]: [{issue['test']}] {issue['issue']}")
        
        # Summary stats
        summary = {
            'total_tests': len(self.test_results),
            'passed': sum(1 for r in self.test_results if r['success']),
            'failed': sum(1 for r in self.test_results if not r['success']),
            'errors': sum(1 for i in self.issues if i['severity'] == 'error'),
            'warnings': sum(1 for i in self.issues if i['severity'] == 'warning'),
        }
        
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Tests: {summary['total_tests']} total, {summary['passed']} passed, {summary['failed']} failed")
        console.print(f"  Issues: {summary['errors']} errors, {summary['warnings']} warnings")
        console.print("=" * 70)


def main():
    """Run all backup tests."""
    console.print("[bold cyan]bbackup Sandbox Backup Testing[/bold cyan]")
    console.print("=" * 70)
    
    tester = BackupTester()
    
    try:
        # Setup
        if not tester.setup_test_environment():
            console.print("[red]Failed to setup test environment[/red]")
            return 1
        
        # Run tests
        tests = [
            tester.test_full_backup,
            tester.test_volumes_only_backup,
            tester.test_config_only_backup,
            tester.test_incremental_backup,
            tester.test_backup_with_encryption,
            tester.test_restore_operation,
        ]
        
        for test_func in tests:
            try:
                test_func()
            except Exception as e:
                console.print(f"[red]Test {test_func.__name__} crashed: {e}[/red]")
        
        # Generate report
        report_path = tester.generate_report()
        console.print(f"\n[green]Test report saved to: {report_path}[/green]")
        
        # Display summary
        tester.display_summary()
        
        return 0
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Tests interrupted by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        return 1
    finally:
        tester.cleanup()


if __name__ == "__main__":
    sys.exit(main())
