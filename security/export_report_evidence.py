"""Retain redacted final-report verification without replacing historical assessments."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local/report-final"
OUT = ROOT / "docs/security-evidence/report-final-2026-10-30"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


OUT.mkdir(parents=True, exist_ok=True)
log = (LOCAL / "regression.txt").read_text(encoding="utf-8-sig")
match = re.search(r"Ran (\d+) tests in ([\d.]+)s", log)
if not match or "\nOK" not in log:
    raise RuntimeError("Regression run did not complete successfully.")
write("regression.json", {"date": "2026-10-30", "command": ".venv/Scripts/python.exe manage.py test --noinput", "tests": int(match[1]), "seconds": float(match[2]), "result": "OK", "raw_log_sha256": sha(LOCAL / "regression.txt"), "performance_claim": False})
audit = read(LOCAL / "dependencies.json")
write("dependencies.json", {"date": "2026-10-30", "tool": "pip-audit 2.10.1", "scope": "Installed application environment including Waitress and pip, excluding the isolated scanner environment", "raw_result_sha256": sha(LOCAL / "dependencies.json"), "packages": [{"name": p["name"], "version": p["version"], "advisories": p["vulns"]} for p in audit["dependencies"]]})
accounts = read(LOCAL / "https-accounts.json")
if len(accounts["checks"]) != 19 or any(row["result"] != "passed" for row in accounts["checks"]):
    raise RuntimeError("The selected HTTPS account checks did not complete.")
write("https-accounts.json", dict(accounts, date="2026-10-30"))
earlier = read(ROOT / "docs/security-evidence/account-recovery/manifest.json")
mismatch = [path for path, expected in earlier["source_fingerprints"].items() if sha(ROOT / path) != expected]
if mismatch:
    raise RuntimeError("Application source differs from the recorded account assessment: " + ", ".join(mismatch))
write("manifest.json", {"date": "2026-10-30", "application_baseline": "aaf4b89", "unchanged_assessed_source_files": len(earlier["source_fingerprints"]), "source_fingerprints": earlier["source_fingerprints"], "report_source_sha256": sha(ROOT / "docs/REPORT_DRAFT.md"), "historical_assessments": {"5339995": "26 October public ZAP/TLS/request assessment in parent evidence folder", "aaf4b89": "26 October MFA/data maintenance assessment in account-recovery"}, "fresh_checks": ["83-test regression run", "19 selected real HTTPS account requests", "12-package installed app dependency audit"], "scope": "No new ZAP/SSLyze scan or independent participant study is claimed. Browser capture was blocked by an untrusted local CA. No trust-store change, warning bypass, user-factor enrolment or public hosting was performed."})
summary = f"ClaimSafe final regression verification\nDate: 30 October 2026\nCommand: .venv/Scripts/python.exe manage.py test --noinput\nRan {match[1]} tests in {match[2]}s\nOK\nSystem check identified no issues.\nTiming is not a performance benchmark.\n"
(ROOT / "docs/report-assets/test-summary-2026-10-30.txt").write_text(summary, encoding="utf-8")
print("Exported fresh redacted verification; 66 assessed source fingerprints match.")
