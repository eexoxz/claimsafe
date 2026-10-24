# Local Git and GitHub

The repository is prepared locally on `main`. The intended GitHub account is `eexoxz`.
There is no GitHub repository or remote until the owner creates/selects one.

Create an empty repository named `claimsafe` under that account. Do not initialise it with
a separate README, licence or gitignore because this repository already has its own history.
Then, from this directory:

```powershell
git remote add origin https://github.com/eexoxz/claimsafe.git
git push -u origin main
```

Use that URL only if that is the repository you actually create. GitHub authentication is
handled by your normal Git credential manager or SSH configuration; never put a token in
the source code, remote URL, or screenshots.

For subsequent work:

```powershell
git status
git diff
git add <specific-files>
git commit -m "Describe the change and its purpose"
git push
```

Keep commits focused on meaningful changes. Database files, encryption keys, passwords,
virtual environments, prior students' reports and generated evidence are excluded.
Git history supports your development record; it does not replace your own explanations.
