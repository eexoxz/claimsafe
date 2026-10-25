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
