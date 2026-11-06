# ClaimSafe submission handoff

The substantive report now covers the implemented app at aaf4b89 and the retained security
assessments, including fresh 30 October regression/dependency/account checks. The three
security reports guide its organisation. The FYP supplied only typography and layout.
The writing approach was checked directly with “Research human writing styles”: preserve
connected reasons, concrete explanations and appropriate qualifications. There is no abstract.

> The five screenshots were captured in the separate fictional walkthrough on 6 November
> and are in the active report in `Downloads\6005CEM`. Use the updated submission guide
> in that folder. The steps below document the original demo plan.

## Your remaining submission items

1. Read the report and verify your name, student ID and module details. Make sure you can
   explain the decisions and accurately identify your contribution and the AI assistance.
2. Confirm with the lecturer that your solo arrangement is accepted, if not already agreed.
   The current brief calls this a group project.
3. Supply the real Turnitin similarity-result screenshot and completed official Generative
   AI Declaration Form from your module/Canvas. The report's acknowledgement does not replace
   that form. Do not invent a result or sign someone else's declaration.
4. Complete the trusted-browser and authenticator steps below, practise the demo, and provide
   the five current app screenshots listed below. These replace/supplement the clearly dated
   initial interface captures; the technical results in the report are already available.
5. After the screenshots/declarations are integrated, check the final PDF and its word count,
   then submit through Canvas. PDF is preferred in the current brief. Check Canvas for any
   separately issued cover sheet or upload instructions.

No extra app features or public hosting are needed merely to complete the local demonstration.
Off-device backup/key custody and institutional operating policies are future operational
decisions; their absence is stated in the report. Push to your chosen GitHub repository
yourself when ready. Do not include .local, databases, passwords or keys.

## Start the normal demonstration profile

Open PowerShell in:

```text
C:\Users\USER\Documents\claimsafe
```

Run:

```powershell
.\run-https.ps1
```

Keep that terminal running. Open https://localhost:8443. This is the normal `.local/https`
profile, separate from the disposable assessment profile. Its fictional accounts are alex,
jamie, officer and admin. Their passwords are in:

```text
.local\https\demo-accounts.txt
```

Open that file privately; do not screenshot or upload it. Alex has a pending headphones
claim and an approved canvas laptop sleeve claim in a fresh demo. Existing demo states may
differ if you already completed a handover. Use another available fictional item if needed.

## Browser certificate trust

The walkthrough used a test client configured with the project CA and verified the
certificate and hostname on each HTTPS connection. Chrome rendered the verified
responses. There is no Windows certificate import step for the report evidence.
Ordinary browser trust remains separate from the local HTTPS checks.

## Enrol your own authenticator

Sign in as officer, confirm its current password and scan the setup QR into an authenticator
you control. Enter the current six-digit code. Save the recovery codes somewhere private
outside the browser. Repeat for admin because privileged accounts require MFA. Students
can remain password-only for the demonstration.

Do not send screenshots of setup QR codes, manual setup keys, passwords, current OTPs,
recovery-code lists, cookies or valid collection codes. The screenshots below avoid them.

## Screenshots to send

Use a desktop browser at a readable size, preferably around 1366x768 or wider. Include the
page title and relevant result; the address bar helps identify the local target. Use only
fictional records. Send the original PNG/JPG files with the names below if convenient.

| File | Account and location | What must be visible |
| --- | --- | --- |
| 01-public-listing.png | Signed out, https://localhost:8443/ | Public item listings with descriptions; no withheld identifying details |
| 02-mfa-challenge.png | officer, https://localhost:8443/account/verify/ | After enrolment, sign out and sign in again with password only. Capture “One more check” with the code field empty, before entering a code |
| 03-student-claim.png | alex, /dashboard/ then open an existing claim | Claim reference, state and the student's own fictional evidence. Capture before generating a collection code or after collection, so no usable code is shown |
| 04-completed-handover.png | officer, /desk/ then open the approved claim | Complete the fictional handover described below, then capture Collected status and confirmation with no code value displayed |
| 05-admin-audit.png | admin, https://localhost:8443/activity/ | Restricted audit dashboard, totals and event rows. Capture after the demo so the collection event is present |

The two historical screenshots already in the report are explicitly labelled as the
25 October initial walkthrough, not the final MFA interface. New images will be integrated
with accurate captions; no screenshot placeholders or invented screenshots are in the report.

## Short handover demonstration

1. In alex's My claims, open an approved claim such as the canvas laptop sleeve and generate
   its collection code. Keep the value private and do not screenshot it.
2. In a separate browser profile/window signed in as officer with MFA complete, open the same
   claim from Review desk. Enter the code, tick the claimant/physical-handover confirmation
   for this fictional exercise and submit.
3. Capture the resulting Collected page for screenshot 04. Reusing the authorisation must
   not produce a second completed handover. Do not claim that a real item changed hands.
4. Open the administrator audit and capture screenshot 05. Alex can also view the updated
   claim without being able to inspect another student's claims or administrator activity.

Use the code privately between your two fictional sessions. Do not upload it here. If the
example was already collected, record a new fictional item as officer, submit a claim as
alex, approve it as officer and repeat. Do not reset or overwrite the database just to
recreate the example.

See [Viva preparation](VIVA_PREPARATION.md) for the explanation prompts. After you send
the images and forms, a final integration pass remains.
