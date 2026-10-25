"""Authenticator and recovery operations. Codes and counter updates are atomic."""
import hashlib
import re
import secrets
import time
from datetime import timedelta

import pyotp
from django.db import transaction
from django.utils import timezone

from .crypto import decrypt_text, encrypt_text
from .models import AccountSecurity, RecoveryCode, User
from .services import WorkflowError, record


def security_state(user):
    return AccountSecurity.objects.get_or_create(user=user)[0]


def needs_mfa(user, state):
    return user.is_officer or state.enabled


def is_verified(request, state):
    return (state.enabled and request.session.get("mfa_user_id") == request.user.pk
            and request.session.get("mfa_version") == state.version)


def mark_verified(request, state):
    if state.user_id != request.user.pk or not state.enabled:
        raise ValueError("MFA proof belongs to another account.")
    request.session.cycle_key()
    request.session["mfa_user_id"] = request.user.pk
    request.session["mfa_version"] = state.version


def landing(user):
    return "audit" if user.is_administrator else "staff_queue" if user.is_officer else "dashboard"


def _counter(secret, code, last=-1):
    if not re.fullmatch(r"[0-9]{6}", code):
        return None
    current = int(time.time()) // 30
    generator = pyotp.TOTP(secret)
    for counter in range(current - 1, current + 2):
        if counter > last and secrets.compare_digest(generator.at(counter * 30), code):
            return counter
    return None


def _digest(user, code):
    if not isinstance(code, str):
        return ""
    normalised = code.replace("-", "").replace(" ", "").lower()
    if not re.fullmatch(r"[0-9a-f]{32}", normalised):
        return ""
    return hashlib.sha256(f"claimsafe.recovery:{user.pk}:{normalised}".encode()).hexdigest()


def _consume_recovery(user, code):
    digest = _digest(user, code)
    return bool(digest and RecoveryCode.objects.filter(user=user, digest=digest, used_at__isnull=True).update(used_at=timezone.now()) == 1)


def _new_recovery_codes(user):
    RecoveryCode.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
    values = []
    for _ in range(10):
        raw = secrets.token_hex(16)
        RecoveryCode.objects.create(user=user, digest=_digest(user, raw))
        values.append("-".join(raw[i:i + 4] for i in range(0, 32, 4)))
    return values


def _current_actor(user):
    current = User.objects.get(pk=user.pk)
    if not current.is_active or not secrets.compare_digest(current.password, user.password):
        raise WorkflowError("Your account changed. Sign in again before managing security.", 403)
    return current


def begin_setup(user, password):
    if not user.is_active or not user.check_password(password):
        raise WorkflowError("Check your current password and try again.", 400)
    with transaction.atomic():
        user = _current_actor(user)
        state = security_state(user)
        if state.enabled:
            raise WorkflowError("An authenticator is already set up. Use account recovery if the device is lost.", 409)
        state.pending_secret_ciphertext = encrypt_text(pyotp.random_base32())
        handle = secrets.token_urlsafe(32)
        state.pending_session_digest = hashlib.sha256(handle.encode()).hexdigest()
        state.pending_expires_at = timezone.now() + timedelta(minutes=10)
        state.save(update_fields=["pending_secret_ciphertext", "pending_expires_at", "pending_session_digest"])
        record(user, "mfa.setup_started")
    return handle


def pending_secret(state, handle):
    if (not handle or not state.pending_session_digest or not state.pending_secret_ciphertext
            or not state.pending_expires_at or state.pending_expires_at <= timezone.now()
            or not secrets.compare_digest(hashlib.sha256(handle.encode()).hexdigest(), state.pending_session_digest)):
        return ""
    return decrypt_text(state.pending_secret_ciphertext)


def confirm_setup(user, code, handle):
    with transaction.atomic():
        user = _current_actor(user)
        state = security_state(user)
        secret = pending_secret(state, handle)
        if state.enabled or not secret:
            raise WorkflowError("Start authenticator setup again; the setup key has expired.", 400)
        counter = _counter(secret, code)
        if counter is None:
            raise WorkflowError("Enter a fresh six-digit code from this authenticator setup.", 400)
        state.totp_secret_ciphertext = state.pending_secret_ciphertext
        state.pending_secret_ciphertext = ""
        state.pending_session_digest = ""
        state.pending_expires_at = None
        state.last_totp_counter = counter
        state.version += 1
        state.save()
        codes = _new_recovery_codes(user)
        record(user, "mfa.enabled")
    return state, codes


def verify_factor(user, code):
    if not user.is_active or not isinstance(code, str):
        return False
    code = code.strip()
    with transaction.atomic():
        try:
            user = _current_actor(user)
        except WorkflowError:
            return False
        state = security_state(user)
        if not state.enabled:
            return False
        if re.fullmatch(r"[0-9]{6}", code):
            counter = _counter(decrypt_text(state.totp_secret_ciphertext), code, state.last_totp_counter)
            if counter is None:
                return False
            accepted = AccountSecurity.objects.filter(user=user, version=state.version, last_totp_counter__lt=counter).update(last_totp_counter=counter) == 1
        else:
            accepted = _consume_recovery(user, code)
        if accepted:
            record(user, "mfa.factor_verified")
        # Carry this exact credential version to the session. Re-reading a newer
        # version after verification could accidentally adopt a concurrent reset.
        return state if accepted else None


def replace_recovery_codes(user, password, code=""):
    if not user.is_active or not user.check_password(password):
        raise WorkflowError("Check your current password and try again.", 400)
    with transaction.atomic():
        user = _current_actor(user)
        state = security_state(user)
        if state.enabled and not verify_factor(user, code):
            raise WorkflowError("Use a fresh authenticator code or an unused recovery code.", 400)
        values = _new_recovery_codes(user)
        state.version += 1
        state.save(update_fields=["version"])
        record(user, "account.recovery_codes_replaced")
    return state, values


def recover_account(user, code, password):
    """A saved high-entropy code authorises recovery, not an email-address assertion."""
    with transaction.atomic():
        if user is None:
            return False
        # Re-read active/password state under the transaction, then invalidate every
        # saved code and MFA proof as part of the same account reset.
        user = User.objects.get(pk=user.pk)
        if not user.is_active or not _consume_recovery(user, code):
            return False
        user.set_password(password)
        user.save(update_fields=["password"])
        state = security_state(user)
        state.totp_secret_ciphertext = ""
        state.pending_secret_ciphertext = ""
        state.pending_session_digest = ""
        state.pending_expires_at = None
        state.last_totp_counter = -1
        state.version += 1
        state.save()
        RecoveryCode.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
        record(user, "account.recovered")
    return True
