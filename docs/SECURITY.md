# Security design and evidence boundaries

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

The database and keys are under ignored `.local/` for easy local development. This excludes
them from Git but does not establish strong separation on the host. On Windows, the operator
must review ACLs before any sensitive use. Production requires a separate protected key
location or secret manager, protected backups, and a documented rotation/recovery process.
Losing the matching field key loses access to encrypted records. Setup never overwrites it.

## SQLite concurrency boundary

The configured database uses IMMEDIATE transactions, so workflow transactions acquire the
SQLite write reservation before performing their decision reads. Each handover consumes an
unused/unexpired matching code using a conditional UPDATE, then changes the claim/item and
writes its audit event within the same transaction. A failure rolls back all of those writes.
This deliberately avoids relying on `select_for_update()`, which does not supply row locking
on SQLite. SQLite serialises writes and is a local prototype choice, not a high-load claim.

Do not switch database engines or transaction settings without reviewing and retesting these
assumptions. Current concurrency evidence applies to this SQLite configuration.

## Deployment still required

Local preview uses HTTP bound to 127.0.0.1. `runserver --insecure` only serves static assets
with DEBUG disabled; it is not an HTTPS or production server. Real users must not enter real
personal data in this local demonstration.

`CLAIMSAFE_PRODUCTION=1` enables HTTPS redirects, Secure cookies and HSTS. These switches
alone do not configure a certificate, TLS termination, or a production process manager.
Before deployment:

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
- No manual proxy assessment, full automated web scan or dependency-vulnerability audit has been completed yet.
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

Consult the primary sources and cite the claims actually used in the final report.
