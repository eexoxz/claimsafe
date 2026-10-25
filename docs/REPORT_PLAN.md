# Report plan

Working title: Design and Implementation of a Secure Campus Lost-Property Claim and
Collection System.

This proposed structure follows the 2026 coursework's emphasis on security design,
implementation, evaluation and evidence. It is not a lecturer-approved template. Follow
[the writing guide](REPORT_WRITING_GUIDE.md) when drafting.

## Proposed structure and word budget

Aim for approximately 4,000 words within the stated 3,200-4,800-word range. The following
budgets total 4,000 words. Confirm how references, captions, tables and appendices count;
do not assume they are excluded simply because an older report treated them that way.

| Section | Target words | Purpose |
| --- | ---: | --- |
| 1. Introduction and system overview | 350 | Establish the ownership/collection problem, users, environment, objectives and scope |
| 2. Security analysis and design | 900 | Analyse application-specific threats and justify the controls and trust boundaries |
| 3. Security implementation and testing | 1,850 | Explain actual code/configuration and evaluate it using authentic evidence |
| 4. Discussion and improvement | 650 | Evaluate effectiveness, challenges, remaining risks and prioritised improvements |
| 5. Summary | 250 | Address objectives and learning outcomes using findings already established |
| Total | 4,000 | Research and citations are integrated into the relevant explanations |

Provide references, required declarations and an appropriate appendix according to the
submission instructions. Research/report quality is assessed across the report, not through
an invented standalone section that consumes words without explaining ClaimSafe.

## 1. Introduction and system overview

Explain the conflict between discoverability and ownership fraud: enough information must
be public to find an item, while distinctive evidence should remain private. Introduce the
student, property officer and administrator roles, the local operating environment and the
staff-reviewed claim and collection workflow. State bounded objectives and the text-only,
single-campus scope. Do not imply a real university has deployed or endorsed the prototype.

## 2. Security analysis and design

Identify the assets, actors and trust boundaries, including the browser, application,
database, key material and physical handover. Explain the permission matrix and why students
must be restricted by ownership as well as role. Model the item and claim states and show
which transitions are permitted. Treat an authorised but dishonest user as a possible source
of abuse as well as an unauthenticated attacker.

Prioritise threats using justified likelihood and impact for this particular application.
Cover public disclosure, cross-account access, privilege escalation, login/session abuse,
injection, CSRF, leaked private records, unauthorised collection, repeated or concurrent
handover requests and incomplete logging. Explain control selection and tradeoffs using
primary sources. Include host/network risks and secure communication in the design.

Suggested figures are a small architecture/trust-boundary diagram, a permission matrix and
an item/claim state diagram. A threat table should link each risk to its control and planned
verification rather than reproduce a prior report's generic list or scores.

## 3. Security implementation and testing

Organise the explanation by related security responsibilities, with a few focused code or
configuration extracts. Cover account creation, authentication and sessions; role and ownership
enforcement; input/output/error handling; private-field protection; approval and collection;
logging, analytics and user education; and the deployed communication/host controls once
implemented. Describe what the framework supplies and how ClaimSafe uses it.

Integrate tests with the controls they assess, then provide a compact overview of the test
environment, manual assessment, automated tools, findings, fixes and retests. Record the code
version, tool versions, environment, steps, expected/observed outcomes and evidence references.
Use the OWASP edition expected by the module and identify it accurately. Do not substitute
an OWASP category checklist for testing.

The current source map is:

| Concern | Main source locations |
| --- | --- |
| Accounts, sessions, throttling and permissions | `core/forms.py`, `core/views.py`, `core/middleware.py`, `core/services.py`, `config/settings.py` |
| Claim ownership and staff access | `core/views.py`, `core/models.py`, `core/services.py` |
| Private evidence encryption | `core/crypto.py`, `scripts/initialize.py` and the encrypted model fields |
| Approval, unique winner and collection transaction | `core/services.py`, `core/models.py` and `core/migrations/0001_initial.py` |
| Template output and browser response protections | `templates/`, `core/middleware.py` |
| Audit events and restricted analytics | `core/models.py`, `core/services.py`, `core/views.py`, `templates/audit.html` |
| Existing automated evidence | `core/tests.py`, `docs/DEVELOPMENT_LOG.md` |

## 4. Discussion and improvement

Evaluate how the implementation addresses the original problem, including the usability
cost of keeping details private and requiring staff review. Discuss the limits of human
ownership assessment, operator trust, local key/database storage and audit integrity. Explain
the SQLite transaction choice and the boundary of the concurrency result. Discuss actual
implementation challenges rather than invented development history.

Prioritise improvements from the findings. Required HTTPS and host hardening should be
completed before the final assessment where possible; they must not be described as delivered
while still only planned. Other candidates include privileged-account MFA, safer account
recovery, external audit protection, alerting, retention/deletion procedures, backup recovery
and tested key rotation. Explain benefit and implementation impact rather than listing names.

## 5. Summary

Return to the stated objectives and assessed learning outcomes. Summarise the demonstrated
behaviour and its practical limits without introducing new controls, results or citations
that the report has not already discussed.

## Evidence readiness as of 2026-10-25

| Evidence area | Current state | Remaining work |
| --- | --- | --- |
| Local application and roles | Implemented and exercised | Review, personalise and identify final version |
| Automated boundary/workflow tests | Recorded run of 45 tests passed | Rerun against the final version and retain actual output |
| Fictional browser collection | Student code generation and officer handover exercised | Capture selected readable figures with test context |
| Desktop/mobile interface | Home layout inspected | Capture other relevant screens only where they support an explanation |
| HTTPS and certificate behaviour | Not deployed/verified | Configure, test and retain real results |
| Host and key protection | Local defaults and documented limits | Configure and evidence the chosen deployment protections |
| Manual security assessment | Not completed | Prepare and execute authorised application-specific cases |
| Automated web/dependency vulnerability assessment | Not completed | Run appropriate tools, assess findings, fix and retest |
| Privacy/legal reasoning | Prototype notice and limits documented | Research actual applicability and justify the proposed data practices |

Do not fill missing evidence with invented measurements or generic sample screenshots.
Keep private keys, passwords, valid collection codes and personal data out of figures and Git.
