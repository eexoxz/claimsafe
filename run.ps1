$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$python = '.venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath '.local/secrets.json') -or !(Test-Path -LiteralPath $python)) {
    throw 'Run .\setup.ps1 first.'
}
& $python manage.py migrate --check
if ($LASTEXITCODE -ne 0) { throw 'The local database is not ready. Run .\setup.ps1 before starting ClaimSafe.' }
Write-Host 'ClaimSafe local prototype: http://127.0.0.1:8000'
Write-Host 'HTTP is for loopback development only. --insecure serves local static assets with DEBUG disabled.'
Write-Host 'Use .\run-https.ps1 for mandatory staff authenticator enrolment and account security.'
& $python manage.py runserver 127.0.0.1:8000 --insecure
exit $LASTEXITCODE
