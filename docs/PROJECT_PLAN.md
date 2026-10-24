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
| Secure communication | NEXT: HTTPS reverse proxy, trusted certificate, secure cookies, redirect and certificate tests |
| Data protection/education | Encrypted identifying details and proof, minimal public fields, privacy and usage guidance |
| Logging/analytics | Audit events, restricted dashboard, per-user history, failed-login and workflow-denial metrics |
| Security testing | Automated boundary tests; NEXT: manual proxy tests, automated application/dependency scans and retests |
| Host/network security | NEXT: restrict database access, least-privilege app account, secret ACLs, backup protection, firewall configuration |

## Deliberately bounded scope

One campus, text evidence, staff judgement, and in-person handover. No real identity-document
uploads, image matching, payments, delivery, live university identity provider or hardware.

## Remaining milestones

1. Review and personalise this local implementation; record your decisions and contribution.
2. Configure and test HTTPS and host hardening in a reproducible deployment environment.
3. Consider privileged-account MFA once the required baseline is stable.
4. Perform manual and automated vulnerability assessments; fix and retest findings.
5. Capture authentic evidence and write the 3,200-4,800-word report against the 2026 rubric.
6. Complete the declarations, Canvas submission and viva preparation.

The brief calls this a group project; the student should verify acceptance of solo work.
No score or distinction is guaranteed by choosing this topic.
