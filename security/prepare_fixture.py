"""Create new fictional records only in the isolated HTTPS assessment database."""
import json
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".local/https-assessment"
if not (STATE / "data/claimsafe.sqlite3").is_file():
    raise SystemExit("Prepare run-https.ps1 -Assessment first.")
os.environ.update({
    "DJANGO_SETTINGS_MODULE": "config.settings",
    "CLAIMSAFE_STATE_DIR": str(STATE),
    "CLAIMSAFE_SECRETS_FILE": str(STATE / "private/secrets.json"),
    "CLAIMSAFE_DATABASE": str(STATE / "data/claimsafe.sqlite3"),
    "CLAIMSAFE_PRODUCTION": "0",
})
sys.path.insert(0, str(ROOT))
import django
django.setup()
from django.db import transaction
from django.utils import timezone
from core.crypto import encrypt_text
from core.models import FoundItem, RateBucket, User
from core.services import review_claim, submit_claim

suffix = secrets.token_hex(4)
fixture = {"actors": {}, "items": [], "marker": f"FICTIONAL-WITHHELD-{suffix}"}
with transaction.atomic():
    # Only this disposable profile is permitted above. Retain audit history, but reset
    # its test rate windows so a previous intentional lockout does not block a new run.
    RateBucket.objects.all().delete()
    for alias, role in [("owner", "student"), ("other", "student"), ("officer", "officer"), ("admin", "admin")]:
        password = secrets.token_urlsafe(24)
        user = User.objects.create_user(f"check_{alias}_{suffix}", f"{alias}-{suffix}@example.test", password, role=role)
        fixture["actors"][alias] = {"id": user.pk, "username": user.username, "password": password}
    officer = User.objects.get(pk=fixture["actors"]["officer"]["id"])
    owner = User.objects.get(pk=fixture["actors"]["owner"]["id"])
    for i in range(3):
        item = FoundItem.objects.create(
            title=f"Fictional assessment item {suffix}-{i}", category="other", location="Fictional test desk",
            public_description="Fictional record for the local security assessment.",
            identifying_details_ciphertext=encrypt_text(fixture["marker"]),
            recorded_by=officer, found_on=timezone.localdate(),
        )
        fixture["items"].append(str(item.pk))
    first = submit_claim(owner, fixture["items"][0], "Fictional ownership evidence: a crescent inside the lid.")
    second = submit_claim(owner, fixture["items"][1], "Fictional ownership evidence: a violet stitched inner pocket.")
    review_claim(officer, second.pk, "approve", "Fictional assessment approval for the collection checks.")
    fixture["pending_claim"] = str(first.pk)
    fixture["approved_claim"] = str(second.pk)
path = STATE / "private/assessment-fixture.json"
path.write_text(json.dumps(fixture), encoding="utf-8")
print("Created four fictional accounts, three items and two claims in the isolated assessment database.")
print("Reset rate counters in this isolated profile for a new assessment run.")
print("Fixture credentials were saved privately and were not printed.")
