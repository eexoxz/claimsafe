# Account security and recoverable local data

This work follows the local HTTPS assessment at commit `5339995`. New evidence is in
`security-evidence/account-recovery/`. Older evidence describes its recorded revision,
not the current account flows. The assignment report remains frozen.

## Use your own authenticator

Run `run-https.ps1` and use `https://localhost:8443` with explicit trust in its project CA.
Do not enter credentials through a certificate-warning bypass. Windows/browser trust
remains the operator's task; see `DEPLOYMENT.md`.

Officers and administrators must enrol an authenticator before opening application records.
After password sign-in, confirm the password, scan the locally generated QR code with an
authenticator you control, and enter its six-digit time-based code. Save the ten recovery
codes privately outside the browser. Students may enable the same factor under **Account
security**, or save recovery codes without enabling an authenticator. Existing local/demo
staff factors have deliberately not been enrolled on the user's behalf.

Setup lasts ten minutes and is bound to the browser session that started it. The database
holds encrypted setup secrets and a digest of the pending session handle. No external QR
service receives the secret. Each TOTP counter is accepted once, including concurrent
requests. The window is the current 30-second step and one step on either side. Wait for
a fresh code after consuming one. TOTP needs an accurate clock and is not phishing-resistant.

Recovery codes each contain 128 random bits and are stored as user-bound digests. They
appear only on the creation response. Replacing a set invalidates the old set and other
existing MFA proofs. Sensitive security changes need password confirmation and, where
enabled, a fresh factor. Passwords need at least fifteen characters. A password change
retains the current valid session and invalidates other sessions via Django's auth hash.

For a lost authenticator, use an unused recovery code at sign-in. To replace the device,
use **Recover account** with a saved code and new password. Full recovery invalidates all
saved codes, resets authenticator enrolment and invalidates password-authenticated sessions.
Staff must then enrol the replacement device. Recovery cannot reactivate a suspended account.
An email address alone never authorises a reset.

Setup, challenge and security changes are throttled per account and network. Validly formed
recovery requests share a completion response for unknown usernames, wrong codes and success.
Validation errors and timing are not claimed to be indistinguishable. No recovery email is
sent. If every saved code and device is lost, identity review requires an actual operator
policy; there is no unauthenticated reset backdoor.

Account pages require HTTPS, CSRF protection and `no-store` responses. Secrets, passwords
and submitted codes are excluded from application audit events. The original HTTP profile
remains available for development but cannot complete staff account-security flows.

## Encrypted backup

Stop the foreground server with Ctrl+C and stop other management commands for that profile.
The WSGI server and supported preparation/maintenance tools share a process-held lease.
This does not coordinate arbitrary SQLite editors, Django shells or unmodified commands.
In PowerShell, from the repo, choose new output filenames each time:

```powershell
.\.venv\Scripts\python.exe scripts/manage_data.py create-backup-key --output .local/backup-key.key
.\.venv\Scripts\python.exe scripts/manage_data.py backup --state .local/https --key-file .local/backup-key.key --output .local/snapshot-01.csb
```

The independent backup key authenticates/encrypts the database and matching Django, field
and proxy secrets together. SQLite's backup API builds a consistent in-memory snapshot;
no plaintext temporary database is written to disk. This does not control OS paging,
process memory or privileged administrators. The prototype refuses archives over 64 MiB,
existing outputs and mismatched/corrupt encrypted fields. It verifies the written archive
before rotation can proceed.

Created Windows files and restored profiles have current-user/SYSTEM ACLs. Changes are
scoped to created files/profiles, not arbitrary parent folders. Protect the destination
too. Copy the encrypted archive and independent key to separate secure off-device places
you control. Both on this laptop is only a local test, not disaster recovery. Losing the
backup key loses access to its snapshots.

## Restore into a new profile

```powershell
.\.venv\Scripts\python.exe scripts/manage_data.py restore --archive .local/snapshot-01.csb --key-file .local/backup-key.key --target .local/restored-demo
.\run-https.ps1 -ProfileName restored-demo -PrepareOnly
```

The destination must not exist. Authentication, checksum, SQLite integrity, foreign keys
and encrypted fields are checked before exposing the complete staged profile. A failed
staging write may leave a private `.restoring-*` directory for investigation, without
replacing an existing profile. Restore excludes the TLS CA, console demo password file
and app source. Keep the compatible source revision separately.

