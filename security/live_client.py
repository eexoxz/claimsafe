"""Small request client for exploratory checks; never prints credentials or cookies."""
import json
from pathlib import Path

from bs4 import BeautifulSoup
import requests

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".local/https-assessment"
BASE = "https://localhost:8443"
CA = str(STATE / "tls/pki/authorities/local/root.crt")


def fixture():
    return json.loads((STATE / "private/assessment-fixture.json").read_text(encoding="utf-8"))


def client(actor=None, *, password_only=False):
    session = requests.Session()
    session.trust_env = False
    session.verify = CA
    if actor is not None:
        account = fixture()["actors"][actor]
        page = session.get(BASE + "/login/", timeout=15)
        token = BeautifulSoup(page.text, "html.parser").select_one('input[name="csrfmiddlewaretoken"]')["value"]
        reply = session.post(BASE + "/login/", data={
            "username": account["username"], "password": account["password"], "csrfmiddlewaretoken": token,
        }, headers={"Origin": BASE, "Referer": BASE + "/login/"}, allow_redirects=False, timeout=15)
        if reply.status_code != 302:
            raise RuntimeError(f"Fixture login did not succeed: HTTP {reply.status_code}")
        if not password_only and reply.headers.get("Location", "").startswith("/account/"):
            complete_mfa(session, actor, reply.headers["Location"])
    return session


def complete_mfa(session, actor, location):
    """Enrol only disposable fictional actors, never an operator's own account."""
    import pyotp
    data = fixture()
    account = data["actors"][actor]
    if not account["username"].startswith("check_"):
        raise ValueError("Automatic enrolment is restricted to fictional assessment accounts.")
    if location == "/account/authenticator/":
        page = post(session, location, {"action": "start", "password": account["password"]})
        element = BeautifulSoup(page.text, "html.parser").select_one(".token-box code")
        if page.status_code != 200 or element is None:
            raise RuntimeError("Fictional authenticator setup failed.")
        secret = element.get_text(strip=True)
        page = post(session, location, {"action": "confirm", "code": pyotp.TOTP(secret).now()})
        codes = [element.get_text(strip=True) for element in BeautifulSoup(page.text, "html.parser").select(".recovery-code-list code")]
        if page.status_code != 200 or len(codes) != 10:
            raise RuntimeError("Fictional authenticator confirmation failed.")
        account.update(totp_secret=secret, recovery_codes=codes)
    elif location == "/account/verify/":
        codes = account.get("recovery_codes", [])
        if not codes:
            raise RuntimeError("Fictional recovery codes exhausted; prepare a new isolated fixture.")
        page = post(session, location, {"code": codes.pop()})
        if page.status_code != 302:
            raise RuntimeError("Fictional second-factor verification failed.")
    else:
        raise RuntimeError("Unexpected account redirect during fixture sign-in.")
    # The fixture lives inside the ACL-protected ignored assessment profile.
    (STATE / "private/assessment-fixture.json").write_text(json.dumps(data), encoding="utf-8")


def get(session, path, **kwargs):
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("Only paths on the local assessment target are allowed.")
    return session.get(BASE + path, allow_redirects=False, timeout=15, **kwargs)


def post(session, path, data, *, csrf=True, headers=None):
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("Only paths on the local assessment target are allowed.")
    payload = dict(data)
    request_headers = {"Origin": BASE, "Referer": BASE + path}
    if csrf:
        if not session.cookies.get("__Host-claimsafe_csrf"):
            get(session, "/login/")
        payload["csrfmiddlewaretoken"] = session.cookies["__Host-claimsafe_csrf"]
    request_headers.update(headers or {})
    return session.post(BASE + path, data=payload, headers=request_headers, allow_redirects=False, timeout=15)


def observe(case, result):
    """Caller supplies only redacted observations, never request/response dumps."""
    row = {"case": case, **result}
    with (STATE / "private/request-observations.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row) + "\n")
    print(json.dumps(row))
