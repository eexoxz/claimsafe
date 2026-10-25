"""Offline encrypted backup, restoration and field-key rotation for standard profiles."""
import argparse
import base64
import csv
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import time

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config.state_lock import StateLock

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
FIELDS = [
    ("core_founditem", "SELECT id, identifying_details_ciphertext FROM core_founditem", "UPDATE core_founditem SET identifying_details_ciphertext=? WHERE id=?"),
    ("core_claim", "SELECT id, proof_ciphertext FROM core_claim", "UPDATE core_claim SET proof_ciphertext=? WHERE id=?"),
    ("core_claim", "SELECT id, review_note_ciphertext FROM core_claim", "UPDATE core_claim SET review_note_ciphertext=? WHERE id=?"),
    ("core_accountsecurity", "SELECT user_id, totp_secret_ciphertext FROM core_accountsecurity", "UPDATE core_accountsecurity SET totp_secret_ciphertext=? WHERE user_id=?"),
    ("core_accountsecurity", "SELECT user_id, pending_secret_ciphertext FROM core_accountsecurity", "UPDATE core_accountsecurity SET pending_secret_ciphertext=? WHERE user_id=?"),
]


def protect(path, directory=False):
    """Change only the named task file/directory, never a parent's ACL."""
    if os.name == "nt":
        system = Path(os.environ["SystemRoot"]) / "System32"
        output = subprocess.run([str(system / "whoami.exe"), "/user", "/fo", "csv", "/nh"], check=True, capture_output=True, text=True).stdout
        sid = next(csv.reader(io.StringIO(output.strip())))[1]
        rights = "(OI)(CI)F" if directory else "F"
        if directory:
            # Python's Windows mode=0700 creates explicit Administrators and
            # OWNER RIGHTS grants. Remove those before applying this profile's
            # narrower current-user/SYSTEM policy; inheritance:r alone keeps them.
            subprocess.run([str(system / "icacls.exe"), str(path), "/remove:g", "*S-1-3-4", "*S-1-5-32-544"], check=True, capture_output=True)
        subprocess.run([str(system / "icacls.exe"), str(path), "/inheritance:r", "/grant:r", f"*{sid}:{rights}", f"*S-1-5-18:{rights}"], check=True, capture_output=True)
    else:
        path.chmod(0o700 if directory else 0o600)


def private_write(path, value, replace=False):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Refusing to write through a symbolic link.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".writing-" + secrets.token_hex(8)) if replace else path
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        # Restrict the newly created empty file before writing any key/plaintext.
        protect(temporary)
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    if replace:
        os.replace(temporary, path)


def profile_paths(state):
    if Path(state).is_symlink() or Path(state).is_junction():
        raise ValueError("Profile must not be a symbolic link or junction.")
    state = Path(state).resolve()
    key_path = state / "private/secrets.json" if (state / "private/secrets.json").is_file() else state / "secrets.json"
    db_path = state / "data/claimsafe.sqlite3" if (state / "data/claimsafe.sqlite3").is_file() else state / "claimsafe.sqlite3"
    if not key_path.is_file() or not db_path.is_file():
        raise ValueError("This standard profile has no matching database and secrets file.")
    return state, key_path, db_path


def cipher(config, primary_only=False):
    keys = [config["encryption_key"]]
    if not primary_only:
        keys.extend(config.get("retired_encryption_keys", []))
    return MultiFernet([Fernet(key) for key in keys])


def has_table(connection, table):
    return connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def verify_database(connection, field_cipher):
    if not has_table(connection, "core_founditem") or not has_table(connection, "core_claim"):
        raise ValueError("Archive is not a ClaimSafe database.")
    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok" or connection.execute("PRAGMA foreign_key_check").fetchone():
        raise ValueError("Database integrity verification failed.")
    count = 0
    for table, select, _ in FIELDS:
        if has_table(connection, table):
            for _, value in connection.execute(select):
                if value:
                    field_cipher.decrypt(value.encode())
                    count += 1
    return count


