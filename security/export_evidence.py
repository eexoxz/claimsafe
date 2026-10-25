"""Export selected redacted observations; raw sessions and credentials stay ignored."""
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
OUT = ROOT / "docs/security-evidence"
OUT.mkdir(parents=True, exist_ok=True)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def audit(path):
    data = read(path)
    return {"raw_result_sha256": digest(path), "packages_examined": len(data["dependencies"]),
            "packages": [{"name": p["name"], "version": p["version"], "advisories": [
                {"id": v["id"], "aliases": v.get("aliases", []), "fix_versions": v["fix_versions"]}
                for v in p["vulns"]]} for p in data["dependencies"]]}


write("dependencies.json", {"tool": "pip-audit 2.10.1", "scope": "Installed application environment including Waitress and pip; audit tools are in a different environment.",
      "before": audit(LOCAL / "initial-app-audit.json"), "after": audit(LOCAL / "patched-app-audit.json"),
      "review": "Seven original advisory records map to four distinct advisories; three PYSEC IDs were returned twice. No direct Fernet exploit was demonstrated. cryptography was upgraded to 50.0.2."})

scan = read(LOCAL / "sslyze-final.json")["server_scan_results"][0]["scan_result"]
protocols = {}
for key in ["ssl_2_0", "ssl_3_0", "tls_1_0", "tls_1_1", "tls_1_2", "tls_1_3"]:
    item = scan[key + "_cipher_suites"]
    result = item["result"]
    protocols[key] = {"status": item["status"], "supported": result["is_tls_version_supported"],
                      "accepted_ciphers": [c["cipher_suite"]["name"] for c in result["accepted_cipher_suites"]]}
certificate = scan["certificate_info"]["result"]["certificate_deployments"][0]
validation = [{"store": item["trust_store"]["name"], "valid": item["was_validation_successful"]}
              for item in certificate["path_validation_results"]]
weaknesses = {k: {"status": scan[k]["status"], "result": scan[k]["result"]} for k in [
    "tls_compression", "openssl_ccs_injection", "tls_fallback_scsv", "heartbleed", "robot", "session_renegotiation"]}
write("tls.json", {"tool": "SSLyze 6.3.1", "target": "localhost:8443", "raw_result_sha256": digest(LOCAL / "sslyze-final.json"),
      "protocols": protocols, "certificate_validation": validation, "weakness_checks": weaknesses,
      "trust_scope": "The supplied project CA validates the chain. Default public root stores do not trust this local CA. No Windows/browser trust-store change was made."})

zap = read(LOCAL / "zap-results/zap-public.json")
alerts = []
for site in zap.get("site", []):
    for alert in site.get("alerts", []):
        alerts.append({"id": alert["pluginid"], "name": alert["name"], "risk": alert["riskdesc"],
                       "count": alert["count"], "instances": [
                           {k: v for k, v in instance.items() if k in {"uri", "method", "param"}}
                           for instance in alert.get("instances", [])]})
log = (LOCAL / "zap-run.txt").read_text(encoding="utf-8-sig", errors="replace")
if "Automation plan succeeded!" not in log:
    raise ValueError("Refusing to export an incomplete ZAP run")
if any(int(alert["riskcode"]) > 0 for site in zap.get("site", []) for alert in site.get("alerts", [])):
    raise ValueError("Non-informational ZAP alerts require review before using this summary")
duration = re.search(r"Job activeScan finished, time taken: (\d+):(\d+):(\d+)", log)
scan_seconds = sum(int(value) * factor for value, factor in zip(duration.groups(), [3600, 60, 1]))
write("zap.json", {"tool": "OWASP ZAP 2.17.0", "target": "https://localhost:8443", "authentication": "Anonymous scan; private role checks were assessed separately.",
      "spider_urls": int(re.search(r"spider found (\d+) URLs", log)[1]), "active_scan_seconds": scan_seconds,
      "policy": "Five active rules: SQL injection, reflected XSS, path traversal, CRLF injection and external redirect; low strength; two threads; three-minute maximum.",
      "automation_plan_succeeded": True, "raw_result_sha256": digest(LOCAL / "zap-results/zap-public.json"),
      "alerts": alerts, "review": {"10015": "Public static assets are cacheable; sensitive responses were confirmed no-store.",
          "10112": "Cookie-bearing authentication/registration responses were identified; this is informational.",
          "10031": "Search input is reflected in an escaped value attribute. A quote/event-handler probe did not create attributes; CSP disallows scripts."}})

bandit = read(LOCAL / "bandit-final.json")
write("static-analysis.json", {"tool": "Bandit 1.9.4", "raw_result_sha256": digest(LOCAL / "bandit-final.json"),
      "findings": [{k: f[k] for k in ["test_id", "issue_severity", "issue_confidence", "filename", "line_number", "issue_text"]} for f in bandit["results"]],
      "review": "B310 flags urlopen in the Caddy installer. The URL is a fixed HTTPS publisher release URL, not request input, and the archive must match a pinned SHA-512 before extraction/execution. Reviewed false positive; retained rather than globally suppressing the rule."})

observations = [json.loads(line) for line in (LOCAL / "https-assessment/private/request-observations.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
write("request-observations.json", {"method": "Exploratory source/configuration review and individually selected HTTP request manipulations, supported by scripts. These are not independent user tests or a full penetration test.", "observations": observations})
test_log = (LOCAL / "security-test-run.txt").read_text(encoding="utf-8-sig", errors="replace")
match = re.search(r"Ran (\d+) tests in ([\d.]+)s", test_log)
if not match or "\nOK" not in test_log:
    raise ValueError("Missing successful automated test result")
write("regression-tests.json", {"command": ".venv/Scripts/python.exe manage.py test --noinput", "tests": int(match[1]), "seconds": float(match[2]), "result": "OK", "raw_log_sha256": digest(LOCAL / "security-test-run.txt"), "performance_claim": False})
write("host-controls.json", read(LOCAL / "host-controls.json"))

tool_sources = {"caddy": {"version": "2.11.7", "checksum_algorithm": "SHA-512", "archive_checksum": "c308154504e53755958ffc62d8a2657ab17eefd6dd25c45dbb2c3d93d29519971f77ca652f7d0f2bcb7f980b9ba3822478865e29969d0272d7613550a43152b1", "source": "https://github.com/caddyserver/caddy/releases/tag/v2.11.7"},
                "zap": read(LOCAL / "tools/zap-download.json"), "java": read(LOCAL / "tools/jre-download.json")}
write("tools.json", tool_sources)
paths = ["config/settings.py", "config/proxy.py", "core/middleware.py", "core/services.py", "core/tests.py", "core/test_deployment.py", "core/management/commands/create_account.py", "core/management/commands/seed_demo.py", "deploy/Caddyfile", "requirements.lock", "requirements-deploy.txt", "run-https.ps1", "scripts/initialize.py", "scripts/check_deployment.py", "scripts/install_caddy.py", "scripts/serve_https_backend.py", "security/zap.yaml", "security/prepare_fixture.py", "security/live_client.py", "security/export_evidence.py"]
write("manifest.json", {"recorded_at": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).isoformat(), "baseline_commit": "29b2bde", "scope": "Local HTTPS and host controls, application regression tests, dependency/static/web/TLS scans and targeted request manipulation. Report frozen.",
      "source_sha256": {path: digest(ROOT / path) for path in paths}, "evidence_sha256": {p.name: digest(p) for p in OUT.glob("*.json") if p.name != "manifest.json"}})
print("Exported redacted security evidence. Raw credentials, codes and sessions were not copied.")
