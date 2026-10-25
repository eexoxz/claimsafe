# Local security assessment 26 October 2026

**Recorded scope:** the assessment below describes `5339995` and its historical manifest.
Later account security and recovery changes are documented in
[Account security and recovery](ACCOUNT_SECURITY_AND_RECOVERY.md) with separate evidence
under `security-evidence/account-recovery/`. References below to absent MFA/backup/rotation
describe that earlier revision. Do not treat its test count or hashes as the current build.

These are development evidence notes, separate from the frozen assignment report. The report
at 29b2bde has not been edited or regenerated. The new application source and evidence hashes
are recorded in `security-evidence/manifest.json`; the local commit identifies the completed
change. Tests used fictional records in an isolated HTTPS profile and did not alter the
earlier demonstration database.

## Scope and method

The assessment combined manual source/configuration review, individually selected HTTP
request manipulations, automated application regression tests, a Python dependency audit,
static analysis, a scoped anonymous web scan and a TLS scan. Request scripts supported the
exploration; they are not independent participant testing. This is a bounded local security
assessment, not a claim of a comprehensive penetration test, high-load validation or legal
compliance. The scanner did not authenticate as a student or officer. Private role/workflow
behaviour was checked through separate live requests and application tests.

The environment was Windows, Python 3.12.14, Django 5.2.18, cryptography 50.0.2, SQLite,
Waitress 3.0.2 and Caddy 2.11.7. Tools were pip-audit 2.10.1, Bandit 1.9.4, OWASP ZAP 2.17.0
and SSLyze 6.3.1. ZAP used a separate verified Temurin 21.0.12.1 runtime. Download sources and
checksums are retained in `security-evidence/tools.json`. Scanning tools are isolated from
the application's Python environment. Raw scan sessions, fixture credentials, keys and
collection codes remain outside Git in ignored local state.

## Findings and changes

| Finding | Decision and observed verification |
| --- | --- |
| No tested TLS endpoint | Added local Caddy TLS with explicit CA validation. TLS 1.2/1.3 succeed; SSL 2/3 and TLS 1.0/1.1 are rejected. Correct hostname verifies and a different hostname fails verification. |
| HTTP development server and broadly inherited state permissions | Added a loopback Waitress backend, authenticated proxy boundary, separated private/data/TLS directories and restricted profile ACLs. Verified only current user and SYSTEM have allow rules, and the processes lack an administrator token. |
| cryptography 46.0.7 had published advisories | Upgraded to 50.0.2. The initial full installed-environment audit returned seven advisory records representing four distinct advisories; three PYSEC IDs appeared twice. The follow-up audit examined nine packages with no known vulnerability results. |
| Twelve-character registration minimum | Raised the minimum to fifteen characters. Tests reject a complex fourteen-character password and accept a suitable fifteen-character one. Existing passwords and encrypted records were not rewritten. |
| Unexpected Host received an empty 200 from the proxy's unmatched route | Added explicit reject routes and unconditional application Host validation. Final HTTPS/HTTP requests with an unexpected Host receive 421; the direct Django regression receives 400. The original empty response did not disclose private content. |

