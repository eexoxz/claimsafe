"""Exercise a real encrypted snapshot in a new private profile; never rotate source keys."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import manage_data as operations


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_digest(state):
    _, key_file, database = operations.profile_paths(state)
    field_cipher = operations.cipher(json.loads(key_file.read_text()))
    values = []
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as db:
        count = operations.verify_database(db, field_cipher)
        for table, query, _ in operations.FIELDS:
            if operations.has_table(db, table):
                for identity, value in db.execute(query):
                    # Keep only a digest in memory; never print plaintext or keys.
                    values.append((table, str(identity), hashlib.sha256(field_cipher.decrypt(value.encode())).hexdigest() if value else ""))
    return count, hashlib.sha256(json.dumps(sorted(values)).encode()).hexdigest()


def fresh_application(state):
    environment = dict(os.environ, DJANGO_SETTINGS_MODULE="config.settings", CLAIMSAFE_STATE_DIR=str(state),
                       CLAIMSAFE_SECRETS_FILE=str(state / "private/secrets.json"),
                       CLAIMSAFE_DATABASE=str(state / "data/claimsafe.sqlite3"), CLAIMSAFE_PRODUCTION="0")
    code = "import django; django.setup(); from django.db import connection; from core.crypto import decrypt_text; from scripts.manage_data import FIELDS; n=0\nfor table,query,_ in FIELDS:\n for _,value in connection.cursor().execute(query):\n  if value: decrypt_text(value); n+=1\nprint(n)"
    result = subprocess.run([sys.executable, "-c", code], env=environment, cwd=ROOT, capture_output=True, text=True, check=True)
    return int(result.stdout.strip())


source = ROOT / ".local/https-assessment"
suffix = secrets.token_hex(5)
workspace = ROOT / (".local/operations-check-" + suffix)
workspace.mkdir(mode=0o700)
operations.protect(workspace, directory=True)
key = workspace / "independent-backup.key"
operations.private_write(key, operations.Fernet.generate_key())
_, source_keys, source_db = operations.profile_paths(source)
before_source = (fingerprint(source_keys), fingerprint(source_db))
archive = workspace / "snapshot.csb"
backup_result = operations.backup(source, key, archive)
restored = ROOT / (".local/restore-check-" + suffix)
restore_result = operations.restore(archive, key, restored)
before = content_digest(restored)
_, _, database = operations.profile_paths(restored)
with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as db:
    invalidated = all(db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] == 0 for table in ["django_session", "core_collectiongrant", "core_ratebucket"])
    codes_revoked = db.execute("SELECT COUNT(*) FROM core_recoverycode WHERE used_at IS NULL").fetchone()[0] == 0
if not invalidated or not codes_revoked:
    raise RuntimeError("Restored authorisations were not revoked.")
restored_application_fields = fresh_application(restored)
rotation = operations.rotate(restored, key, workspace / "before-rotation.csb")
if content_digest(restored) != before or fresh_application(restored) != restored_application_fields:
    raise RuntimeError("Rotation changed decrypted data or failed after a fresh app start.")
retirement = operations.retire(restored, key, workspace / "before-retirement.csb")
if content_digest(restored) != before or fresh_application(restored) != restored_application_fields:
    raise RuntimeError("Retirement changed decrypted data or failed after a fresh app start.")
if (fingerprint(source_keys), fingerprint(source_db)) != before_source:
    raise RuntimeError("Assessment source unexpectedly changed.")
legacy = ROOT / ".local"
legacy_fields, _ = content_digest(legacy)
with closing(sqlite3.connect((legacy / "claimsafe.sqlite3").as_uri() + "?mode=ro", uri=True)) as db:
    legacy_counts = {"items": db.execute("SELECT COUNT(*) FROM core_founditem").fetchone()[0], "claims": db.execute("SELECT COUNT(*) FROM core_claim").fetchone()[0]}
result = {"method": "Offline authenticated snapshot of the real fictional HTTPS assessment database, restored into a new private profile; rotation and retirement performed only on that copy", "backup": backup_result, "restore": restore_result, "rotation": rotation, "retirement": retirement, "fresh_application_decrypted_fields": restored_application_fields, "decrypted_data_preserved_through_rotation_and_retirement": True, "source_database_and_keys_unchanged": True, "restored_sessions_grants_rate_buckets_cleared": invalidated, "restored_recovery_codes_revoked": codes_revoked, "original_demo": dict(legacy_counts, encrypted_fields_verified=legacy_fields), "secrets_printed": False}
(workspace / "redacted-result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
print("Private copy for launcher validation: " + restored.name)
