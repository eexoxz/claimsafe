# ClaimSafe

ClaimSafe is a campus lost-property application. Students browse found items and submit private claims. Property staff review claims and confirm collection using a single-use code.

## Run the demo

Follow the [user manual](docs/USER_MANUAL.md) to set up the local HTTPS site, sign in with the demo accounts and complete a handover.

## Development

From the repository folder in PowerShell 7, with Python 3.12 installed:

```powershell
.\setup.ps1
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

See the [deployment guide](docs/DEPLOYMENT.md) for Caddy and Waitress, the [security design](docs/SECURITY.md) for access controls, and the [security assessment](docs/SECURITY_ASSESSMENT.md) for test results.