The cryptography advisories concern PKCS7 decryption, certificate verification and bundled
OpenSSL. No direct exploit of ClaimSafe's Fernet operations was demonstrated. The upgrade
removes the known affected dependency rather than implying that the unused APIs had been
exploited. All six existing demo items and both existing claims still decrypted after the
upgrade. The [maintainer's changelog](https://cryptography.io/en/latest/changelog/) and the
advisory identifiers retained in the dependency evidence support the version decision.

During setup, a broad removal of forwarded headers caused HTTPS redirect loops. It was
replaced with specific header handling and retested. A strict SNI setting also rejected ZAP's
localhost client before useful scanning could occur. Explicit hostname routing now rejects
unserved hosts while supporting that client. Runs that returned 421 at the starting page or
failed to export reports were discarded; the recorded final automation plan succeeded with
200 at its expected starting page. These were configuration/debugging observations, not
successful vulnerability scans.

## Targeted live request observations

| Request manipulation | Observed result |
| --- | --- |
| Another student's session requests the owner's exact private claim ID | 404; private marker absent. Owner and authorised officer receive 200. |
| Student/officer opens system audit | Both receive 403; administrator receives 200. |
| Public registration supplies admin, staff and superuser fields | Account is still a student with both elevated flags false. |
| Officer review omits CSRF or supplies a foreign Origin with a valid token | 403 in both cases. Student review also receives 403. |
| Approved owner generates a code, then staff submit collection twice | Code response is no-store; first handover redirects successfully; replay receives 409. One completion event and a collected claim remain. |
| Login response cookie attributes | Session and CSRF use Secure, HttpOnly, SameSite=Lax, Path=/ and `__Host-` names. Logout GET receives 405. |
| Private evidence contains script markup | Claim submission succeeds; staff response encodes markup and retains script-src 'none'. |
| Search contains SQL-like text | Response is 200 and the item count is preserved. |
| Administrator deactivates an account with an existing session | Next protected request redirects to login. |
| Client changes forwarded protocol or address | Normal HTTPS remains 200; forged credentials sent directly to the backend receive 404. |
| Failed login uses a different forged address each time | The probe reaches 429 on its 22nd attempt after earlier requests in the same rate window. Changing the supplied address does not evade the shared network limit. |
| Requests for keys, Git metadata, source or static traversal/directory listing | All five inspected paths return 404. CSS returns 200 with a CSS content type and nosniff. |

Exact redacted outcomes, including the initial hostname observation and its retests, are in
`security-evidence/request-observations.json`. No secret code, cookie value or password is
included. The backend rejects requests before Django when the proxy credential is absent or
incorrect; forwarding headers alone do not grant access.

## Automated results and review

The Django runner completed **51 tests in 15.181 seconds**, all passing. This is a test-run
duration rather than a performance benchmark. The original workflow/concurrency cases remain,
with deployment boundary and password-policy regression cases added.

The final ZAP spider found **17 URLs**. Five selected active rules ran at low strength with
two threads and a three-minute maximum; the active phase completed in **25 seconds**, before
that limit. Rules covered SQL injection, reflected XSS, path traversal, CRLF injection and
external redirects. There were **no low, medium or high alerts**. Three informational alert
types were reviewed:

| ZAP ID | Review |
| --- | --- |
| 10015 Cache-control directives | Static assets are deliberately cacheable; sensitive dynamic and code responses were checked as no-store. |
| 10112 Session management response identified | Identifies cookie-bearing authentication responses; it does not establish a session weakness. |
| 10031 User-controllable HTML attribute | Search text is reflected inside an escaped value. A quote/autofocus/onfocus probe remained text and created neither injected attribute; CSP also disallows scripts. |

Bandit returned one medium finding, B310, at the Caddy downloader's `urlopen`. Manual review
found a constant HTTPS publisher URL and pinned SHA-512 verification before extraction and
execution. There is no user-supplied URL. This is retained as a reviewed false positive,
rather than suppressing the rule across the project or claiming the tool found nothing.

SSLyze rejected all attempted SSL 2/3 and TLS 1.0/1.1 suites. TLS 1.2 and 1.3 each accepted
three modern suites. Its compression, Heartbleed, CCS injection, ROBOT and renegotiation
checks did not identify the tested weaknesses. The supplied local CA validated the expected
chain; default public trust stores correctly did not trust it. No public Mozilla compliance
certification is claimed. The independent hostname verification used the received certificate
and the patched application's cryptography version.

## OWASP classification and coverage limits

The following uses the [OWASP Top 10 2025](https://top10.owasp.org/2025/) categories to organise
the evidence. It is not a checklist declaring an entire category eliminated.

| Category | Relevant evidence and remaining boundary |
| --- | --- |
| A01 Broken Access Control | Role, claim ownership, administrator access and proxy bypass checks. Staff remain broadly trusted within this single-campus design. |
| A02 Security Misconfiguration | Host rejection, private file ACLs, loopback listeners, cookie settings and deployment checks. A dedicated public deployment is still required. |
| A03 Software Supply Chain Failures | Before/after installed Python dependency audit; verified Caddy/ZAP/JRE downloads. This does not audit every operating-system component or all scanner dependencies. |
| A04 Cryptographic Failures | Validated TLS, protocol checks, encrypted-record compatibility and dependency upgrade. The local CA needs explicit client trust. |
| A05 Injection | ORM/input review, stored markup and query tests, selected active scanner rules and attribute-reflection review. Coverage is bounded by the inspected inputs and pages. |
| A06 Insecure Design | Approval and collection states, no self-review, replay and concurrent collection tests. Human ownership judgement remains necessary. |
| A07 Authentication Failures | Password policy, login throttling, session/cookie checks and deactivation. MFA and delivered account recovery remain absent. |
| A08 Software or Data Integrity Failures | Publisher download checksums and workflow transactions. Protected restoration and key rotation have not been exercised. |
| A09 Security Logging and Alerting Failures | Audit access restrictions and one completion event. No independent tamper-resistant log sink or operational alerting has been added. |
| A10 Mishandling of Exceptional Conditions | Generic errors, state failure/rollback tests and rejected inputs. Additional failure and resource-exhaustion assessment remains possible. |

## Reproduce and retain evidence

Install app deployment dependencies, then run `run-https.ps1 -Assessment`. Prepare new
fictional fixtures with `.venv/Scripts/python.exe security/prepare_fixture.py` in another
terminal. This command is restricted to the isolated profile and resets its test rate
windows; it preserves audit history and the original demo database. It writes credentials
privately. `security/live_client.py` supplies TLS-validated clients for individually selected
request probes; its `observe` function records only the observations explicitly supplied.

For example, from a Python session using the isolated audit environment:

```python
import sys
sys.path.insert(0, 'security')
from live_client import client, fixture, get
other = client('other')
response = get(other, '/claims/' + fixture()['pending_claim'] + '/')
print(response.status_code)  # expected 404
```

Create `.local/audit-venv` and install `requirements-audit.lock` for the recorded scanner
environment. Audit the **installed application path**, not just the wrapper requirements file:

```powershell
.\.local\audit-venv\Scripts\python.exe -m pip_audit --path .venv/Lib/site-packages --cache-dir .local/audit-cache --format json --output .local/app-audit.json
.\.local\audit-venv\Scripts\python.exe -m bandit -r core config scripts/initialize.py scripts/serve_https_backend.py scripts/check_deployment.py scripts/install_caddy.py -x core/tests.py,core/test_deployment.py -f json -o .local/bandit.json
.\.venv\Scripts\python.exe manage.py test --noinput
```

An initial `--disable-pip --no-deps` invocation against the nested requirements wrapper
examined only Waitress, so it was rejected as insufficient. The retained before/after audits
both examine nine installed packages. Always inspect the audited inventory as well as the
tool's exit status.

After obtaining the verified ZAP/JRE packages described in `security-evidence/tools.json`,
the recorded ZAP command is:

```powershell
& '.local/tools/jre/jdk-21.0.12.1+1-jre/bin/java.exe' -jar '.local/tools/zap/ZAP_2.17.0/zap-2.17.0.jar' -dir '.local/zap-home' -port 8090 -host 127.0.0.1 -cmd -silent -notel -autorun security/zap.yaml
```

The YAML scope is this local app, without authenticated scanner users. Raw public scan
reports are under `.local/zap-results/`. Redacted summaries and source hashes are versioned
under `docs/security-evidence/`; `security/export_evidence.py` exports them using the app
interpreter. The collector expects the recorded filenames and separately captured host ACL
observations. An assessment should be reviewed before replacing those evidence files.

Public hosting, browser trust installation, a dedicated service identity, MFA, protected
backup recovery, rotation, retention/deletion and independent audit protection remain future
work. No GitHub push or public deployment was performed. The assignment report remains frozen.
