# ClaimSafe user manual

Use the fictional demo accounts to submit a lost-property claim, approve it and record the collection.

## Install and start

You need Windows x64, Git, PowerShell 7, Python 3.12 with the Windows Python launcher, Firefox, and a time-based authenticator app for the staff accounts. The first setup needs internet access.

Open **PowerShell 7** and run the commands below one at a time. If you already cloned ClaimSafe, open PowerShell in the `claimsafe` folder and start with `py -3.12 --version`.

```powershell
git clone https://github.com/eexoxz/claimsafe.git
cd claimsafe
py -3.12 --version
.\setup.ps1
.\.venv\Scripts\python.exe -m pip install -r requirements-deploy.txt
.\run-https.ps1
```

Check that the version command prints `Python 3.12.x`. When setup finishes and prints `Ready`, continue with the next command above. Leave PowerShell open when it prints `ClaimSafe HTTPS: https://localhost:8443`.

## Open the HTTPS site

Import the certificate once per checkout in a separate Firefox profile.

1. In Firefox, open `about:profiles`. Choose **Create a New Profile**, name it **ClaimSafe Demo**, then choose **Launch profile in new browser** for that profile.
2. In the new Firefox window, open **Settings** and search for `certificates`. Choose **View Certificates → Authorities → Import**.
3. Copy the full `root.crt` path printed after **Local CA** in PowerShell and paste it into the import file picker. The file is under `.local\https\tls\pki\authorities\local\root.crt` in the checkout. Tick **Trust this CA to identify websites** and select **OK**.
4. Type `https://localhost:8443/` into that Firefox window. The lost-property board should open.

## Sign in

Open the file printed after **Fictional credentials** in PowerShell. It is `.local\https\demo-accounts.txt` in the checkout. Use the password beside each username.

| Username | Role | Where to go |
| --- | --- | --- |
| `alex` | Student | **Find your belongings** or **My claims** |
| `officer` | Property officer | **Review desk** |
| `admin` | Administrator | **Security activity** |
| `jamie` | Second student | Optional check that Alex’s claim is private |

Keep `alex` in the regular Firefox demo window. Open a private window from the same demo profile for `officer`. Use that private window for `admin` after signing out as `officer`.

On the first sign-in as `officer` or `admin`, enter the **Current password** again and choose **Create setup key**. Scan the QR code with your authenticator, enter its six-digit code and select **Confirm authenticator**. Save the recovery codes privately and select **I have saved the codes**. On later sign-ins, enter a fresh six-digit code on the **One more check** screen.

## Walk through a claim

1. **Submit as `alex`.** Search the public board for **Pocket sketchbook** and open the item. Choose **I think this is mine**. In the evidence box, enter `Page six contains a drawing of three bicycles under an arch.` Tick the confirmation and choose **Submit private claim**. The claim should show **Under review**.
2. **Approve as `officer`.** In **Review desk**, open the **Pocket sketchbook** claim from `alex`. Compare the evidence with **Withheld item details**. Choose **Approve claim**, enter `The details match the withheld record. Please collect your item at the property desk.` and choose **Save review**. The status should change to **Ready to collect**.
3. **Generate the code as `alex`.** In **My claims**, open the same claim and choose **Generate collection code**. Copy the code while it is visible. It expires after 15 minutes, and generating another code replaces it.
4. **Confirm the handover as `officer`.** In **Review desk**, choose **Ready to collect**, click **Filter** and open the same claim. Paste the code into **Claimant’s collection code**. Tick the in-person identity and handover confirmation for this fictional demo and choose **Confirm handover**. The claim should now show **Collected**.
5. **Check the audit as `admin`.** Sign out as `officer`, sign in as `admin`, and open **Security activity**. Look for `collection.completed` in the **Audit trail**.

For the privacy check, copy Alex’s claim URL. Sign out of the private-window account, sign in as `jamie`, then open that URL. ClaimSafe should show its unavailable page without revealing the claim.

To stop ClaimSafe, return to the PowerShell window running it and press `Ctrl+C`.

## Troubleshooting

| What you see | What to check |
| --- | --- |
| `py -3.12` fails | Check that Python 3.12 and its Windows launcher are installed before running setup. |
| Firefox shows an untrusted certificate | Open the **ClaimSafe Demo** profile and import the `root.crt` printed by this checkout’s launcher. |
| `localhost:8443` will not open | Confirm `run-https.ps1` is still running. If the launcher reports a port in use, stop the earlier ClaimSafe session before starting another. |
| The sketchbook already has a claim | Use a different available item, or use **Review desk → Record found item** as the officer to create a new fictional item with identifying details you know. |

See the [deployment guide](DEPLOYMENT.md) for the local HTTPS configuration.
