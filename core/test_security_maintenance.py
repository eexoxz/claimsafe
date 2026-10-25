from datetime import timedelta

from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from .crypto import encrypt_text
from .models import AccountSecurity, RateBucket, User


class SecurityMaintenanceTests(TestCase):
    def test_pruning_clears_only_expired_state(self):
        now = timezone.now()
        user = User.objects.create_user("prune_student", "prune@example.test", "A-unique-pruning-password!465")
        AccountSecurity.objects.create(user=user, totp_secret_ciphertext=encrypt_text("active-factor"),
            pending_secret_ciphertext=encrypt_text("expired-setup"), pending_session_digest="old", pending_expires_at=now-timedelta(seconds=1))
        Session.objects.create(session_key="old", session_data="", expire_date=now-timedelta(seconds=1))
        Session.objects.create(session_key="live", session_data="", expire_date=now+timedelta(hours=1))
        RateBucket.objects.create(key="expired", expires_at=now-timedelta(seconds=1))
        RateBucket.objects.create(key="active", expires_at=now+timedelta(minutes=10))
        call_command("prune_security_state", "--dry-run")
        self.assertTrue(RateBucket.objects.filter(key="expired").exists())
        call_command("prune_security_state")
        self.assertFalse(Session.objects.filter(session_key="old").exists())
        self.assertTrue(Session.objects.filter(session_key="live").exists())
        self.assertFalse(RateBucket.objects.filter(key="expired").exists())
        self.assertTrue(RateBucket.objects.filter(key="active").exists())
        state = AccountSecurity.objects.get(user=user)
        self.assertEqual(state.pending_secret_ciphertext, "")
        self.assertEqual(state.pending_session_digest, "")
        self.assertTrue(state.enabled)
