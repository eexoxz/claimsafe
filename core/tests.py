"""Tests assert security rules and permitted workflows, not just implementation details."""
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from cryptography.fernet import InvalidToken
from django.conf import settings
from django.db import IntegrityError, close_old_connections, transaction
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .crypto import decrypt_text, encrypt_text
from .forms import RegistrationForm
from .models import AccountSecurity, AuditEvent, Claim, CollectionGrant, FoundItem, RateBucket, User
from .services import WorkflowError, collect_item, issue_collection_code, review_claim, submit_claim, throttle


PASSWORD = "A-mossy-courtyard!493"
PROOF = "A crescent sticker inside the left ear cup, and a blue cable in the case."
PRIVATE = "Secret engraving: silver maple, fictional item identifying detail."


def make_item(officer, title="Headphones"):
    return FoundItem.objects.create(
        title=title, category="electronics", public_description="Wireless headphones in a case.",
        location="Campus library", found_on=timezone.localdate(),
        identifying_details_ciphertext=encrypt_text(PRIVATE), recorded_by=officer,
    )


class SecurityWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alex = User.objects.create_user("alex", "alex@example.test", PASSWORD)
        cls.jamie = User.objects.create_user("jamie", "jamie@example.test", PASSWORD)
        cls.officer = User.objects.create_user("officer", "officer@example.test", PASSWORD, role="officer")
        cls.admin = User.objects.create_user("admin", "admin@example.test", PASSWORD, role="admin")
        cls.item = make_item(cls.officer)
        cls.claim = submit_claim(cls.alex, cls.item.pk, PROOF)

    def sign_in_as(self, user, client=None):
        client = client or self.client
        client.force_login(user)
        session = client.session
        session["authenticated_at"] = time.time()
        if user.is_officer:
            # These tests isolate authorisation/workflow behaviour. Actual password
            # and second-factor exchanges are exercised in test_account_security.py.
            state, _ = AccountSecurity.objects.get_or_create(user=user, defaults={"totp_secret_ciphertext": encrypt_text("JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP")})
            if not state.enabled:
                state.totp_secret_ciphertext = encrypt_text("JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP")
                state.save(update_fields=["totp_secret_ciphertext"])
            session["mfa_user_id"] = user.pk
            session["mfa_version"] = state.version
        session.save()
        return client

    def approve(self):
        review_claim(self.officer, self.claim.pk, "approve", "The identifying details match. Please visit the property desk.")

    def test_public_pages_never_disclose_private_item_details_or_claim_evidence(self):
        for url in (reverse("home"), reverse("item_detail", args=[self.item.pk])):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, PRIVATE)
            self.assertNotContains(response, PROOF)
            self.assertNotContains(response, self.item.identifying_details_ciphertext)

    def test_student_cannot_read_another_persons_claim(self):
        self.sign_in_as(self.jamie)
        response = self.client.get(reverse("claim_detail", args=[self.claim.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, PROOF, status_code=404)
        self.assertTrue(AuditEvent.objects.filter(action="access.claim_denied", outcome="denied").exists())

    def test_claimant_can_read_own_claim_but_not_withheld_details(self):
        self.sign_in_as(self.alex)
        response = self.client.get(reverse("claim_detail", args=[self.claim.pk]))
        self.assertContains(response, PROOF)
        self.assertNotContains(response, PRIVATE)

    def test_officer_can_read_private_evidence_and_access_is_logged(self):
        self.sign_in_as(self.officer)
        response = self.client.get(reverse("claim_detail", args=[self.claim.pk]))
        self.assertContains(response, PRIVATE)
        self.assertTrue(AuditEvent.objects.filter(actor=self.officer, action="evidence.claim_viewed").exists())

    def test_registration_cannot_set_privileged_fields(self):
        response = self.client.post(reverse("register"), {
            "username": "newstudent", "email": "new@example.test", "password1": PASSWORD,
            "password2": PASSWORD, "privacy_acknowledged": "on", "role": "admin", "is_staff": "1", "is_superuser": "1",
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newstudent")
        self.assertEqual(user.role, "student")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_registration_rejects_weak_password(self):
        response = self.client.post(reverse("register"), {
            "username": "newstudent", "email": "new@example.test", "password1": "password",
            "password2": "password", "privacy_acknowledged": "on",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newstudent").exists())

    def test_registration_cannot_use_duplicate_email_with_different_case(self):
        self.client.post(reverse("register"), {
            "username": "newstudent", "email": "ALEX@EXAMPLE.TEST", "password1": PASSWORD,
            "password2": PASSWORD, "privacy_acknowledged": "on",
        })
        self.assertFalse(User.objects.filter(username="newstudent").exists())

    def test_student_cannot_record_items_review_collect_or_view_admin_data(self):
        self.sign_in_as(self.alex)
        for name in ("item_new", "staff_queue", "audit", "users"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)
        for name in ("review", "collect"):
            self.assertEqual(self.client.post(reverse(name, args=[self.claim.pk]), {}).status_code, 403, name)

    def test_officer_can_record_an_item_without_publishing_private_details(self):
        self.sign_in_as(self.officer)
        response = self.client.post(reverse("item_new"), {
            "title": "Fictional notebook", "category": "books", "location": "Design studio",
            "found_on": timezone.localdate().isoformat(), "public_description": "A lined notebook.",
            "identifying_details": PRIVATE,
        })
        self.assertEqual(response.status_code, 302)
        item = FoundItem.objects.get(title="Fictional notebook")
        self.assertEqual(decrypt_text(item.identifying_details_ciphertext), PRIVATE)
        self.client.post(reverse("logout"))
        self.assertNotContains(self.client.get(reverse("item_detail", args=[item.pk])), PRIVATE)

    def test_item_form_rejects_future_found_dates(self):
        self.sign_in_as(self.officer)
        self.client.post(reverse("item_new"), {
            "title": "Future item", "category": "books", "location": "Design studio",
            "found_on": (timezone.localdate() + timedelta(days=1)).isoformat(),
            "public_description": "A lined notebook.", "identifying_details": PRIVATE,
        })
        self.assertFalse(FoundItem.objects.filter(title="Future item").exists())

    def test_officer_cannot_view_admin_dashboard_or_manage_users(self):
        self.sign_in_as(self.officer)
        self.assertEqual(self.client.get(reverse("audit")).status_code, 403)
        self.assertEqual(self.client.post(reverse("toggle_user", args=[self.alex.pk])).status_code, 403)

    def test_staff_cannot_review_their_own_claim(self):
        own_claim = submit_claim(self.officer, self.item.pk, PROOF)
        with self.assertRaises(WorkflowError) as raised:
            review_claim(self.officer, own_claim.pk, "approve", "My own claim should not be approved by me.")
        self.assertEqual(raised.exception.status, 403)

    def test_approval_reserves_item_and_closes_competing_claims(self):
        other = submit_claim(self.jamie, self.item.pk, "Different evidence from another fictional claimant.")
        self.approve()
        self.item.refresh_from_db()
        self.claim.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.item.status, "reserved")
        self.assertEqual(self.claim.status, "approved")
        self.assertEqual(other.status, "rejected")

    def test_rejected_claim_does_not_reserve_the_item(self):
        review_claim(self.officer, self.claim.pk, "reject", "We could not establish a sufficient match.")
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, "available")

    def test_approved_claim_cannot_be_reviewed_again(self):
        self.approve()
        with self.assertRaises(WorkflowError):
            review_claim(self.officer, self.claim.pk, "reject", "A second review should be rejected.")

    def test_one_person_cannot_submit_duplicate_claims(self):
        with self.assertRaises(WorkflowError):
            submit_claim(self.alex, self.item.pk, PROOF)

    def test_claim_submission_cannot_force_approved_state(self):
        self.sign_in_as(self.jamie)
        self.client.post(reverse("claim_new", args=[self.item.pk]), {"proof": PROOF, "truthful": "on", "status": "approved"})
        self.assertEqual(Claim.objects.get(claimant=self.jamie).status, "pending")

    def test_database_rejects_two_winning_claims_for_one_item(self):
        self.approve()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Claim.objects.create(item=self.item, claimant=self.jamie, proof_ciphertext=encrypt_text(PROOF), status="approved")

    def test_pending_claim_cannot_get_collection_authorisation(self):
        with self.assertRaises(WorkflowError):
            issue_collection_code(self.alex, self.claim.pk)

    def test_only_claimant_can_issue_a_code_even_if_other_user_is_staff(self):
        self.approve()
        for user in (self.jamie, self.officer, self.admin):
            with self.assertRaises(WorkflowError):
                issue_collection_code(user, self.claim.pk)

    def test_code_is_hashed_and_never_written_to_audit_events(self):
        self.approve()
        token = issue_collection_code(self.alex, self.claim.pk)
        grant = CollectionGrant.objects.get(claim=self.claim)
        self.assertNotEqual(grant.digest, token)
        self.assertEqual(grant.digest, hashlib.sha256(token.encode()).hexdigest())
        self.assertNotIn(token, str(list(AuditEvent.objects.values())))

    def test_reissued_code_invalidates_the_previous_one(self):
        self.approve()
        first = issue_collection_code(self.alex, self.claim.pk)
        second = issue_collection_code(self.alex, self.claim.pk)
        with self.assertRaises(WorkflowError):
            collect_item(self.officer, self.claim.pk, first, True)
        collect_item(self.officer, self.claim.pk, second, True)

    def test_expired_code_cannot_collect_item(self):
        self.approve()
        token = issue_collection_code(self.alex, self.claim.pk)
        CollectionGrant.objects.filter(claim=self.claim).update(expires_at=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(WorkflowError):
            collect_item(self.officer, self.claim.pk, token, True)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, "reserved")

    def test_full_handover_and_replay_rejection(self):
        self.approve()
        token = issue_collection_code(self.alex, self.claim.pk)
        collect_item(self.officer, self.claim.pk, token, True)
        self.claim.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(self.claim.status, "collected")
        self.assertEqual(self.item.status, "returned")
        with self.assertRaises(WorkflowError):
            collect_item(self.officer, self.claim.pk, token, True)
        self.assertEqual(AuditEvent.objects.filter(action="collection.completed").count(), 1)

    def test_collection_requires_an_in_person_confirmation(self):
        self.approve()
        token = issue_collection_code(self.alex, self.claim.pk)
        with self.assertRaises(WorkflowError):
            collect_item(self.officer, self.claim.pk, token, False)
        self.assertIsNone(CollectionGrant.objects.get(claim=self.claim).used_at)

    def test_officer_cannot_confirm_their_own_handover(self):
        own_claim = submit_claim(self.officer, self.item.pk, PROOF)
        review_claim(self.admin, own_claim.pk, "approve", "Another staff member reviewed these details.")
        token = issue_collection_code(self.officer, own_claim.pk)
        with self.assertRaises(WorkflowError) as raised:
            collect_item(self.officer, own_claim.pk, token, True)
        self.assertEqual(raised.exception.status, 403)

    def test_wrong_claim_code_cannot_authorise_a_different_item(self):
        self.approve()
        token = issue_collection_code(self.alex, self.claim.pk)
        other_item = make_item(self.officer, "Notebook")
        other_claim = submit_claim(self.alex, other_item.pk, PROOF)
        review_claim(self.officer, other_claim.pk, "approve", "This claim was reviewed independently.")
        with self.assertRaises(WorkflowError):
            collect_item(self.officer, other_claim.pk, token, True)

    def test_failed_handover_rolls_back_token_consumption(self):
        self.approve()
        token = issue_collection_code(self.alex, self.claim.pk)
        FoundItem.objects.filter(pk=self.item.pk).update(status="available")
        with self.assertRaises(WorkflowError):
            collect_item(self.officer, self.claim.pk, token, True)
        self.assertIsNone(CollectionGrant.objects.get(claim=self.claim).used_at)
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.status, "approved")

    def test_code_response_is_private_and_code_does_not_reappear_on_get(self):
        self.approve()
        self.sign_in_as(self.alex)
        response = self.client.post(reverse("issue_code", args=[self.claim.pk]))
        token = response.context["collection_token"]
        self.assertContains(response, token)
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertNotContains(self.client.get(reverse("claim_detail", args=[self.claim.pk])), token)

    def test_stored_script_is_rendered_as_text(self):
        payload = '<script>alert("evidence")</script>'
        self.claim.proof_ciphertext = encrypt_text(payload)
        self.claim.save(update_fields=["proof_ciphertext"])
        self.sign_in_as(self.officer)
        response = self.client.get(reverse("claim_detail", args=[self.claim.pk]))
        self.assertNotContains(response, payload)
        self.assertContains(response, "&lt;script&gt;")
        self.assertIn("script-src 'none'", response.headers["Content-Security-Policy"])

    def test_search_input_is_not_executed_as_sql(self):
        response = self.client.get(reverse("home"), {"q": "' OR 1=1 --"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["items"].paginator.count, 0)
        self.assertEqual(FoundItem.objects.count(), 1)

    def test_csrf_required_even_for_an_authenticated_staff_member(self):
        csrf_client = self.sign_in_as(self.officer, Client(enforce_csrf_checks=True))
        response = csrf_client.post(reverse("review", args=[self.claim.pk]), {"decision": "approve", "note": "Should not bypass a missing CSRF token."})
        self.assertEqual(response.status_code, 403)
        self.assertIn("Content-Security-Policy", response.headers)
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.status, "pending")

    def test_mutating_routes_reject_get(self):
        self.sign_in_as(self.officer)
        for name in ("review", "collect", "issue_code"):
            self.assertEqual(self.client.get(reverse(name, args=[self.claim.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)

    def test_login_rotates_session_and_logout_invalidates_it(self):
        session = self.client.session
        session["pre_login"] = True
        session.save()
        old = session.session_key
        response = self.client.post(reverse("login"), {"username": "alex", "password": PASSWORD})
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(self.client.session.session_key, old)
        self.assertIn("authenticated_at", self.client.session)
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_privileged_password_login_requires_authenticator_setup_before_workspace(self):
        for user in (self.officer, self.admin):
            response = self.client.post(reverse("login"), {"username": user.username, "password": PASSWORD})
            self.assertRedirects(response, reverse("mfa_setup"), fetch_redirect_response=False)
            self.client.post(reverse("logout"))

    def test_absolute_session_age_is_enforced(self):
        self.sign_in_as(self.alex)
        session = self.client.session
        session["authenticated_at"] = time.time() - settings.SESSION_ABSOLUTE_SECONDS - 1
        session.save()
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_deactivated_user_loses_access_with_an_existing_session(self):
        self.sign_in_as(self.alex)
        User.objects.filter(pk=self.alex.pk).update(is_active=False)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 302)

    def test_login_throttle_persists_across_requests(self):
        RateBucket.objects.all().delete()
        for _ in range(5):
            self.client.post(reverse("login"), {"username": "nonexistent", "password": "wrong"})
        response = self.client.post(reverse("login"), {"username": "nonexistent", "password": "wrong"})
        self.assertEqual(response.status_code, 429)
        self.assertNotIn("nonexistent", str(list(RateBucket.objects.values())))

    def test_counter_window_can_expire(self):
        self.assertTrue(throttle("test", "actor", 1))
        self.assertFalse(throttle("test", "actor", 1))
        RateBucket.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertTrue(throttle("test", "actor", 1))

    def test_private_fields_are_encrypted_and_authenticate_ciphertext(self):
        self.assertNotIn(PROOF, self.claim.proof_ciphertext)
        self.assertEqual(decrypt_text(self.claim.proof_ciphertext), PROOF)
        tampered = self.claim.proof_ciphertext[:-8] + "AAAAAAAA"
        with self.assertRaises(InvalidToken):
            decrypt_text(tampered)

    def test_admin_can_view_audit_but_private_proof_is_absent(self):
        self.sign_in_as(self.admin)
        response = self.client.get(reverse("audit"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, PROOF)
        self.assertNotContains(response, PRIVATE)

    def test_admin_cannot_deactivate_self(self):
        self.sign_in_as(self.admin)
        response = self.client.post(reverse("toggle_user", args=[self.admin.pk]))
        self.assertEqual(response.status_code, 403)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertTrue(AuditEvent.objects.filter(action="account.change_denied", outcome="denied").exists())

    def test_administrator_can_deactivate_a_student_and_record_the_action(self):
        self.sign_in_as(self.admin)
        self.assertEqual(self.client.post(reverse("toggle_user", args=[self.jamie.pk]), {"active": "0"}).status_code, 302)
        self.jamie.refresh_from_db()
        self.assertFalse(self.jamie.is_active)
        self.assertTrue(AuditEvent.objects.filter(action="account.deactivated", actor=self.admin).exists())

    def test_reactivation_does_not_restore_an_old_session(self):
        self.sign_in_as(self.admin)
        for user, legacy in [(self.jamie, False), (self.alex, True)]:
            with self.subTest(legacy=legacy):
                previous = self.sign_in_as(user, Client())
                url = reverse("toggle_user", args=[user.pk])
                if legacy:
                    User.objects.filter(pk=user.pk).update(is_active=False)
                else:
                    self.assertRedirects(self.client.post(url, {"active": "0"}), reverse("users"))
                self.assertRedirects(self.client.post(url, {"active": "1"}), reverse("users"))
                self.assertRedirects(previous.get(reverse("dashboard")), reverse("login"))
                response = previous.post(reverse("login"), {"username": user.username, "password": PASSWORD})
                self.assertRedirects(response, reverse("dashboard"))

    def test_repeating_deactivation_does_not_reactivate_account(self):
        self.sign_in_as(self.admin)
        url = reverse("toggle_user", args=[self.jamie.pk])
        for _ in range(2):
            self.assertEqual(self.client.post(url, {"active": "0"}).status_code, 302)
        self.jamie.refresh_from_db()
        self.assertFalse(self.jamie.is_active)
        self.assertEqual(AuditEvent.objects.filter(action="account.deactivated", target=str(self.jamie.pk)).count(), 1)

    def test_login_throttle_groups_equivalent_unicode_usernames(self):
        url = reverse("login")
        for username in ("alex", "ａｌｅｘ", "alex", "ａｌｅｘ", "alex"):
            self.assertEqual(self.client.post(url, {"username": username, "password": "wrong"}).status_code, 200)
        self.assertEqual(self.client.post(url, {"username": "ａｌｅｘ", "password": PASSWORD}).status_code, 429)

    @override_settings(DEBUG=False)
    def test_missing_page_does_not_disclose_tracebacks(self):
        response = self.client.get("/not-a-real-page/")
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, "Traceback", status_code=404)


class ConcurrentRegistrationTests(TransactionTestCase):
    def test_concurrent_case_variants_cannot_register_twice(self):
        barrier = Barrier(2)
        validate = RegistrationForm.is_valid

        def synchronised_validation(form):
            valid = validate(form)
            if valid:
                barrier.wait(timeout=15)
            return valid

        def register(username):
            close_old_connections()
            try:
                return Client().post(reverse("register"), {
                    "username": username, "email": f"entry-{ord(username[0])}@example.test",
                    "password1": PASSWORD, "password2": PASSWORD, "privacy_acknowledged": "on",
                }).status_code
            finally:
                close_old_connections()

        with patch.object(RegistrationForm, "is_valid", synchronised_validation):
            with ThreadPoolExecutor(max_workers=2) as executor:
                responses = list(executor.map(register, ["CampusAccount", "campusaccount"]))
        self.assertCountEqual(responses, [200, 302])
        self.assertEqual(User.objects.filter(username__iexact="campusaccount").count(), 1)


class ConcurrentHandoverTests(TransactionTestCase):
    def test_two_simultaneous_requests_only_complete_one_handover(self):
        officer = User.objects.create_user("officer", "officer@example.test", PASSWORD, role="officer")
        student = User.objects.create_user("alex", "alex@example.test", PASSWORD)
        item = make_item(officer)
        claim = submit_claim(student, item.pk, PROOF)
        review_claim(officer, claim.pk, "approve", "The details were reviewed and matched.")
        token = issue_collection_code(student, claim.pk)
        barrier = Barrier(2)

        def attempt():
            close_old_connections()
            try:
                actor = User.objects.get(pk=officer.pk)
                barrier.wait(timeout=10)
                try:
                    collect_item(actor, claim.pk, token, True)
                    return "collected"
                except WorkflowError:
                    return "denied"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _: attempt(), range(2)))
        self.assertCountEqual(outcomes, ["collected", "denied"])
        self.assertEqual(AuditEvent.objects.filter(action="collection.completed").count(), 1)
        claim.refresh_from_db()
        self.assertEqual(claim.status, "collected")
