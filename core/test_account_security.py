import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

import pyotp
from django.db import close_old_connections
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from .account_security import (begin_setup, confirm_setup, pending_secret, recover_account,
                               replace_recovery_codes, security_state, verify_factor)
from .crypto import decrypt_text, encrypt_text
from .models import AccountSecurity, AuditEvent, RecoveryCode, User
from .services import WorkflowError

PASSWORD = "A-square-brass-lock!492"
NEW_PASSWORD = "An-even-better-lock!648"
SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"


class AccountSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user("security_student", "student@example.test", PASSWORD)
        cls.officer = User.objects.create_user("security_officer", "officer@example.test", PASSWORD, role="officer")

    def password_session(self, user, client=None, verified=False):
        client = client or self.client
        client.force_login(user)
        session = client.session
        session["authenticated_at"] = time.time()
        if verified:
            state = security_state(user)
            session["mfa_user_id"] = user.pk
            session["mfa_version"] = state.version
        session.save()
        return client

    def enrolled(self, user):
        return AccountSecurity.objects.create(user=user, totp_secret_ciphertext=encrypt_text(SECRET))

    def test_password_alone_does_not_open_staff_routes_or_private_record_routes(self):
        response = self.client.post(reverse("login"), {"username": self.officer.username, "password": PASSWORD}, secure=True)
        self.assertRedirects(response, reverse("mfa_setup"), fetch_redirect_response=False)
        for url in [reverse("staff_queue"), reverse("users"), reverse("home"), "/claims/00000000-0000-0000-0000-000000000001/"]:
            response = self.client.get(url, secure=True)
            self.assertRedirects(response, reverse("mfa_setup"), fetch_redirect_response=False)

    def test_authenticator_operations_refuse_http(self):
        self.password_session(self.officer)
        response = self.client.get(reverse("mfa_setup"))
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("setup_secret", response.context)

    def test_pending_secret_is_encrypted_and_bound_to_the_browser_session(self):
        first = self.password_session(self.officer)
        second = self.password_session(self.officer, Client())
        response = first.post(reverse("mfa_setup"), {"action": "start", "password": PASSWORD}, secure=True)
        secret = response.context["setup_secret"]
        state = security_state(self.officer)
        self.assertTrue(secret)
        self.assertNotIn(secret, state.pending_secret_ciphertext)
        self.assertEqual(decrypt_text(state.pending_secret_ciphertext), secret)
        self.assertEqual(second.get(reverse("mfa_setup"), secure=True).context["setup_secret"], "")
        response = second.post(reverse("mfa_setup"), {"action": "confirm", "code": pyotp.TOTP(secret).now()}, secure=True)
        self.assertEqual(response.status_code, 200)
        state.refresh_from_db()
        self.assertFalse(state.enabled)

    def test_setup_requires_current_password(self):
        self.password_session(self.officer)
        self.client.post(reverse("mfa_setup"), {"action": "start", "password": "wrong"}, secure=True)
        self.assertFalse(security_state(self.officer).pending_secret_ciphertext)

    def test_setup_expiry_and_wrong_code_do_not_enable_authenticator(self):
        handle = begin_setup(self.officer, PASSWORD)
        state = security_state(self.officer)
        with self.assertRaises(WorkflowError):
            confirm_setup(self.officer, "not-a-code", handle)
        state.pending_expires_at = timezone.now() - timedelta(seconds=1)
        state.save(update_fields=["pending_expires_at"])
        self.assertEqual(pending_secret(state, handle), "")
        with self.assertRaises(WorkflowError):
            confirm_setup(self.officer, pyotp.TOTP(decrypt_text(state.pending_secret_ciphertext)).now(), handle)

    def test_completed_setup_shows_recovery_codes_once_and_enables_staff_access(self):
        self.password_session(self.officer)
        response = self.client.post(reverse("mfa_setup"), {"action": "start", "password": PASSWORD}, secure=True)
        secret = response.context["setup_secret"]
        response = self.client.post(reverse("mfa_setup"), {"action": "confirm", "code": pyotp.TOTP(secret).now()}, secure=True)
        codes = response.context["codes"]
        self.assertEqual(len(codes), 10)
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertEqual(self.client.get(reverse("staff_queue"), secure=True).status_code, 200)
        account = self.client.get(reverse("account_security"), secure=True)
        for code in codes:
            self.assertNotContains(account, code)
            self.assertFalse(RecoveryCode.objects.filter(digest=code).exists())
        state = security_state(self.officer)
        self.assertFalse(state.pending_secret_ciphertext)
        self.assertNotEqual(secret, state.totp_secret_ciphertext)

    def test_password_and_fresh_totp_finish_login_but_another_session_cannot_replay_it(self):
        self.enrolled(self.officer)
        for client in [self.client, Client()]:
            reply = client.post(reverse("login"), {"username": self.officer.username, "password": PASSWORD}, secure=True)
            self.assertRedirects(reply, reverse("mfa_challenge"), fetch_redirect_response=False)
            self.assertRedirects(client.get(reverse("staff_queue"), secure=True), reverse("mfa_challenge"), fetch_redirect_response=False)
            code = getattr(self, "first_code", pyotp.TOTP(SECRET).now())
            reply = client.post(reverse("mfa_challenge"), {"code": code}, secure=True)
            if client is self.client:
                self.first_code = code
                self.assertRedirects(reply, reverse("staff_queue"))
            else:
                self.assertEqual(reply.status_code, 200)
                self.assertRedirects(client.get(reverse("staff_queue"), secure=True), reverse("mfa_challenge"), fetch_redirect_response=False)

    def test_unused_recovery_code_can_finish_mfa_once(self):
        _, codes = replace_recovery_codes(self.officer, PASSWORD)
        self.enrolled_secret_existing(self.officer)
        self.assertTrue(verify_factor(self.officer, codes[0]))
        self.assertFalse(verify_factor(self.officer, codes[0]))

    def enrolled_secret_existing(self, user):
        state = security_state(user)
        state.totp_secret_ciphertext = encrypt_text(SECRET)
        state.save(update_fields=["totp_secret_ciphertext"])
        return state

    def test_wrong_codes_are_throttled(self):
        self.enrolled(self.officer)
        self.password_session(self.officer)
        for _ in range(5):
            self.assertEqual(self.client.post(reverse("mfa_challenge"), {"code": "invalid"}, secure=True).status_code, 200)
        self.assertEqual(self.client.post(reverse("mfa_challenge"), {"code": pyotp.TOTP(SECRET).now()}, secure=True).status_code, 429)

    def test_changing_security_version_invalidates_previous_mfa_proof(self):
        state = self.enrolled(self.officer)
        self.password_session(self.officer, verified=True)
        state.version += 1
        state.save(update_fields=["version"])
        self.assertRedirects(self.client.get(reverse("staff_queue"), secure=True), reverse("mfa_challenge"), fetch_redirect_response=False)

    def test_student_can_generate_recovery_codes_without_enabling_totp(self):
        self.password_session(self.student)
        response = self.client.post(reverse("account_security"), {"password": PASSWORD}, secure=True)
        codes = response.context["codes"]
        self.assertEqual(len(codes), 10)
        self.assertFalse(security_state(self.student).enabled)
        self.assertEqual(self.client.get(reverse("dashboard"), secure=True).status_code, 200)

    def test_generating_replacement_codes_revokes_the_old_set(self):
        _, old = replace_recovery_codes(self.student, PASSWORD)
        _, new = replace_recovery_codes(self.student, PASSWORD)
        self.assertFalse(recover_account(self.student, old[0], NEW_PASSWORD))
        self.assertTrue(recover_account(self.student, new[0], NEW_PASSWORD))

    def test_full_account_recovery_changes_password_revokes_sessions_and_resets_factors(self):
        _, codes = replace_recovery_codes(self.officer, PASSWORD)
        self.enrolled_secret_existing(self.officer)
        previous = self.password_session(self.officer, Client(), verified=True)
        response = self.client.post(reverse("account_recovery"), {"username": self.officer.username,
            "recovery_code": codes[0], "new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD}, secure=True)
        self.assertEqual(response.status_code, 200)
        self.officer.refresh_from_db()
        self.assertTrue(self.officer.check_password(NEW_PASSWORD))
        self.assertFalse(security_state(self.officer).enabled)
        self.assertFalse(RecoveryCode.objects.filter(user=self.officer, used_at__isnull=True).exists())
        self.assertFalse(recover_account(self.officer, codes[0], PASSWORD))
        self.assertRedirects(previous.get(reverse("staff_queue"), secure=True), reverse("login") + "?next=" + reverse("staff_queue"), fetch_redirect_response=False)

    def test_saved_code_cannot_reactivate_a_deactivated_account(self):
        _, codes = replace_recovery_codes(self.student, PASSWORD)
        self.student.is_active = False
        self.student.save(update_fields=["is_active"])
        self.assertFalse(recover_account(self.student, codes[0], NEW_PASSWORD))

    def test_recovery_has_the_same_completion_message_for_invalid_and_unknown_accounts(self):
        bodies = []
        for name in [self.student.username, "not_an_account"]:
            response = self.client.post(reverse("account_recovery"), {"username": name,
                "recovery_code": "a" * 32, "new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD}, secure=True)
            self.assertEqual(response.status_code, 200)
            bodies.append(response.context["user"].is_authenticated)
            self.assertContains(response, "If the username and saved recovery code were valid")
        self.assertEqual(bodies, [False, False])

    def test_recovery_prefers_the_exact_unicode_username(self):
        user = User.objects.create_user("Straße", "unicode@example.test", PASSWORD)
        User.objects.create_user("strasse", "other@example.test", PASSWORD)
        _, codes = replace_recovery_codes(user, PASSWORD)
        self.client.post(reverse("account_recovery"), {"username": "Straße",
            "recovery_code": codes[0], "new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD}, secure=True)
        user.refresh_from_db()
        self.assertTrue(user.check_password(NEW_PASSWORD))

    def test_recovery_keeps_account_specific_validation_private_until_code_is_valid(self):
        password = self.student.email + "!"
        for username in (self.student.username, "not_an_account"):
            response = self.client.post(reverse("account_recovery"), {"username": username,
                "recovery_code": "a" * 32, "new_password1": password, "new_password2": password}, secure=True)
            self.assertContains(response, "If the username and saved recovery code were valid")

        _, codes = replace_recovery_codes(self.student, PASSWORD)
        response = self.client.post(reverse("account_recovery"), {"username": self.student.username,
            "recovery_code": codes[0], "new_password1": password, "new_password2": password}, secure=True)
        self.assertTrue(response.context["form"].has_error("new_password2", "password_too_similar"))
        self.assertTrue(recover_account(self.student, codes[0], NEW_PASSWORD))

    def test_recovery_rejects_weak_new_password_without_consuming_saved_code(self):
        _, codes = replace_recovery_codes(self.student, PASSWORD)
        response = self.client.post(reverse("account_recovery"), {"username": self.student.username,
            "recovery_code": codes[0], "new_password1": "password", "new_password2": "password"}, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(recover_account(self.student, codes[0], NEW_PASSWORD))

    def test_password_change_preserves_current_session_and_invalidates_another(self):
        self.password_session(self.student)
        previous = self.password_session(self.student, Client())
        response = self.client.post(reverse("password_change"), {"old_password": PASSWORD,
            "new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD}, secure=True)
        self.assertRedirects(response, reverse("account_security"), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("dashboard"), secure=True).status_code, 200)
        self.assertRedirects(previous.get(reverse("dashboard"), secure=True), reverse("login") + "?next=" + reverse("dashboard"), fetch_redirect_response=False)

    def test_authenticator_protected_password_change_requires_a_fresh_factor(self):
        self.enrolled(self.officer)
        self.password_session(self.officer, verified=True)
        payload = {"old_password": PASSWORD, "new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD}
        self.client.post(reverse("password_change"), payload, secure=True)
        self.officer.refresh_from_db()
        self.assertTrue(self.officer.check_password(PASSWORD))
        payload["code"] = pyotp.TOTP(SECRET).now()
        self.assertRedirects(self.client.post(reverse("password_change"), payload, secure=True), reverse("account_security"), fetch_redirect_response=False)

    def test_sensitive_posts_still_require_csrf(self):
        client = self.password_session(self.student, Client(enforce_csrf_checks=True))
        self.assertEqual(client.post(reverse("account_security"), {"password": PASSWORD}, secure=True).status_code, 403)

    def test_audit_events_exclude_passwords_totp_secrets_and_recovery_codes(self):
        handle = begin_setup(self.officer, PASSWORD)
        state = security_state(self.officer)
        secret = pending_secret(state, handle)
        _, codes = confirm_setup(self.officer, pyotp.TOTP(secret).now(), handle)
        events = str(list(AuditEvent.objects.values("action", "target", "outcome")))
        for value in [PASSWORD, secret, *codes]:
            self.assertNotIn(value, events)

    def test_a_concurrent_security_change_is_not_adopted_as_a_new_mfa_proof(self):
        state = self.enrolled(self.officer)
        self.password_session(self.officer)
        def accepted_then_revoked(user, code):
            proof = verify_factor(user, code)
            AccountSecurity.objects.filter(user=user).update(version=state.version + 1)
            return proof
        with patch("core.account_views.verify_factor", side_effect=accepted_then_revoked):
            self.client.post(reverse("mfa_challenge"), {"code": pyotp.TOTP(SECRET).now()}, secure=True)
        self.assertRedirects(self.client.get(reverse("staff_queue"), secure=True), reverse("mfa_challenge"), fetch_redirect_response=False)

    def test_a_password_reset_prevents_recovery_code_generation_from_a_stale_actor(self):
        stale = User.objects.get(pk=self.student.pk)
        self.student.set_password(NEW_PASSWORD)
        self.student.save(update_fields=["password"])
        with self.assertRaises(WorkflowError):
            replace_recovery_codes(stale, PASSWORD)
        self.assertFalse(RecoveryCode.objects.filter(user=self.student, used_at__isnull=True).exists())


class ConcurrentAuthenticatorTests(TransactionTestCase):
    def test_simultaneous_use_of_the_same_totp_succeeds_once(self):
        user = User.objects.create_user("concurrent_factor", "concurrent@example.test", PASSWORD, role="officer")
        AccountSecurity.objects.create(user=user, totp_secret_ciphertext=encrypt_text(SECRET))
        code = pyotp.TOTP(SECRET).now()
        barrier = Barrier(2)
        def attempt():
            close_old_connections()
            try:
                actor = User.objects.get(pk=user.pk)
                barrier.wait(timeout=10)
                return bool(verify_factor(actor, code))
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))
        self.assertEqual(sorted(results), [False, True])
