# Localsetup v2 - Deploy step. Thin wrapper; logic in deploy.py.
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$EngineDir = (Get-Item (Join-Path $ScriptDir '..')).FullName
$py = Get-Command python3 -ErrorAction SilentlyContinue; if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
if (-not $py) { Write-Host '[FAIL] python3 or python not found'; exit 1 }
& $py.Source (Join-Path $EngineDir 'tools\deploy.py') @args
exit $LASTEXITCODE
