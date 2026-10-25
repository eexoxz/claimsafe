# ClaimSafe

A secure campus lost-property claim and collection application. Built as an original
6000CMD / 6005CEM coursework project, with a local Git history and evidence-led development.

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

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py check
```

See [project scope](docs/PROJECT_PLAN.md), [security design](docs/SECURITY.md),
[development log](docs/DEVELOPMENT_LOG.md), and [Git instructions](docs/VERSION_CONTROL.md).

## Report draft

The full report source is in [docs/REPORT_DRAFT.md](docs/REPORT_DRAFT.md), with versioned
figures and an actual test summary in `docs/report-assets/`. The draft covers the verified
local implementation and explicitly identifies unfinished deployment and assessment work.

To regenerate the PDF on a machine with the optional report dependencies installed:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-report.txt
.\.venv\Scripts\python.exe scripts/build_report.py
```

This writes a PDF, an editable Markdown copy and supporting figures to `.local/report/`.
The PDF includes an automatically populated contents page. Its source evidence and conclusions
must be updated when the implementation or verification results change.

## Academic ownership

This repository is an original implementation. Prior student submissions are reference
material only and must not be copied into it. Keep your own notes, understand and adapt
the implementation, and acknowledge AI assistance and external sources in the final
submission as required by the assignment. Tests and screenshots are evidence of only
the behaviours they actually exercise; they do not certify complete security.

## Current boundary

This is a local prototype. HTTPS deployment, certificate validation, deployment hardening,
manual vulnerability assessment, automated scanning, and the coursework report must be
completed and evidenced before treating the assignment as finished. See the project plan.
