# Project plan

## Working title

Design and Implementation of a Secure Campus Lost-Property Claim and Collection System.

## Users and workflow

- Student: register, browse limited public listings, submit private claims, track their
  own claims, and obtain collection authorisation after approval.
- Property officer: record physically received items, review claims other than their own,
  and confirm an authorised handover.
- Administrator: officer capabilities plus account activation controls and the audit dashboard.

Item state: available -> reserved -> returned.
Claim state: pending -> approved -> collected, or pending -> rejected.
All state changes are server-side and cannot be selected in a browser form.

## First implementation

- Django server-rendered UI, SQLite local database, Django authentication and sessions.
- Separate public fields and encrypted private fields.
- Student ownership checks, staff checks, and no self-review or self-handover.
- Transactional approval and single-use, expiring collection authorisation.
- Role-scoped activity views, audit dashboard, and basic abuse throttling.
- Automated tests of security boundaries and legitimate workflows.

## Assessment mapping

| Brief requirement | Implementation and evidence to collect |
| --- | --- |
| Access levels | Registration, password hashing, session rotation, role/ownership checks; test cross-account requests |
| Input/output/errors | Server-side forms, ORM parameterisation, autoescaped templates, CSRF, generic error pages |
| Secure communication | Local Caddy/Waitress HTTPS, explicit project CA validation, secure cookies and redirect tests; public/browser trust remains separate |
| Data protection/education | Encrypted identifying details and proof, minimal public fields, privacy and usage guidance |
| Logging/analytics | Audit events, restricted dashboard, per-user history, failed-login and workflow-denial metrics |
| Security testing | 83 passing regression tests, 19 selected live HTTPS account checks, isolated backup/restore/rotation, dependency audit and reviewed Bandit findings; earlier ZAP/SSLyze evidence remains revision-specific |
| Host/network security | Private-profile ACLs, loopback listeners, authenticated backend, non-admin process and tested local recovery; dedicated service identity and off-device key/backup custody require the operator |

## Deliberately bounded scope

One campus, text evidence, staff judgement, and in-person handover. No real identity-document
uploads, image matching, payments, delivery, live university identity provider or hardware.

## Remaining milestones

1. Review and personalise this local implementation; record your decisions and contribution.
2. Local HTTPS and scoped host hardening are verified; choose and assess a real hosting environment if deployment is required.
3. Enrol the user's own staff authenticator, save recovery codes privately and choose separate off-device backup/key storage. These personal/operator steps cannot be supplied by code.
4. Extend the completed bounded assessment when new features, hosting or authentication controls are added.
5. Keep the existing report unchanged until the user supplies their further notes, then incorporate approved new evidence.
6. Complete the declarations, Canvas submission and viva preparation.

Report preparation follows [the writing guide](REPORT_WRITING_GUIDE.md) and
[the report plan](REPORT_PLAN.md), using the user's established academic writing preferences.

The brief calls this a group project; the student should verify acceptance of solo work.
No score or distinction is guaranteed by choosing this topic.
