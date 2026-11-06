# ClaimSafe demonstration and viva preparation

Use this to check your understanding, not as a script to memorise. Read each referenced
function and explain it in your own words. Do not claim independent work or understanding
you cannot demonstrate; the report acknowledges substantive AI help.

| Likely question | Explanation to understand | Where to look |
| --- | --- | --- |
| Why this application? | Public details help owners find belongings but can also help impostors. Withhold distinctive evidence and require staff review. | FoundItem fields; item form; public item template |
| Why is login not enough? | Authentication identifies the account. A role permits a kind of action; ownership restricts which claim a student can read. Check every request. | core/views.py scoped_claim; staff_only; admin_only |
| Why three different password/token protections? | Passwords use slow salted hashing. Evidence must be recoverable, so it is encrypted. High-entropy random collection/recovery codes can be stored as digests because originals need not be recovered. | settings password validators; core/crypto.py; services and account_security |
| What does MFA add? | A stolen password alone does not open staff records. TOTP is a second check, not proof against phishing. The account/version/counter update prevents reuse and stale proofs. | core/account_security.py verify_factor; core/middleware.py MFABoundaryMiddleware |
| What if the phone is lost? | Saved codes work once. Full recovery changes password, revokes codes, resets enrolment and invalidates sessions. A suspended account stays suspended. No saved code requires operator identity review. | recover_account; replace_recovery_codes |
| How are injection and XSS different? | SQL parameters keep data out of query syntax. HTML escaping prevents submitted markup becoming page structure. Validation alone does not replace either. | forms.py; home search; templates; CSP middleware |
| What does CSRF protect? | A different origin must not cause an authenticated browser to perform a state change without the required token/origin checks. It does not replace role checks. | Django CSRF middleware; POST views; enforced-CSRF tests |
| What is actually encrypted in transit? | Browser to Caddy uses TLS. The Caddy-to-Waitress HTTP hop stays on loopback on the same host and requires a proxy credential. A certificate needs client trust as well as encryption. | deploy/Caddyfile; config/proxy.py; serve_https_backend.py |
| Why can an item only be collected once? | The code must belong to an approved claim, match its digest, be unused and unexpired. Conditional consumption and custody/audit updates commit together. | core/services.py collect_item; database constraints |
| Why IMMEDIATE transactions? | SQLite does not provide SELECT FOR UPDATE row locking. Short IMMEDIATE transactions and conditional writes coordinate writers; the concurrent test examines two real connections. | settings DATABASES; concurrent tests |
| What did the scanners prove? | A bounded anonymous surface was scanned, not every authenticated route. Informational and static findings were reviewed. No known dependency advisory is time-specific and not a guarantee of complete safety. | security-evidence/zap.json; account-recovery/static-analysis.json; final dependency JSON |
| What is a dangerous restore assumption? | An old snapshot cannot contain later password changes, suspensions or physical returns. Restore revokes usable sessions/grants/codes, but an operator must reconcile later events. | scripts/manage_data.py restore; RESTORE_NOTES |
| Can the administrator secretly alter logs? | App routes restrict the audit interface, but an operator with database access can change the underlying records. An external protected sink is future work. | AuditEvent; audit_dashboard; report limitations |
| What was learned from actual failures? | Tests exposed SQLite handles left open and unexpected Windows directory grants. Explicit closing and ACL correction were verified. The Host fallback was also corrected and retested. | test_data_operations.py; manage_data.py protect; deployment notes |

Practise the normal workflow and one rejected request. Be able to identify the tested
application baseline, explain why screenshots are illustrations rather than complete tests,
and distinguish the current 83-test/19-request verification from the earlier ZAP/TLS run.
The screenshots use fictional records; they are not a real campus deployment or user study.