def _backup_locked(key_path, db_path, backup_key, output):
    config = json.loads(key_path.read_text(encoding="utf-8"))
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as source, closing(sqlite3.connect(":memory:")) as snapshot:
        source.backup(snapshot)
        count = verify_database(snapshot, cipher(config))
        database = snapshot.serialize()
    payload = {"format": "ClaimSafe backup 1", "created_at": datetime.now(timezone.utc).isoformat(),
               "database_sha256": hashlib.sha256(database).hexdigest(), "database": base64.b64encode(database).decode(), "secrets": config}
    backup_cipher = Fernet(Path(backup_key).read_bytes().strip())
    encrypted = backup_cipher.encrypt(json.dumps(payload).encode())
    if len(encrypted) > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive exceeds the prototype's 64 MiB limit.")
    private_write(output, encrypted)
    # Authentication and read-back must succeed before a rotation may proceed.
    if backup_cipher.decrypt(Path(output).read_bytes()) != json.dumps(payload).encode():
        raise ValueError("Backup read-back verification failed.")
    return {"encrypted_fields_verified": count, "archive_bytes": len(encrypted), "archive_sha256": hashlib.sha256(encrypted).hexdigest()}


def backup(state, backup_key, output):
    state, key_path, db_path = profile_paths(state)
    with StateLock(state):
        return _backup_locked(key_path, db_path, backup_key, output)


