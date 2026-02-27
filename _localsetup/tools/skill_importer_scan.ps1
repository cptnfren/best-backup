# Localsetup v2 - Scan directory for Agent Skills. Thin wrapper; logic in skill_importer_scan.py.
param([string]$Path = '')
if (-not $Path) { Write-Error 'Usage: .\skill_importer_scan.ps1 -Path <directory>'; exit 1 }
if (-not (Test-Path -LiteralPath $Path -PathType Container)) { Write-Error "Not a directory: $Path"; exit 1 }
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$EngineDir = (Get-Item (Join-Path $ScriptDir '..')).FullName
$py = Get-Command python3 -ErrorAction SilentlyContinue; if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
if (-not $py) { Write-Host '[FAIL] python3 or python not found'; exit 1 }
& $py.Source (Join-Path $EngineDir 'tools\skill_importer_scan.py') $Path
exit $LASTEXITCODE
