# Development log

## 2026-10-25 - Scope and foundation

- Selected an original campus lost-property claim and collection workflow.
- Planned public/private item data separation and a staff-reviewed ownership process.
- Chose Django 5.2 LTS for a small, explainable server-rendered application with framework
  authentication, CSRF protection, ORM queries and template escaping.
- Chose SQLite for the initial local prototype. Collection authorisation must use conditional
  writes inside a transaction, rather than relying on SQLite row-lock functionality.
- Prepared a dedicated local repository and excluded runtime data and secrets.

## 2026-10-25 - First functional local version

- Implemented student registration, secure sessions, staff provisioning and role-based workspaces.
- Implemented public listings, encrypted identifying details/evidence, staff review, collection
  authorisation, audit events, and account activation controls.
- Added a 15-minute, claim-bound, single-use code with digest-only storage and transactional handover.
- Added a responsive interface with original category illustrations and no external scripts/fonts.
- Recorded dependency versions in `requirements.lock`; `pip check` reports no broken dependencies.
- Django system checks pass, and `makemigrations --check --dry-run` reports no pending schema changes.
- Ran 45 automated tests successfully (14.239 seconds on this machine), including two actual
  simultaneous collection requests against a file-backed SQLite test database. One succeeds,
  one is denied, and one completed-handover event is recorded.
- Browser-verified student/officer/administrator sign-in, private claim display, a fictional
  laptop-sleeve handover, and the audit dashboard. Checked the home layout at desktop size
  and at a 390-pixel mobile viewport; reset the viewport afterwards.
- Refined privileged login landing pages, preserved denied account-change audit events, and
  prevented IP-throttled requests from allocating additional username rate buckets.
- Development server was bound only to loopback for QA. HTTPS, real certificate validation,
  deployment hardening and full vulnerability assessment remain outstanding.

## Assistance and evidence

### 2026-10-25 report draft

Prepared the full security report against the 2026 rubric using the established writing
preferences. The main report contains approximately 3,630 words; its source including
references and appendices contains approximately 4,205 words. The rendered PDF has 15 pages,
four figures and three tables. The bibliography includes primary security documentation,
NIST guidance and a foundational academic paper on protection principles.

The report evidence baseline is d1086b5. A fresh run of all 45 tests passed in 12.129 seconds.
That is a test-run duration, not an application performance measurement. The actual summary
is retained in `docs/report-assets/test-summary.txt`. The report does not invent TLS, scan,
user-study or real-campus results. It identifies the twelve-character password setting as
a gap against NIST's single-factor password-length guidance.

The report source, figures and optional PDF builder are versioned. The application code
was not changed while preparing the report. Remaining coursework evidence and submission
attachments are identified in the draft.

Codex (OpenAI) assisted with planning, implementation, tests, documentation and local UI QA.
The student must review the code, personalise the decisions, understand the security rules,
and acknowledge assistance according to the assignment's Generative AI declaration.
No prior student report, code, diagram, test result or screenshot was copied into the repository.

### 2026-10-26 formal report revision

Revised the report after the user supplied their own FYP document as a presentation and
writing reference. The coursework retains five security chapters, now numbered with their
subsections. The body uses Times New Roman 12 pt, 1.5 line spacing, justified text, A4 pages
and one-inch margins. An abstract, updated contents, caption lists and Roman/Arabic page
numbering provide the formal assignment structure. Reworked 22 substantive paragraphs,
reduced repeated qualifications, and separated submission guidance from report content.
The factual AI acknowledgement remains in the report.

The reviewed report has 21 pages, four figures and three tables. Its main text is approximately
3,888 words; the complete Markdown source is approximately 4,550 words under the same token
counting method. These counts describe the files rather than deciding the module's counting
rules. The PDF was exported directly from the saved DOCX using Microsoft Word, including live
contents and caption-field refresh. All 21 pages were inspected as 140 dpi images. After the
final code-line wrapping, pages 1-20 were pixel-identical and page 21 was reviewed again.
The original FYP reference remained byte-for-byte unchanged. Checks found no old tourism
content, unresolved fields or incorrect extra table caption in the delivered report.

All 45 application tests passed again in 20.056 seconds on 26 October, using the separate
SQLite test database. The rerun summary is recorded separately from the previous day's run.
No application features were changed for this revision. The report continues to distinguish
regression tests and fictional browser evidence from the outstanding HTTPS deployment,
host hardening and complete manual/automated vulnerability assessment.

Versioned Word and PDF copies are under `docs/report/`; text, sanitised template and builder
remain editable in the repository. Production instructions and submission reminders are in
`REPORT_BUILD.md`, outside the formal report. Local version control only; no remote push.

### 2026-10-26 local HTTPS and security assessment

The user authorised application security work and explicitly froze further report changes.
Added a Caddy 2.11.7 / Waitress 3.0.2 profile, private current-user/SYSTEM state ACLs, loopback
listeners, a credential-protected WSGI boundary, explicit Host rejection and Secure/HttpOnly
`__Host-` cookies. The app uses a separate database and key file in the HTTPS profile. No
Windows/browser CA installation, public hosting, firewall change or service-account creation
was performed. Process checks confirmed a non-administrator token.

