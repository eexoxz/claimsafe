import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        OFFICER = "officer", "Property officer"
        ADMIN = "admin", "Administrator"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.STUDENT)

    @property
    def is_officer(self):
        return self.is_active and self.role in (self.Role.OFFICER, self.Role.ADMIN)

    @property
    def is_administrator(self):
        return self.is_active and self.role == self.Role.ADMIN


class FoundItem(models.Model):
    class Category(models.TextChoices):
        ELECTRONICS = "electronics", "Electronics"
        ACCESSORIES = "accessories", "Accessories"
        BOOKS = "books", "Books & stationery"
        OTHER = "other", "Other belongings"

    class Status(models.TextChoices):
        AVAILABLE = "available", "Open for claims"
        RESERVED = "reserved", "Awaiting collection"
        RETURNED = "returned", "Returned"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=90)
    category = models.CharField(max_length=20, choices=Category.choices)
    public_description = models.CharField(max_length=300)
    location = models.CharField(max_length=80)
    found_on = models.DateField()
    identifying_details_ciphertext = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.AVAILABLE)
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="recorded_items")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def short_reference(self):
        return str(self.id).split("-")[0].upper()


class Claim(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Under review"
        APPROVED = "approved", "Ready to collect"
        REJECTED = "rejected", "Not approved"
        COLLECTED = "collected", "Collected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(FoundItem, on_delete=models.PROTECT, related_name="claims")
    claimant = models.ForeignKey(User, on_delete=models.PROTECT, related_name="claims")
    proof_ciphertext = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    review_note_ciphertext = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="reviewed_claims")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    collected_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="handed_over_claims")
    collected_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["item", "claimant"], name="one_claim_per_person_and_item"),
            models.UniqueConstraint(fields=["item"], condition=Q(status__in=["approved", "collected"]), name="one_winning_claim_per_item"),
        ]

    @property
    def short_reference(self):
        return str(self.id).split("-")[0].upper()


class CollectionGrant(models.Model):
    claim = models.OneToOneField(Claim, on_delete=models.CASCADE, related_name="collection_grant")
    digest = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AuditEvent(models.Model):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50)
    outcome = models.CharField(max_length=12, choices=[("success", "Success"), ("denied", "Denied")])
    target = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class RateBucket(models.Model):
    """Persisted, HMAC-keyed throttling state; raw usernames/IP addresses are not stored."""
    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField()


class AccountSecurity(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name="account_security")
    totp_secret_ciphertext = models.TextField(blank=True)
    pending_secret_ciphertext = models.TextField(blank=True)
    pending_session_digest = models.CharField(max_length=64, blank=True)
    pending_expires_at = models.DateTimeField(null=True, blank=True)
    last_totp_counter = models.BigIntegerField(default=-1)
    version = models.PositiveIntegerField(default=1)

    @property
    def enabled(self):
        return bool(self.totp_secret_ciphertext)


class RecoveryCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recovery_codes")
    digest = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