Restore clears sessions, collection grants, abuse counters and pending MFA setups, revokes
all saved recovery codes, advances MFA versions, and regenerates Django's signing key and
the proxy credential. Enrolled authenticators remain usable after the conservative counter
window passes (allow up to 90 seconds). Generate and save new recovery codes after sign-in.
Restored students without MFA need their known password or an operator identity review.

**Before reopening**, read `RESTORE_NOTES.txt`, review account/password/deactivation changes
since the snapshot, and reconcile later approvals and physical handovers. A snapshot cannot
know about later password changes, account suspension or physical events. Do not assume
those later changes survived. No demonstration records are added to a restored profile.
After reconciliation:

```powershell
.\run-https.ps1 -ProfileName restored-demo
```

The new profile creates its own TLS material: review client trust again. The old CA does
not automatically trust its new certificate. Only one profile can use these ports at once.
Names are restricted to short lowercase alphanumeric/hyphen names under `.local/`.

## Rotate and retire field keys

Stop the profile and use new backup filenames:

```powershell
.\.venv\Scripts\python.exe scripts/manage_data.py rotate --state .local/https --key-file .local/backup-key.key --backup-output .local/before-rotation.csb
.\.venv\Scripts\python.exe scripts/manage_data.py retire --state .local/https --key-file .local/backup-key.key --backup-output .local/before-retirement.csb
```

Both commands create and verify a new independent-key snapshot first. Rotation writes a
new primary plus retained fallback keys before rewriting all five encrypted field types in
an exclusive SQLite transaction. Failed verification rolls back record changes while keeping
keys able to read the original records. Fernet timestamps are preserved. The app writes with
the primary and reads with its key ring. Restart after key changes. Retirement first checks
that every current encrypted value decrypts using the primary alone. Historical snapshots
still hold their matching key rings; retirement is not erasure of snapshots or disk sectors.

This CLI supports standard file-backed profiles, including the original `.local/` layout.
It refuses environment-supplied field keys and does not coordinate profiles sharing database
or secret paths through arbitrary overrides. Direct profile links/junctions are refused;
trusted operator control of containing directories is assumed.

## Expired transient state

```powershell
.\.venv\Scripts\python.exe manage.py prune_security_state --dry-run
.\.venv\Scripts\python.exe manage.py prune_security_state
```

These use the profile selected by Django's environment. Only expired sessions/rate windows
and expired pending MFA setups are removed. Live factors, unused recovery codes, evidence,
claims and audit history remain. HTTPS preparation also runs cleanup. No scheduled task
or general personal-data deletion policy was invented.

References: [PyOTP](https://pyotp.readthedocs.io/en/stable/),
[Django password/session behaviour](https://docs.djangoproject.com/en/5.2/topics/auth/default/#session-invalidation-on-password-change),
[SQLite backup](https://sqlite.org/c3ref/backup_finish.html),
[Python SQLite backup API](https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.backup),
[Fernet/MultiFernet](https://cryptography.io/en/stable/fernet/).

## Reproduce the selected live checks

With the isolated audit dependencies already installed as described in
`SECURITY_ASSESSMENT.md`, run `run-https.ps1 -Assessment`. In another terminal:

```powershell
.\.venv\Scripts\python.exe security/prepare_fixture.py
.\.venv\Scripts\python.exe -c 'import sys,runpy; sys.path.append(".local/audit-venv/Lib/site-packages"); sys.path.insert(0,"security"); runpy.run_path("security/check_accounts.py",run_name="__main__")'
```

This enrols only new fictional `check_` accounts, keeps their credentials/factors/codes in
the ignored private assessment profile and prints a redacted result. It waits for a fresh
30-second TOTP step before testing replay. Prepare a new fixture before repeating it.
After stopping that assessment server, test restoration and rotation only on a new copy:

```powershell
.\.venv\Scripts\python.exe security/check_data_operations.py > .local/data-check-result.txt
```

The script prints only counts/checksums and the name of its newly restored private profile.
Its source assessment database/keys and original demo are checked for preservation.
`security/export_accounts.py` collects this phase's specific retained log filenames into
the separate evidence folder; inspect the results before exporting, and do not use the
earlier `export_evidence.py` to overwrite historical scanner results for this new build.
