# ClaimSafe

A secure campus lost-property claim and collection application. Built as an original
6000CMD / 6005CEM coursework project, with a local Git history and evidence-led development.

Start with the [user manual](docs/USER_MANUAL.md) to set up the HTTPS demo and walk through a claim.

## The problem

An item must be discoverable without publishing the details someone could use to make a
false ownership claim. ClaimSafe separates public descriptions from private identifying
details, supports staff review, and enforces an approved, single-use collection process.

## Local development

Python 3.12 or newer is required. On Windows, from this directory:

```powershell
.\setup.ps1
.\run.ps1
```

Setup creates an isolated virtual environment, installs the locked dependencies, generates
local secrets, applies migrations, and creates fictional demonstration records. Visit
http://127.0.0.1:8000. This is a loopback-only development server, not a production deployment.

Generated demo usernames and passwords are saved to `.local/demo-accounts.txt` on this
machine only. Use the student, officer, and administrator accounts to explore different
permissions. No passwords or local records belong in Git. To create your own officer or
administrator without loading demo data, see `python manage.py create_account --help`.
Staff now require an authenticator. Use the HTTPS profile below for staff access and account
security; the HTTP developer profile cannot complete these HTTPS-only flows.

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check
```

See [project scope](docs/PROJECT_PLAN.md), [security design](docs/SECURITY.md),
[development log](docs/DEVELOPMENT_LOG.md), and [Git instructions](docs/VERSION_CONTROL.md).

## Local HTTPS

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-deploy.txt
.\run-https.ps1
```

This runs Caddy and Waitress at `https://localhost:8443`, with HTTP redirection on port 8080.
It uses its own protected state and fictional credentials under `.local/https/`; the earlier
demo is preserved. Client validation uses the generated local CA explicitly. Windows/browser
trust is not installed automatically, so ordinary browser trust still needs to be configured.
See [deployment instructions](docs/DEPLOYMENT.md) and [security assessment evidence](docs/SECURITY_ASSESSMENT.md).
The application, backend and proxy remain local; this does not publish the app.
See [account security, encrypted backups and key rotation](docs/ACCOUNT_SECURITY_AND_RECOVERY.md)
for authenticator enrolment, saved-code recovery and tested offline maintenance commands.

## Report draft

The full report source is in [docs/REPORT_DRAFT.md](docs/REPORT_DRAFT.md), with versioned
figures and an actual test summary in `docs/report-assets/`. The draft covers the assessed
HTTPS, staff MFA, backup recovery and key rotation implementation.

To regenerate the editable Word document with the optional report dependencies installed:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-report.txt
.\.venv\Scripts\python.exe scripts/build_report.py
```

This writes a DOCX, a Markdown copy and supporting figures to `.local/report/`.
On Windows with Microsoft Word installed, add `--export-pdf` to refresh the contents,
caption lists and page numbers and export a matching PDF from the saved DOCX.
The reviewed Word and PDF versions are stored in `docs/report/`.
See [report production notes](docs/REPORT_BUILD.md) for formatting and evidence details.
The source evidence and conclusions must be updated when implementation or verification changes.

## Academic ownership

This repository is an original implementation. Prior student submissions are reference
material only and must not be copied into it. Keep your own notes, understand and adapt
the implementation, and acknowledge AI assistance and external sources in the final
submission as required by the assignment. Tests and screenshots are evidence of only
the behaviours they actually exercise; they do not certify complete security.

## Current boundary

This is a local prototype with a verified local HTTPS profile and a bounded security
assessment. Public deployment, browser trust, a dedicated service identity and operational
controls such as off-device backup/key custody remain operator tasks. Mandatory staff MFA,
saved-code recovery, encrypted snapshot restoration and key rotation are implemented and
checked locally. See [the submission handoff](docs/SUBMISSION_HANDOFF.md) for the browser
demonstration, current screenshots and required submission materials.
