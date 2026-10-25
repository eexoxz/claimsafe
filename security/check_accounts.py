"""Selected real HTTPS account checks against new fictional assessment actors only.

Run with the app interpreter and the isolated audit site-packages appended for
requests/BeautifulSoup. Never capture whole responses: they contain private codes.
"""
import json
from pathlib import Path
import secrets
import sys
import time

import pyotp
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from live_client import STATE, client, complete_mfa, fixture, get, post
from scripts.manage_data import backup


def check(condition, name):
    if not condition:
        raise RuntimeError("Failed check: " + name)
    RESULTS.append({"case": name, "result": "passed"})


RESULTS = []
data = fixture()
if any("totp_secret" in account for account in data["actors"].values()):
    raise SystemExit("Prepare a new fictional fixture before running this sequence.")

officer = client("officer", password_only=True)
page = get(officer, "/desk/")
check(page.status_code == 302 and page.headers["Location"] == "/account/authenticator/", "staff_password_alone_cannot_open_desk")
page = get(officer, "/items/" + data["items"][0] + "/")
check(data["marker"] not in page.text and page.status_code == 302, "staff_password_alone_cannot_read_private_item")
page = post(officer, "/account/authenticator/", {"action": "start", "password": data["actors"]["officer"]["password"]}, csrf=False)
check(page.status_code == 403, "authenticator_setup_rejects_missing_csrf")
complete_mfa(officer, "officer", "/account/authenticator/")
data = fixture()
check(get(officer, "/desk/").status_code == 200, "authenticator_enrolment_opens_staff_desk")
page = get(officer, "/account/security/")
check(page.status_code == 200 and "no-store" in page.headers.get("Cache-Control", ""), "account_security_response_is_not_cacheable")
check(not any(code in page.text for code in data["actors"]["officer"]["recovery_codes"]), "recovery_codes_not_redisplayed_on_security_page")
check(get(officer, "/activity/").status_code == 403, "verified_officer_cannot_open_administrator_audit")

password_only = client("officer", password_only=True)
secret = data["actors"]["officer"]["totp_secret"]
page = post(password_only, "/account/verify/", {"code": pyotp.TOTP(secret).now()})
check(page.status_code == 200 and get(password_only, "/desk/").status_code == 302, "enrolment_totp_cannot_be_replayed_for_sign_in")
# Wait for a genuinely fresh time step rather than manufacturing a future code.
time.sleep(30 - time.time() % 30 + 0.2)
code = pyotp.TOTP(secret).now()
page = post(password_only, "/account/verify/", {"code": code})
check(page.status_code == 302 and get(password_only, "/desk/").status_code == 200, "fresh_totp_completes_real_https_sign_in")
replay = client("officer", password_only=True)
page = post(replay, "/account/verify/", {"code": code})
check(page.status_code == 200 and get(replay, "/desk/").status_code == 302, "consumed_totp_cannot_open_another_session")
recovery_code = data["actors"]["officer"]["recovery_codes"].pop()
check(post(replay, "/account/verify/", {"code": recovery_code}).status_code == 302, "saved_recovery_code_completes_second_factor")
another = client("officer", password_only=True)
page = post(another, "/account/verify/", {"code": recovery_code})
check(page.status_code == 200 and get(another, "/desk/").status_code == 302, "consumed_recovery_code_cannot_be_replayed")
(STATE / "private/assessment-fixture.json").write_text(json.dumps(data), encoding="utf-8")

admin = client("admin")
check(get(admin, "/activity/").status_code == 200, "verified_administrator_can_open_audit")
owner = client("owner")
other = client("other")
check(get(other, "/claims/" + data["pending_claim"] + "/").status_code == 404, "other_student_cannot_open_owner_claim")
page = post(owner, "/account/security/", {"password": data["actors"]["owner"]["password"]})
codes = [element.get_text(strip=True) for element in BeautifulSoup(page.text, "html.parser").select(".recovery-code-list code")]
check(page.status_code == 200 and len(codes) == 10, "student_can_save_recovery_codes_without_enrolling_mfa")
second_owner = client("owner")
new_password = secrets.token_urlsafe(24)
page = post(owner, "/account/password/", {"old_password": data["actors"]["owner"]["password"], "new_password1": new_password, "new_password2": new_password})
check(page.status_code == 302 and get(owner, "/dashboard/").status_code == 200 and get(second_owner, "/dashboard/").status_code == 302, "password_change_keeps_current_session_and_revokes_other_session")
recoverer = client()
recovered_password = secrets.token_urlsafe(24)
page = post(recoverer, "/account/recover/", {"username": data["actors"]["owner"]["username"], "recovery_code": codes[0], "new_password1": recovered_password, "new_password2": recovered_password})
check(page.status_code == 200 and get(owner, "/dashboard/").status_code == 302, "saved_code_account_recovery_revokes_old_browser_session")
new_data = fixture()
new_data["actors"]["owner"]["password"] = recovered_password
(STATE / "private/assessment-fixture.json").write_text(json.dumps(new_data), encoding="utf-8")
check(get(client("owner"), "/dashboard/").status_code == 200, "recovered_student_can_sign_in_with_new_password")

try:
    backup(STATE, STATE / "private/not-a-backup-key", STATE / "private/should-not-exist.csb")
except RuntimeError:
    check(not (STATE / "private/should-not-exist.csb").exists(), "live_wsgi_profile_lease_blocks_offline_backup")
else:
    raise RuntimeError("The live server did not hold its profile lease.")

output = STATE / "private/account-checks.json"
output.write_text(json.dumps({"target": "https://localhost:8443", "tls_validation": "Project CA, hostname and validity verified by requests; no bypass", "method": "Selected scripted HTTPS requests using disposable fictional actors; not independent user testing or a complete penetration test", "checks": RESULTS}, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"checks_passed": len(RESULTS), "secrets_printed": False}))
