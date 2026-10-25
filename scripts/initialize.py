"""Create checkout-local keys once. Never overwrite keys for an existing database."""
import json
import argparse
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--proxy-token", action="store_true", help="Also provision the local HTTPS proxy credential")
args = parser.parse_args()
local = Path(os.environ.get("CLAIMSAFE_STATE_DIR", Path(__file__).resolve().parent.parent / ".local")).resolve()
local.mkdir(mode=0o700, exist_ok=True)
path = Path(os.environ.get("CLAIMSAFE_SECRETS_FILE", local / "secrets.json")).resolve()
database = Path(os.environ.get("CLAIMSAFE_DATABASE", local / "claimsafe.sqlite3")).resolve()
path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
database.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
if not path.exists():
    if database.exists():
        raise SystemExit("Database exists without secrets. Restore the matching keys; do not generate replacements.")
    with path.open("x", encoding="utf-8") as stream:
        values = {"secret_key": secrets.token_urlsafe(64), "encryption_key": Fernet.generate_key().decode()}
        if args.proxy_token:
            values["proxy_token"] = secrets.token_urlsafe(48)
        json.dump(values, stream)
    if os.name != "nt":
        path.chmod(0o600)
    print("Created private local configuration. Keep .local out of version control.")
else:
    if args.proxy_token and not json.loads(path.read_text(encoding="utf-8")).get("proxy_token"):
        raise SystemExit("Existing secrets lack a proxy token. Provision it explicitly; existing keys were retained.")
    print("Existing local configuration retained.")
