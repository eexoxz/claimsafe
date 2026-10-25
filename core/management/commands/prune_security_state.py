from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import AccountSecurity, RateBucket
from core.services import record


class Command(BaseCommand):
    help = "Remove expired sessions, abuse counters and unconfirmed authenticator setup keys."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        now = timezone.now()
        with transaction.atomic():
            sessions = Session.objects.filter(expire_date__lte=now)
            buckets = RateBucket.objects.filter(expires_at__lte=now)
            setups = AccountSecurity.objects.filter(pending_expires_at__lte=now)
            counts = {"sessions": sessions.count(), "rate_buckets": buckets.count(), "pending_setups": setups.count()}
            if not options["dry_run"]:
                sessions.delete()
                buckets.delete()
                setups.update(pending_secret_ciphertext="", pending_session_digest="", pending_expires_at=None)
                if any(counts.values()):
                    record(None, "maintenance.expired_state_pruned", str(counts))
        self.stdout.write(str(counts) + (" (dry run)" if options["dry_run"] else ""))
