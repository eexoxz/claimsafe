import json
import os
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.test import override_settings

from config.state_lock import StateLock
from core.crypto import decrypt_text, encrypt_text
from scripts import manage_data


class DataOperationsTests(TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory(dir=Path(settings.BASE_DIR) / ".local")
        self.root = Path(self.temporary.name).resolve()
        self.assertTrue(self.root.is_relative_to((Path(settings.BASE_DIR) / ".local").resolve()))
        self.addCleanup(self.temporary.cleanup)
        self.state = self.root / "source"
        self.state.mkdir()
        self.keys = {"secret_key": "original-session-key", "proxy_token": "original-proxy-token", "encryption_key": Fernet.generate_key().decode()}
        self.key_file = self.state / "private/secrets.json"
        self.database = self.state / "data/claimsafe.sqlite3"
        self.backup_key = self.root / "backup.key"
        manage_data.private_write(self.key_file, json.dumps(self.keys).encode())
        manage_data.private_write(self.backup_key, Fernet.generate_key())
        self.database.parent.mkdir()
        self.token = Fernet(self.keys["encryption_key"]).encrypt(b"fictional private evidence").decode()
        with closing(sqlite3.connect(self.database)) as db, db:
            db.executescript("""
                CREATE TABLE core_founditem (id TEXT PRIMARY KEY, identifying_details_ciphertext TEXT);
                CREATE TABLE core_claim (id TEXT PRIMARY KEY, proof_ciphertext TEXT, review_note_ciphertext TEXT);
                CREATE TABLE core_accountsecurity (user_id INTEGER PRIMARY KEY, totp_secret_ciphertext TEXT, pending_secret_ciphertext TEXT, pending_session_digest TEXT, pending_expires_at TEXT, last_totp_counter INTEGER, version INTEGER);
                CREATE TABLE django_session (session_key TEXT);
                CREATE TABLE core_collectiongrant (id INTEGER);
                CREATE TABLE core_ratebucket (key TEXT);
                CREATE TABLE core_recoverycode (digest TEXT, used_at TEXT);
                INSERT INTO django_session VALUES ('old-session');
                INSERT INTO core_collectiongrant VALUES (1);
                INSERT INTO core_ratebucket VALUES ('expired-or-old-counter');
                INSERT INTO core_recoverycode VALUES ('old-recovery-code-digest', NULL);
            """)
            db.execute("INSERT INTO core_founditem VALUES (?,?)", ("item", self.token))
            db.execute("INSERT INTO core_claim VALUES (?,?,?)", ("claim", self.token, self.token))
            db.execute("INSERT INTO core_accountsecurity VALUES (?,?,?,?,?,?,?)", (1, self.token, self.token, "old-handle", "2099-01-01", -1, 1))

    def value(self):
        with closing(sqlite3.connect(self.database)) as db:
            return db.execute("SELECT proof_ciphertext FROM core_claim").fetchone()[0]

    def test_encrypted_backup_restores_data_and_revokes_old_authorisations(self):
        archive = self.root / "snapshot.csb"
        result = manage_data.backup(self.state, self.backup_key, archive)
        self.assertEqual(result["encrypted_fields_verified"], 5)
        self.assertNotIn(b"fictional private evidence", archive.read_bytes())
        self.assertNotIn(self.keys["encryption_key"].encode(), archive.read_bytes())
        target = self.root / "restored"
        manage_data.restore(archive, self.backup_key, target)
        restored_keys = json.loads((target / "private/secrets.json").read_text())
        self.assertNotEqual(restored_keys["secret_key"], self.keys["secret_key"])
        self.assertNotEqual(restored_keys["proxy_token"], self.keys["proxy_token"])
        with closing(sqlite3.connect(target / "data/claimsafe.sqlite3")) as db:
            value = db.execute("SELECT proof_ciphertext FROM core_claim").fetchone()[0]
            self.assertEqual(Fernet(restored_keys["encryption_key"]).decrypt(value.encode()), b"fictional private evidence")
            for table in ["django_session", "core_collectiongrant", "core_ratebucket"]:
                # These are constant test fixture identifiers, never request input.
                self.assertEqual(db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0], 0)
            self.assertIsNotNone(db.execute("SELECT used_at FROM core_recoverycode").fetchone()[0])
            state = db.execute("SELECT pending_secret_ciphertext,pending_session_digest,version FROM core_accountsecurity").fetchone()
            self.assertEqual(state, ("", "", 2))

    def test_wrong_backup_key_and_tampering_leave_no_restore_destination(self):
        archive = self.root / "snapshot.csb"
        manage_data.backup(self.state, self.backup_key, archive)
        wrong_key = self.root / "wrong.key"
        manage_data.private_write(wrong_key, Fernet.generate_key())
        with self.assertRaises(InvalidToken):
            manage_data.restore(archive, wrong_key, self.root / "wrong-target")
        self.assertFalse((self.root / "wrong-target").exists())
        data = bytearray(archive.read_bytes())
        data[-12] = ord('a') if data[-12] != ord('a') else ord('b')
        archive.write_bytes(data)
        with self.assertRaises(InvalidToken):
            manage_data.restore(archive, self.backup_key, self.root / "tamper-target")
        self.assertFalse((self.root / "tamper-target").exists())

    def test_backup_and_restore_never_overwrite_existing_outputs(self):
        archive = self.root / "snapshot.csb"
        manage_data.backup(self.state, self.backup_key, archive)
        original = archive.read_bytes()
        with self.assertRaises(FileExistsError):
            manage_data.backup(self.state, self.backup_key, archive)
        self.assertEqual(archive.read_bytes(), original)
        with self.assertRaises(ValueError):
            manage_data.restore(archive, self.backup_key, self.state)
        self.assertEqual(self.value(), self.token)

    def test_rotation_then_retirement_preserves_data_and_token_timestamps(self):
        result = manage_data.rotate(self.state, self.backup_key, self.root / "before-rotation.csb")
        self.assertEqual(result["rotated_fields"], 5)
        keys = json.loads(self.key_file.read_text())
        self.assertNotEqual(keys["encryption_key"], self.keys["encryption_key"])
        self.assertEqual(keys["retired_encryption_keys"], [self.keys["encryption_key"]])
        new = self.value()
        self.assertEqual(Fernet(keys["encryption_key"]).decrypt(new.encode()), b"fictional private evidence")
        with self.assertRaises(InvalidToken):
            Fernet(self.keys["encryption_key"]).decrypt(new.encode())
        self.assertEqual(Fernet(keys["encryption_key"]).extract_timestamp(new.encode()), Fernet(self.keys["encryption_key"]).extract_timestamp(self.token.encode()))
        result = manage_data.retire(self.state, self.backup_key, self.root / "before-retirement.csb")
        self.assertEqual(result["retired_keys_removed"], 1)
        self.assertEqual(json.loads(self.key_file.read_text())["retired_encryption_keys"], [])

    def test_retirement_refuses_records_still_using_an_old_key(self):
        changed = dict(self.keys, encryption_key=Fernet.generate_key().decode(), retired_encryption_keys=[self.keys["encryption_key"]])
        manage_data.private_write(self.key_file, json.dumps(changed).encode(), replace=True)
        with self.assertRaises(InvalidToken):
            manage_data.retire(self.state, self.backup_key, self.root / "before-retirement.csb")
        self.assertEqual(json.loads(self.key_file.read_text()), changed)

    def test_failed_rotation_rolls_back_records_with_both_keys_available(self):
        real_verify = manage_data.verify_database
        calls = []
        def fail_at_final_verification(connection, field_cipher):
            calls.append(True)
            if len(calls) == 3:
                raise InvalidToken
            return real_verify(connection, field_cipher)
        with patch.object(manage_data, "verify_database", side_effect=fail_at_final_verification):
            with self.assertRaises(InvalidToken):
                manage_data.rotate(self.state, self.backup_key, self.root / "before-failed-rotation.csb")
        self.assertEqual(self.value(), self.token)
        remaining = json.loads(self.key_file.read_text())
        self.assertIn(self.keys["encryption_key"], remaining["retired_encryption_keys"])
        self.assertEqual(manage_data.cipher(remaining).decrypt(self.token.encode()), b"fictional private evidence")

    def test_server_lease_blocks_maintenance_and_a_second_process(self):
        with StateLock(self.state):
            with self.assertRaises(RuntimeError):
                manage_data.backup(self.state, self.backup_key, self.root / "blocked.csb")
            code = "from config.state_lock import StateLock; import sys; StateLock(sys.argv[1]).acquire()"
            result = subprocess.run([sys.executable, "-c", code, str(self.state)], cwd=settings.BASE_DIR, capture_output=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            environment = dict(os.environ, CLAIMSAFE_STATE_DIR=str(self.state))
            result = subprocess.run([sys.executable, "scripts/prepare_profile.py"], env=environment, cwd=settings.BASE_DIR, capture_output=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"This profile is in use", result.stderr)
        self.assertFalse((self.root / "blocked.csb").exists())

    def test_application_key_ring_reads_old_records_but_only_writes_with_primary(self):
        new_key = Fernet.generate_key().decode()
        with override_settings(FIELD_ENCRYPTION_KEY=new_key, FIELD_ENCRYPTION_FALLBACK_KEYS=[self.keys["encryption_key"]]):
            self.assertEqual(decrypt_text(self.token), "fictional private evidence")
            value = encrypt_text("new evidence")
            self.assertEqual(Fernet(new_key).decrypt(value.encode()), b"new evidence")
            with self.assertRaises(InvalidToken):
                Fernet(self.keys["encryption_key"]).decrypt(value.encode())
