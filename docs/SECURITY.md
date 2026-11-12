# Security design and evidence boundaries

Account MFA, saved-code recovery and offline backup/key maintenance are detailed in
[Account security and recovery](ACCOUNT_SECURITY_AND_RECOVERY.md), with current results
in `security-evidence/account-recovery/`. The earlier scanner evidence remains revision-specific.

## Trust model

The browser is untrusted. Roles, ownership, approval state and collection state come from
the server database. The application operator and host administrator remain trusted: this
prototype does not protect data against an operator who controls both the database and keys.

Students register themselves. Officer and administrator roles are provisioned locally through
`create_account`; browser registration cannot elevate a user. Officers can inspect claims
and identifying item details. Administrators additionally manage account activation and audit
views. No application endpoint edits or deletes audit records or changes account roles.

## Assets and controls

| Asset / threat | Implemented control | Evidence |
| --- | --- | --- |
| Public listing leaks withheld information | Separate public fields; no public serializer for private fields | Public page tests inspect response content |
| Claim disclosure across accounts | Ownership-scoped retrieval; staff role checks | Cross-account 404 test, role-denial tests |
| Login attacks | Django password hashing; persistent username/IP keyed rate counters; generic failures | Hash verification, rate-limit tests |
| Staff password compromise | Mandatory TOTP/recovery-code second factor; encrypted session-bound setup; consumed-counter rejection | Account-security tests including a real concurrent TOTP race; selected real HTTPS checks |
| Account lockout | Single-use high-entropy recovery-code digests; full reset invalidates other codes/sessions and cannot reactivate suspended users | Recovery, session invalidation and inactive-account tests |
| Session fixation or stale sessions | Django session rotation at login, logout invalidation, 30-minute idle cookie lifetime and 8-hour absolute ceiling | Session rotation/logout/age tests |
| Role escalation | Explicit registration allowlist and forced student role; CLI staff provisioning | Privileged field injection test |
| SQL injection | Django ORM queries with parameter binding; no raw SQL built from user inputs | Search injection regression test (limited scope) |
| XSS | Autoescaped quoted template values; no `safe`; no script execution permitted by CSP | Stored-script response test, CSP header assertion |
| CSRF | Django CSRF middleware and per-form tokens; state-changing routes require POST | Enforced-CSRF and GET-rejection tests |
| Private evidence at rest | `cryptography.fernet` authenticated encryption with a separately generated key | Encrypt/decrypt and tampering tests |
| Competing approvals | Transactional available-to-reserved update; unique winning-claim constraint | Competing claim and database constraint tests |
| Unauthorised collection | Claim-bound 192-bit random code, SHA-256 digest storage, 15-minute expiry | Ownership, expiry, wrong-claim, reissue and replay tests |
| Duplicate handover | Conditional token consumption and state changes in one SQLite IMMEDIATE transaction | Actual two-thread test on a file-backed test database |
| Misuse by property staff | No self-review or self-handover; evidence access audit events | Self-review and evidence-access tests |
| Inactive accounts | Authentication backend rejects deactivated users, including existing sessions | Existing-session deactivation test |
| Lost database/key mismatch | Authenticated independent-key snapshots containing matching database/key ring; restore into a new profile only | Wrong-key/tamper/no-overwrite tests and isolated real restore |
| Unsafe field-key retirement | Profile lease, verified pre-change backup, transactional rotation, primary-only verification before retirement | Failure rollback test, cross-process lease check and fresh-app decrypt checks |

No application audit event includes claim evidence, identifying item details, passwords,
email addresses or collection codes. It does include user references, action names, target
references, outcomes and timestamps. Database administrators can modify the audit table;
it is not a tamper-proof or independently verified audit service.

## Cryptographic choice

Use the high-level Fernet implementation rather than inventing a cipher construction.
Fernet uses AES-128-CBC with HMAC-SHA256 authentication and random IVs. This is authenticated
encryption, not AES-GCM or end-to-end encryption. The application can decrypt records during
authorised requests. Token metadata may expose encryption time. Passwords use Django's
password hashing API; collection codes have high entropy and are stored as SHA-256 digests.

