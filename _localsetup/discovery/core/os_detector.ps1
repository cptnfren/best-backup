# Localsetup v2 - OS detection. Thin wrapper; logic in os_detector.py.
# Output: os_type|os_version|architecture (same as os_detector.py).
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$EngineDir = (Get-Item (Join-Path $ScriptDir '..\..')).FullName
$py = Get-Command python3 -ErrorAction SilentlyContinue; if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
if (-not $py) { Write-Error 'python3 or python not found'; exit 1 }
& $py.Source (Join-Path $EngineDir 'discovery\core\os_detector.py')
exit $LASTEXITCODE
