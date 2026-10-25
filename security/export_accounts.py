"""Export this phase's redacted evidence without replacing the earlier assessment."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
OUT = ROOT / "docs/security-evidence/account-recovery"
OUT.mkdir(parents=True, exist_ok=True)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


log = (LOCAL / "final-account-tests.txt").read_text(encoding="utf-8-sig")
match = re.search(r"Ran (\d+) tests in ([\d.]+)s", log)
if not match or "\nOK" not in log:
    raise ValueError("No completed successful regression result")
write("regression.json", {"command": ".venv/Scripts/python.exe manage.py test --noinput", "tests": int(match[1]), "seconds": float(match[2]), "result": "OK", "raw_log_sha256": digest(LOCAL / "final-account-tests.txt"), "performance_claim": False})

audit = read(LOCAL / "account-app-audit.json")
write("dependencies.json", {"tool": "pip-audit 2.10.1", "scope": "12 installed app packages including Waitress and pip, excluding isolated scanner environment", "raw_result_sha256": digest(LOCAL / "account-app-audit.json"), "packages": [{"name": p["name"], "version": p["version"], "advisories": p["vulns"]} for p in audit["dependencies"]]})

checks = read(LOCAL / "https-assessment/private/account-checks.json")
write("https-accounts.json", checks)
operations_lines = (LOCAL / "data-check-result.txt").read_text(encoding="utf-8-sig").splitlines()
write("data-operations.json", json.loads(operations_lines[0]))

bandit = read(LOCAL / "account-bandit-final.json")
write("static-analysis.json", {"tool": "Bandit 1.9.4", "scope": "core and config excluding tests; initializer, WSGI runner, deployment checks, downloader, data maintenance and profile preparation. Frozen report builders excluded.", "raw_result_sha256": digest(LOCAL / "account-bandit-final.json"), "findings": [{k: f[k] for k in ["test_id", "issue_severity", "issue_confidence", "filename", "line_number", "issue_text"]} for f in bandit["results"]], "review": {"B310": "Fixed publisher HTTPS URL with pinned SHA-512 verification in the Caddy downloader, reviewed in the earlier assessment.", "B105/B106": "Empty strings clearing/resetting authenticator setup fields and local display variables, not hardcoded usable secrets.", "B404/B603": "Reviewed offline tools: shell=False, fixed System32 whoami/icacls paths with explicit argv, and current sys.executable with fixed project preparation commands. No request-controlled executable or shell string. CLI paths are operator-selected local paths. These generic subprocess findings are retained rather than globally suppressed."}})

paths = []
for folder in ["config", "core", "templates", "static"]:
    paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and p.suffix in {".py", ".html", ".css"})
paths.extend(ROOT / value for value in ["requirements.txt", "requirements.lock", "requirements-deploy.txt", "run-https.ps1", "run.ps1", "deploy/Caddyfile", "scripts/initialize.py", "scripts/serve_https_backend.py", "scripts/check_deployment.py", "scripts/install_caddy.py", "scripts/manage_data.py", "scripts/prepare_profile.py", "security/live_client.py", "security/check_accounts.py", "security/check_data_operations.py", "security/export_accounts.py"])
write("manifest.json", {"recorded_utc": datetime.now(timezone.utc).isoformat(), "baseline_commit": "5339995", "source_fingerprints": {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(paths)}, "scope": "Current source and selected account/recovery checks. This phase did not rerun the old ZAP or SSLyze scan, which remains evidence for its recorded revision. New endpoints were checked through HTTPS requests and Django tests. No independent usability study, public hosting, browser trust installation or off-device storage claim.", "normal_profile_smoke": {"tls_validation": "Python ssl project-CA validation, hostname and validity", "get_200_no_store": ["/", "/login/", "/account/recover/", "/privacy/"]}, "restored_launcher": "run-https.ps1 -ProfileName restore-check-8562d026fa -PrepareOnly passed deployment checks with the two documented localhost HSTS exceptions; no demo seed inserted", "report": "Frozen at 29b2bde; no report sources, builders or exports changed"})
print("Exported redacted account/recovery evidence; private credentials, factors, codes, databases and archives were excluded.")