The original HTTP demo keeps its database and keys under ignored `.local/`. The HTTPS
launcher uses a separate profile with private/data/TLS directories and an ACL limited to
the current Windows user and SYSTEM. This was verified on the isolated assessment profile.
The processes ran without an administrator token, although a dedicated service identity has
not been provisioned. A real deployment still requires protected backups and a documented
rotation/recovery process. Losing the matching field key loses access to encrypted records.
Setup never overwrites an existing key. The application now uses cryptography 50.0.2.

## SQLite concurrency boundary

The configured database uses IMMEDIATE transactions, so workflow transactions acquire the
SQLite write reservation before performing their decision reads. Each handover consumes an
unused/unexpired matching code using a conditional UPDATE, then changes the claim/item and
writes its audit event within the same transaction. A failure rolls back all of those writes.
This deliberately avoids relying on `select_for_update()`, which does not supply row locking
on SQLite. SQLite serialises writes and is a local prototype choice, not a high-load claim.

Do not switch database engines or transaction settings without reviewing and retesting these
assumptions. Current concurrency evidence applies to this SQLite configuration.

## Local HTTPS and remaining deployment work

Local preview uses HTTP bound to 127.0.0.1. `runserver --insecure` only serves static assets
with DEBUG disabled; it is not an HTTPS or production server. Real users must not enter real
personal data in this local demonstration.

`run-https.ps1` provides a tested Caddy/Waitress profile on loopback. TLS 1.2/1.3, certificate
validation against the explicit project CA, redirects, cookie flags, protected file ACLs and
proxy/Host manipulation were checked. The proxy's administration API is disabled. Direct
backend requests need an unlogged random credential, not just a forwarded protocol header.
The password minimum is fifteen characters. See [deployment instructions](DEPLOYMENT.md)
and [the separate assessment record](SECURITY_ASSESSMENT.md).

Windows/browser trust stores were not changed, so the local CA is not publicly or
automatically browser-trusted. All listeners remain on 127.0.0.1. The production settings
switch alone is still not a substitute for running the actual deployment profile.
Before deployment beyond this machine:

1. Configure a production WSGI server behind a trusted HTTPS reverse proxy with a valid certificate.
2. Set the actual `CLAIMSAFE_ALLOWED_HOSTS` and `CLAIMSAFE_CSRF_ORIGINS`.
3. Terminate HTTPS correctly. If using a forwarded-protocol setting, trust it only from a proxy
   that removes client-supplied forwarding headers. Do not simply enable it for arbitrary clients.
4. Collect and serve static assets through the web server; do not expose `.local`, `.git`,
   the SQLite database, source files, or private keys.
5. Restrict filesystem access and inbound ports; run the app with a dedicated least-privilege identity.
6. Run `manage.py check --deploy` in the actual deployment configuration and resolve findings.
7. Verify certificate hostname/trust/expiry, HTTPS redirection, cookie flags, TLS configuration
   and HTTP traffic behaviour with appropriate tools. Capture actual results.

## Known limitations / next assessment work

- No automated ownership verification. Officer judgement, insider honesty and physical checks remain necessary.
- No MFA, email verification, password-reset delivery, user-facing password change or notification email yet.
- Registration can reveal username/address availability. Throttling reduces but does not eliminate abuse.
- Fixed-window throttles can inconvenience legitimate users and do not provide distributed DDoS protection.
- Add periodic deletion of expired rate buckets and a researched, documented data-retention/deletion policy.
- No tamper-evident external log storage, alerting, backup restoration exercise or key rotation workflow yet.
- No upload handling; no claim of malware scanning or attachment security.
- A bounded manual request assessment, anonymous ZAP scan, TLS scan, static analysis and
  before/after installed-dependency audit have been completed. Their exact scope and findings
  are recorded separately; authenticated scanner coverage and exhaustive penetration testing
  have not been completed.
- Tests cover specified cases, not every possible injection payload, race or authorisation path.
- Privacy notice is a prototype notice; assess actual legal applicability before real processing.

## Authoritative references

- Django security: https://docs.djangoproject.com/en/5.2/topics/security/
- Django QuerySet / locking notes: https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update
- Django SQLite transactions: https://docs.djangoproject.com/en/5.2/ref/databases/#sqlite-notes
- Fernet specification and implementation: https://cryptography.io/en/latest/fernet/
- OWASP authorization: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
- OWASP business logic: https://cheatsheetseries.owasp.org/cheatsheets/Business_Logic_Security_Cheat_Sheet.html
- OWASP transaction authorization: https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html
