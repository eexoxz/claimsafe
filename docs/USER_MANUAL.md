# ClaimSafe user manual

ClaimSafe is a local campus lost-property demo. Use fictional items and ownership evidence throughout the walkthrough.

## Install and start

You need Windows x64, Git, PowerShell 7, Python 3.12, Firefox, and an authenticator app for the staff accounts. The first setup needs internet access.

Open PowerShell 7 and run these commands in order. If you already cloned the repository, open the `claimsafe` folder and start at `setup.ps1`.

```powershell
git clone https://github.com/eexoxz/claimsafe.git
cd claimsafe
.\setup.ps1
.\.venv\Scripts\python.exe -m pip install -r requirements-deploy.txt
.\run-https.ps1
```

Keep the PowerShell window open when it displays `ClaimSafe HTTPS: https://localhost:8443`. Press `Ctrl+C` in that window when you finish.

## Open ClaimSafe in Firefox

Complete these steps once for the demo Firefox profile and this checkout’s certificate.

1. In Firefox, open `about:profiles`, create a profile named **ClaimSafe Demo**, then select **Launch profile in new browser** for it.
2. In that window, open Firefox Settings and search for `certificates`. Select **View Certificates → Authorities → Import**.
3. In the `claimsafe` folder, select `.local\https\tls\pki\authorities\local\root.crt`. Tick **Trust this CA to identify websites** and choose **OK**. The launcher prints the full certificate path.
4. Type `https://localhost:8443/` in the demo Firefox window. The public lost-property board should appear.

## Sign in

Read the generated passwords from `.local\https\demo-accounts.txt` in your checkout. Keep them private.

| Account | Role | Where to go |
| --- | --- | --- |
| `alex` | Student | **Find your belongings**, then **My claims** |
| `jamie` | Second student | Use to check that Alex’s claim is private |
| `officer` | Property officer | **Review desk** |
| `admin` | Administrator | **Security activity** |

Use a regular window for `alex` and a private window from the same Firefox demo profile for `officer`. When first signing in as `officer` or `admin`, confirm the account password, scan the setup QR code with your authenticator and enter its six-digit code. Keep any recovery codes private.

## Walk through a claim

1. **Submit as Alex.** From the public board, open an available item and choose **I think this is mine**. Enter a fictional identifying detail, tick the confirmation and submit. Open the claim in **My claims**.
2. **Approve as the officer.** In **Review desk**, open Alex’s pending claim. Compare the evidence with the withheld item record, select **Approve claim**, enter a claimant-facing message and select **Save review**.
3. **Generate a collection code as Alex.** Reopen the approved claim in **My claims** and choose **Generate collection code**. The code is shown once and expires after 15 minutes. A replacement invalidates the previous code.
4. **Confirm the handover as the officer.** In **Review desk**, filter by **Ready to collect** and open the claim. Enter the code, tick the in-person identity and handover confirmation for the fictional demo, then select **Confirm handover**. The claim should show **Collected**.
5. **Check the audit as the administrator.** Sign out as the officer, sign in as `admin`, and open **Security activity** to find the completed collection event.

To check privacy, copy Alex’s claim URL and try it in a session signed in as `jamie`. ClaimSafe should show its unavailable page without exposing any claim details.

## Troubleshooting

| What you see | What to check |
| --- | --- |
| Firefox shows an untrusted certificate | Use the **ClaimSafe Demo** profile and import the `root.crt` printed by this checkout’s launcher. |
| `localhost:8443` will not open | Confirm `run-https.ps1` is still running. If a port is in use, stop the earlier ClaimSafe session before starting another. |
| The claim is already collected | Choose a different available item or record a new fictional item through **Review desk → Record found item**. |

See the [deployment notes](DEPLOYMENT.md) for the local HTTPS configuration.