def restore(archive, backup_key, target):
    if Path(target).is_symlink() or Path(target).is_junction():
        raise ValueError("Restore destination must not be a link or junction.")
    target = Path(target).resolve()
    if target.exists():
        raise ValueError("Restore requires a new destination; existing profiles are never overwritten.")
    if Path(archive).stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive exceeds the prototype's 64 MiB limit.")
    raw = Fernet(Path(backup_key).read_bytes().strip()).decrypt(Path(archive).read_bytes())
    payload = json.loads(raw)
    if payload.get("format") != "ClaimSafe backup 1":
        raise ValueError("Unsupported backup format.")
    database = base64.b64decode(payload["database"], validate=True)
    if hashlib.sha256(database).hexdigest() != payload["database_sha256"]:
        raise ValueError("Database checksum verification failed.")
    config = payload["secrets"]
    with closing(sqlite3.connect(":memory:")) as restored:
        restored.deserialize(database)
        count = verify_database(restored, cipher(config))
        # An older snapshot must not resurrect browser sessions, handover codes,
        # pending enrolments or saved recovery codes that may have since been used.
        for sql, table in [("DELETE FROM django_session", "django_session"),
                           ("DELETE FROM core_collectiongrant", "core_collectiongrant"),
                           ("DELETE FROM core_ratebucket", "core_ratebucket")]:
            if has_table(restored, table):
                restored.execute(sql)
        if has_table(restored, "core_recoverycode"):
            restored.execute("UPDATE core_recoverycode SET used_at=? WHERE used_at IS NULL", (datetime.now(timezone.utc).isoformat(),))
        if has_table(restored, "core_accountsecurity"):
            restored.execute("UPDATE core_accountsecurity SET pending_secret_ciphertext='', pending_session_digest='', pending_expires_at=NULL, version=version+1, last_totp_counter=?", (int(time.time()) // 30 + 1,))
        restored.commit()
        database = restored.serialize()
    config["secret_key"] = secrets.token_urlsafe(64)
    config["proxy_token"] = secrets.token_urlsafe(48)
    # Build beside the requested destination, then expose the complete profile at
    # once. A failed staging write leaves no half-restored runnable destination.
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(target.name + ".restoring-" + secrets.token_hex(8)).resolve()
    if staging.parent != target.parent:
        raise ValueError("Restore staging escaped the requested parent.")
    staging.mkdir(exist_ok=False, mode=0o700)
    protect(staging, directory=True)
    with StateLock(staging):
        private_write(staging / "private/secrets.json", json.dumps(config).encode())
        private_write(staging / "data/claimsafe.sqlite3", database)
        private_write(staging / "RESTORE_NOTES.txt", b"Restored snapshot. Sessions, collection grants and recovery codes were invalidated. Review account changes and reconcile physical custody since the snapshot before reopening the service.\n")
    if target.exists():
        raise ValueError("Restore destination appeared during staging; nothing was overwritten.")
    os.rename(staging, target)
    return {"encrypted_fields_verified": count, "sessions_and_grants_invalidated": True, "saved_recovery_codes_revoked": True}


def rotate(state, backup_key, backup_output):
    state, key_path, db_path = profile_paths(state)
    with StateLock(state):
        _backup_locked(key_path, db_path, backup_key, backup_output)
        config = json.loads(key_path.read_text(encoding="utf-8"))
        old = [config["encryption_key"], *config.get("retired_encryption_keys", [])]
        new = Fernet.generate_key().decode()
        promoted = dict(config, encryption_key=new, retired_encryption_keys=old)
        with closing(sqlite3.connect(db_path)) as connection, connection:
            verify_database(connection, cipher(config))
            connection.execute("BEGIN EXCLUSIVE")
            # Write a recoverable key ring before changing records. Any crash leaves
            # either old or new tokens decryptable; SQLite rolls back partial writes.
            private_write(key_path, json.dumps(promoted).encode(), replace=True)
            transformer = cipher(promoted)
            count = 0
            for table, select, update in FIELDS:
                if has_table(connection, table):
                    for identity, value in connection.execute(select).fetchall():
                        if value:
                            connection.execute(update, (transformer.rotate(value.encode()).decode(), identity))
                            count += 1
            verify_database(connection, cipher(promoted, primary_only=True))
            connection.commit()
    return {"rotated_fields": count, "previous_keys_retained": len(old)}


def retire(state, backup_key, backup_output):
    state, key_path, db_path = profile_paths(state)
    with StateLock(state):
        _backup_locked(key_path, db_path, backup_key, backup_output)
        config = json.loads(key_path.read_text(encoding="utf-8"))
        with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as connection:
            count = verify_database(connection, cipher(config, primary_only=True))
        retired = len(config.get("retired_encryption_keys", []))
        config["retired_encryption_keys"] = []
        private_write(key_path, json.dumps(config).encode(), replace=True)
    return {"encrypted_fields_verified": count, "retired_keys_removed": retired}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    key = sub.add_parser("create-backup-key")
    key.add_argument("--output", required=True, type=Path)
    make = sub.add_parser("backup")
    make.add_argument("--state", required=True, type=Path)
    make.add_argument("--key-file", required=True, type=Path)
    make.add_argument("--output", required=True, type=Path)
    recover = sub.add_parser("restore")
    recover.add_argument("--archive", required=True, type=Path)
    recover.add_argument("--key-file", required=True, type=Path)
    recover.add_argument("--target", required=True, type=Path)
    for operation in ["rotate", "retire"]:
        rotate_parser = sub.add_parser(operation)
        rotate_parser.add_argument("--state", required=True, type=Path)
        rotate_parser.add_argument("--key-file", required=True, type=Path)
        rotate_parser.add_argument("--backup-output", required=True, type=Path,
                                   help="A new authenticated backup is written and verified before changing keys")
    args = parser.parse_args()
    try:
        if os.environ.get("CLAIMSAFE_ENCRYPTION_KEY"):
            raise ValueError("This file-backed maintenance tool does not manage environment-supplied field keys.")
        if args.operation == "create-backup-key":
            private_write(args.output, Fernet.generate_key() + b"\n")
            result = {"created_backup_key_file": str(args.output), "key_printed": False}
        elif args.operation == "backup":
            result = backup(args.state, args.key_file, args.output)
        elif args.operation == "restore":
            result = restore(args.archive, args.key_file, args.target)
        else:
            result = rotate(args.state, args.key_file, args.backup_output) if args.operation == "rotate" else retire(args.state, args.key_file, args.backup_output)
        print(json.dumps(result))
    except (ValueError, RuntimeError, OSError, InvalidToken, sqlite3.DatabaseError) as error:
        raise SystemExit(f"Maintenance stopped without printing secret data: {type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
