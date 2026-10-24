$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
function Invoke-Checked { param([scriptblock]$Command); & $Command; if ($LASTEXITCODE -ne 0) { throw 'Setup command failed. See the output above.' } }
if (!(Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    Invoke-Checked { py -3.12 -m venv .venv }
}
Invoke-Checked { & '.venv/Scripts/python.exe' -m pip install -r requirements.lock }
Invoke-Checked { & '.venv/Scripts/python.exe' scripts/initialize.py }
Invoke-Checked { & '.venv/Scripts/python.exe' manage.py migrate --noinput }
Invoke-Checked { & '.venv/Scripts/python.exe' manage.py seed_demo }
Write-Host 'Ready. Run .\run.ps1. Demo credentials: .local/demo-accounts.txt'
