"""Create checkout-local keys once. Never overwrite keys for an existing database."""
import json
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet

local = Path(__file__).resolve().parent.parent / ".local"
local.mkdir(mode=0o700, exist_ok=True)
path = local / "secrets.json"
if not path.exists():
    if (local / "claimsafe.sqlite3").exists():
        raise SystemExit("Database exists without secrets. Restore the matching keys; do not generate replacements.")
    with path.open("x", encoding="utf-8") as stream:
        json.dump({"secret_key": secrets.token_urlsafe(64), "encryption_key": Fernet.generate_key().decode()}, stream)
    if os.name != "nt":
        path.chmod(0o600)
    print("Created private local configuration. Keep .local out of version control.")
else:
    print("Existing local configuration retained.")
