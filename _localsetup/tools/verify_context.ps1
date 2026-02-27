# Localsetup v2 - Context verification. Thin wrapper; logic in verify_context.py.
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$EngineDir = (Get-Item (Join-Path $ScriptDir '..')).FullName
$py = Get-Command python3 -ErrorAction SilentlyContinue; if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
if (-not $py) { Write-Host '[FAIL] python3 or python not found'; exit 1 }
& $py.Source (Join-Path $EngineDir 'tools\verify_context.py')
exit $LASTEXITCODE
