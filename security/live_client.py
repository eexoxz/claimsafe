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


def client(actor=None):
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
    return session


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
        page = get(session, "/dashboard/")
        element = BeautifulSoup(page.text, "html.parser").select_one('input[name="csrfmiddlewaretoken"]')
        payload["csrfmiddlewaretoken"] = element["value"]
    request_headers.update(headers or {})
    return session.post(BASE + path, data=payload, headers=request_headers, allow_redirects=False, timeout=15)


def observe(case, result):
    """Caller supplies only redacted observations, never request/response dumps."""
    row = {"case": case, **result}
    with (STATE / "private/request-observations.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row) + "\n")
    print(json.dumps(row))
