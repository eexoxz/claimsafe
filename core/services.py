"""Workflow boundary. Views must not change claim/item states independently."""
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .crypto import encrypt_text
from .models import AuditEvent, Claim, CollectionGrant, FoundItem, RateBucket


class WorkflowError(Exception):
    def __init__(self, message, status=409):
        super().__init__(message)
        self.status = status


def record(actor, action, target="", outcome="success"):
    return AuditEvent.objects.create(
        actor=actor if actor and actor.is_authenticated else None,
        action=action, target=str(target)[:80], outcome=outcome,
    )


def throttle(scope, identity, limit=5, seconds=900):
    """A fixed-window, persisted counter. No proxy-supplied IP headers are trusted."""
    key = salted_hmac("claimsafe.throttle", f"{scope}:{identity}").hexdigest()
    now = timezone.now()
    with transaction.atomic():
        bucket, _ = RateBucket.objects.get_or_create(key=key, defaults={"expires_at": now + timedelta(seconds=seconds)})
        if bucket.expires_at <= now:
            bucket.count = 0
            bucket.expires_at = now + timedelta(seconds=seconds)
            bucket.save(update_fields=["count", "expires_at"])
        if bucket.count >= limit:
            return False
        RateBucket.objects.filter(pk=key).update(count=F("count") + 1)
    return True


def require_officer(actor):
    if not actor.is_authenticated or not actor.is_officer:
        raise WorkflowError("This action is restricted to property staff.", 403)


def submit_claim(actor, item_id, proof):
    if not actor.is_authenticated or not actor.is_active:
        raise WorkflowError("Sign in to make a claim.", 403)
    if not 20 <= len(proof.strip()) <= 2000:
        raise WorkflowError("Provide between 20 and 2,000 characters of identifying evidence.", 400)
    with transaction.atomic():
        item = FoundItem.objects.get(pk=item_id)
        if item.status != FoundItem.Status.AVAILABLE:
            raise WorkflowError("This item is no longer accepting claims.")
        if Claim.objects.filter(item=item, claimant=actor).exists():
            raise WorkflowError("You have already submitted a claim for this item.")
        claim = Claim.objects.create(item=item, claimant=actor, proof_ciphertext=encrypt_text(proof.strip()))
        record(actor, "claim.submitted", claim.id)
    return claim


def review_claim(actor, claim_id, decision, note):
    require_officer(actor)
    if decision not in ("approve", "reject") or not 10 <= len(note.strip()) <= 1000:
        raise WorkflowError("Choose a review outcome and provide an appropriate message.", 400)
    with transaction.atomic():
        claim = Claim.objects.select_related("item").get(pk=claim_id)
        if claim.claimant_id == actor.pk:
            raise WorkflowError("You cannot review your own claim.", 403)
        if claim.status != Claim.Status.PENDING:
            raise WorkflowError("This claim has already been reviewed.")
        status = Claim.Status.REJECTED
        if decision == "approve":
            # A conditional write prevents two approvals from reserving one item.
            changed = FoundItem.objects.filter(pk=claim.item_id, status=FoundItem.Status.AVAILABLE).update(status=FoundItem.Status.RESERVED)
            if changed != 1:
                raise WorkflowError("This item has already been reserved or returned.")
            status = Claim.Status.APPROVED
        changed = Claim.objects.filter(pk=claim_id, status=Claim.Status.PENDING).update(
            status=status, reviewed_by=actor, reviewed_at=timezone.now(), review_note_ciphertext=encrypt_text(note.strip()),
        )
        if changed != 1:
            raise WorkflowError("Another review changed this claim. Refresh and try again.")
        if decision == "approve":
            # Other pending claimants get a final outcome without disclosure of who won.
            for other in Claim.objects.filter(item_id=claim.item_id, status=Claim.Status.PENDING):
                other.status = Claim.Status.REJECTED
                other.reviewed_by = actor
                other.reviewed_at = timezone.now()
                other.review_note_ciphertext = encrypt_text("This item is no longer available following staff review.")
                other.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note_ciphertext"])
                record(actor, "claim.closed_unavailable", other.id)
        record(actor, f"claim.{status}", claim_id)


def issue_collection_code(actor, claim_id):
    with transaction.atomic():
        claim = Claim.objects.get(pk=claim_id)
        if not actor.is_authenticated or not actor.is_active or claim.claimant_id != actor.pk:
            raise WorkflowError("Only the approved claimant can generate a collection code.", 403)
        if claim.status != Claim.Status.APPROVED:
            raise WorkflowError("A collection code requires an approved, uncollected claim.")
        token = secrets.token_urlsafe(24)
        CollectionGrant.objects.update_or_create(claim=claim, defaults={
            "digest": hashlib.sha256(token.encode()).hexdigest(),
            "expires_at": timezone.now() + timedelta(seconds=settings.COLLECTION_TOKEN_SECONDS), "used_at": None,
        })
        record(actor, "collection.code_issued", claim_id)
    return token


def collect_item(actor, claim_id, token, identity_checked):
    require_officer(actor)
    if not identity_checked:
        raise WorkflowError("Confirm the claimant and physical handover first.", 400)
    if not isinstance(token, str) or not 20 <= len(token) <= 80:
        raise WorkflowError("The collection code is invalid, expired or already used.", 400)
    with transaction.atomic():
        claim = Claim.objects.get(pk=claim_id)
        if claim.claimant_id == actor.pk:
            raise WorkflowError("Another property officer must confirm your collection.", 403)
        if claim.status != Claim.Status.APPROVED:
            raise WorkflowError("This claim is not awaiting collection.")
        now = timezone.now()
        # First write consumes a matching, unexpired token exactly once. All following
        # state and audit writes commit or roll back with it. No SQLite row locks assumed.
        changed = CollectionGrant.objects.filter(
            claim=claim, digest=hashlib.sha256(token.encode()).hexdigest(), used_at__isnull=True, expires_at__gt=now,
        ).update(used_at=now)
        if changed != 1:
            raise WorkflowError("The collection code is invalid, expired or already used.", 400)
        changed = Claim.objects.filter(pk=claim.pk, status=Claim.Status.APPROVED).update(
            status=Claim.Status.COLLECTED, collected_by=actor, collected_at=now,
        )
        if changed != 1 or FoundItem.objects.filter(pk=claim.item_id, status=FoundItem.Status.RESERVED).update(status=FoundItem.Status.RETURNED) != 1:
            raise WorkflowError("The item state changed. Refresh before continuing.")
        record(actor, "collection.completed", claim_id)
