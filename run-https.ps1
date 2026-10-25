param([switch]$Assessment, [switch]$PrepareOnly)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
function Invoke-Checked { param([scriptblock]$Command); & $Command; if ($LASTEXITCODE -ne 0) { throw 'HTTPS setup failed. See the output above.' } }
if (!(Test-Path -LiteralPath '.venv/Scripts/python.exe')) { throw 'Run setup.ps1 first.' }
Invoke-Checked { & '.venv/Scripts/python.exe' -c 'import waitress' }
if ($env:CLAIMSAFE_PRODUCTION -eq '1') { throw 'Start this script from a shell without a pre-existing production setting.' }
$profileName = if ($Assessment) { 'https-assessment' } else { 'https' }
$stateDirectory = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".local\$profileName"))
$localRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '.local')) + [IO.Path]::DirectorySeparatorChar
if (!$stateDirectory.StartsWith($localRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'State directory is outside this checkout.' }
New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null
if ((Get-Item -LiteralPath $stateDirectory).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'State directory must not be a junction or symbolic link.' }
# Scope ACL changes to this profile directory, with no global account or firewall changes.
$ownerSid = [Security.Principal.WindowsIdentity]::GetCurrent().User
Invoke-Checked { & icacls.exe $stateDirectory /inheritance:r /grant:r "*$($ownerSid.Value):(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' }
$resultingAcl = Get-Acl -LiteralPath $stateDirectory
foreach ($rule in $resultingAcl.Access) {
    $ruleSid = $rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value
    if ($rule.AccessControlType -eq 'Allow' -and $ruleSid -notin @($ownerSid.Value,'S-1-5-18')) { throw 'Unexpected access remains on the profile directory; review its ACL.' }
}
foreach ($folder in @('private','data','logs','tls')) { New-Item -ItemType Directory -Path (Join-Path $stateDirectory $folder) -Force | Out-Null }
$environmentNames = @('CLAIMSAFE_STATE_DIR','CLAIMSAFE_SECRETS_FILE','CLAIMSAFE_DATABASE','CLAIMSAFE_PRODUCTION','CLAIMSAFE_ALLOWED_HOSTS','CLAIMSAFE_CSRF_ORIGINS','CLAIMSAFE_HSTS_SECONDS','CLAIMSAFE_TLS_STORAGE','CLAIMSAFE_STATIC_ROOT','CLAIMSAFE_PROXY_TOKEN')
$savedEnvironment = @{}
foreach ($name in $environmentNames) { $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$backendProcess = $null
try {
    $env:CLAIMSAFE_STATE_DIR = $stateDirectory
    $env:CLAIMSAFE_SECRETS_FILE = Join-Path $stateDirectory 'private\secrets.json'
    $env:CLAIMSAFE_DATABASE = Join-Path $stateDirectory 'data\claimsafe.sqlite3'
    Invoke-Checked { & '.venv/Scripts/python.exe' scripts/initialize.py --proxy-token }
    Invoke-Checked { & '.venv/Scripts/python.exe' manage.py migrate --noinput }
    if (!(Test-Path -LiteralPath (Join-Path $stateDirectory 'demo-accounts.txt'))) {
        Invoke-Checked { & '.venv/Scripts/python.exe' manage.py seed_demo }
    }
    Invoke-Checked { & '.venv/Scripts/python.exe' manage.py collectstatic --noinput }
    Invoke-Checked { & '.venv/Scripts/python.exe' scripts/install_caddy.py }
    $env:CLAIMSAFE_PRODUCTION = '1'
    $env:CLAIMSAFE_ALLOWED_HOSTS = 'localhost,127.0.0.1'
    $env:CLAIMSAFE_CSRF_ORIGINS = 'https://localhost:8443,https://127.0.0.1:8443'
    $env:CLAIMSAFE_HSTS_SECONDS = '3600'
    $env:CLAIMSAFE_TLS_STORAGE = (Join-Path $stateDirectory 'tls').Replace('\','/')
    $env:CLAIMSAFE_STATIC_ROOT = (Join-Path $PSScriptRoot 'staticfiles').Replace('\','/')
    $env:CLAIMSAFE_PROXY_TOKEN = (Get-Content -LiteralPath $env:CLAIMSAFE_SECRETS_FILE -Raw | ConvertFrom-Json).proxy_token
    Invoke-Checked { & '.venv/Scripts/python.exe' scripts/check_deployment.py }
    Invoke-Checked { & '.local/tools/caddy/caddy.exe' validate --config deploy/Caddyfile --adapter caddyfile }
    if ($PrepareOnly) { return }
    foreach ($port in @(8080,8443,9010)) {
        if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) { throw "Port $port is already in use. No existing process was stopped." }
    }
    $backendProcess = Start-Process -FilePath (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') -ArgumentList 'scripts/serve_https_backend.py' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $stateDirectory 'logs\backend.out.log') -RedirectStandardError (Join-Path $stateDirectory 'logs\backend.err.log')
    Write-Host 'ClaimSafe HTTPS: https://localhost:8443 (loopback only)'
    Write-Host "Local CA: $stateDirectory\tls\pki\authorities\local\root.crt"
    Write-Host 'No certificate was installed into Windows or browser trust stores.'
    Write-Host "Fictional credentials: $stateDirectory\demo-accounts.txt"
    Invoke-Checked { & '.local/tools/caddy/caddy.exe' run --config deploy/Caddyfile --adapter caddyfile }
} finally {
    if ($null -ne $backendProcess -and !$backendProcess.HasExited) { Stop-Process -Id $backendProcess.Id }
    foreach ($name in $environmentNames) { [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process') }
}
