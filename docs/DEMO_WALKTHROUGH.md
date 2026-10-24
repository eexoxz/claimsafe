# Demonstration walkthrough

Use only fictional records. Generated accounts are listed in `.local/demo-accounts.txt`.
Each browser session has one active account. Use two browser profiles or sign out between roles.

1. Visit the board while signed out. Search and filter listings. Public pages never show
   the staff identifying record or anyone's ownership evidence.
2. Sign in as `alex`. The initial demo has a pending headphones claim and an approved
   laptop-sleeve claim. Browser QA may already have collected the sleeve; the pending claim
   remains available for demonstrating staff review.
3. As `officer`, open Review desk. Read and assess the pending claim, then approve it with
   a claimant-facing message that does not reveal private identifying details.
4. Sign back in as `alex`, open the approved claim, and generate a collection code.
   Copy it while it is displayed. It expires after 15 minutes; a replacement invalidates the old code.
5. Sign in as `officer`, filter Ready to collect, open the claim, enter the code, and confirm
   the fictional in-person handover. The state changes to Collected and the item becomes Returned.
6. Sign in as `admin` to inspect security activity and manage account activation.
7. To exercise privacy boundaries, use `jamie` to attempt to open Alex's exact claim URL.
   It must return the generic unavailable-page response without private evidence.

For a fresh manual scenario, record a new fictional item as an officer and submit a claim
as a student. The seed command is intentionally idempotent and will not reset existing cases.
Automated tests use their own disposable database and do not reset or modify the demo database.

Do not invent test results or label the generated sample records as real campus cases.
