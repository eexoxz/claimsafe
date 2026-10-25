$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (!(Test-Path -LiteralPath '.local/secrets.json')) { throw 'Run .\setup.ps1 first.' }
Write-Host 'ClaimSafe local prototype: http://127.0.0.1:8000'
Write-Host 'HTTP is for loopback development only. --insecure serves local static assets with DEBUG disabled.'
Write-Host 'Use .\run-https.ps1 for mandatory staff authenticator enrolment and account security.'
& '.venv/Scripts/python.exe' manage.py runserver 127.0.0.1:8000 --insecure
exit $LASTEXITCODE