The initial full installed-environment dependency audit found seven advisory records in
cryptography 46.0.7, representing four distinct advisories. Upgraded it to 50.0.2 and verified
all six original demo items and both original claims could still be decrypted. The repeated
audit examined nine installed packages with no known vulnerability results. Raised the new
password minimum from twelve to fifteen characters and aligned CLI guidance.

Reviewed configuration/source and individually manipulated live HTTPS requests for ownership,
role boundaries, registration privilege fields, CSRF/origin, stored markup, SQL-like search,
session deactivation, collection replay, headers, private file paths and forwarding-based
throttle bypass. Corrected a setup redirect loop and an empty success response on unknown
hosts; final unknown-host requests receive 421. Failed/incomplete scanner runs were discarded.

The final ZAP automation plan succeeded, discovered 17 URLs, and completed five selected
active rules in 25 seconds. No low/medium/high alerts; three informational types were reviewed.
Bandit returned one reviewed B310 false positive on the fixed HTTPS/checksummed downloader.
SSLyze confirmed TLS 1.2/1.3, rejected SSL 2/3 and TLS 1.0/1.1, and did not identify the
specified legacy TLS weaknesses. Project-CA trust and hostname rejection were checked
independently; default public stores intentionally do not trust this local CA.

All 51 automated application tests passed in 15.181 seconds. New tests cover the authenticated
backend boundary, credential removal before app/error logging, Host rejection and password
length. This timing is not a performance benchmark. Technical notes and redacted evidence are
under `docs/DEPLOYMENT.md`, `docs/SECURITY_ASSESSMENT.md` and `docs/security-evidence/`.
The report sources, builders, assets and reviewed Word/PDF are unchanged from 29b2bde.

### 2026-10-26 account security and offline recovery

Continued the user's authorised application work while preserving the report freeze. Added
mandatory officer/administrator TOTP, optional student enrolment, locally generated QR codes,
encrypted/browser-bound ten-minute pending setup, single-use counter updates and saved
128-bit recovery codes stored as digests. Account password changes and saved-code recovery
invalidate older sessions; full recovery resets the factor and remaining codes without
reactivating suspended accounts. Security views require HTTPS and CSRF protection, have
account/network throttles, and exclude secrets from audit events. Real operator/demo factors
remain unenrolled for the user to add with their own authenticator.

Added offline independent-key encrypted snapshots, non-overwriting restoration, transactional
MultiFernet rotation and verified fallback retirement. WSGI/preparation/maintenance share a
profile lease. Restoration revokes sessions, collection grants, saved recovery codes and
pending enrolments, regenerates signing/proxy secrets and requires operator reconciliation
of later account/custody changes. Added expired transient-state pruning and named HTTPS
profiles without seeding restored data. Windows testing exposed unclosed SQLite connections
and explicit directory ACL grants; corrected both and reran affected checks.

All 83 regression tests passed in 39.206 seconds. Nineteen selected real HTTPS account checks
passed with project-CA/hostname validation. An isolated real snapshot verified 24 encrypted
values; rotation and retirement preserved their decrypted content after fresh app starts.
Source database/keys stayed unchanged and the original six items/two claims still decrypted.
The normal HTTPS profile was prepared and four public pages returned 200/no-store under
validated TLS. Twelve installed app packages had no known pip-audit advisories. Bandit's
twelve retained findings were reviewed: empty reset values, fixed/no-shell offline process
calls, and the earlier fixed HTTPS/checksummed downloader. No ZAP/SSLyze rerun or independent
user study is claimed for this phase. Redacted evidence is separate from the older assessment.

Windows/browser trust, the user's authenticator enrolment, off-device backup/key custody,
operator identity/retention decisions and any public institutional hosting remain user-owned
steps. Report files/builders/exports retain their frozen revision. Local commit only; no push.

### 2026-10-29 report style and format correction

The user clarified that the supplied reports should guide ordinary academic prose and
report formatting, with no brochure or workbook headings. Revised the cover to a plain
report title, adopted conventional `1.0`/`1.1` section numbering and subject headings,
simplified the introductory prose and access-control explanation, and placed implementation
extracts and the AI acknowledgement under the numbered appendix. Retained the established
A4/Times New Roman/1.5 spacing, captions, references and paragraph-based discussion.

This is a presentation revision of the existing d1086b5/45-test report baseline, not an
update to incorporate the subsequent HTTPS/MFA/backup work. No sample text or findings
were copied. Word automation initially failed against its cached Office interface; switching
the exporter to late-bound calls allowed the same saved DOCX to export correctly. The
matching 21-page Word/PDF pair was rendered and every page inspected, with contents and
caption/page fields updated. The main source count is approximately 3,852 words. Updated
the working report copies and retained this limited style authorisation in the writing guide.

The user further clarified that the three security samples govern content organisation and
explanation, while the FYP supplies only font, justification and neat layout. Checked all
three supplied security PDFs for an abstract heading; none was found. Removed the abstract
from the source and builder, refreshed the contents/preliminary numbering and exported the
matching 20-page Word/PDF pair. Main-report text and its technical evidence remain unchanged.
