import base64
import secrets
from functools import wraps
from io import BytesIO

import pyotp
import qrcode
from qrcode.image.svg import SvgPathImage
from django import forms
from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm, UsernameField
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .account_security import (begin_setup, confirm_setup, is_verified, landing, mark_verified,
                               pending_secret, recover_account, replace_recovery_codes, security_state, verify_factor)
from .models import RecoveryCode, User
from .services import WorkflowError, record, throttle
from .views import failure


class FactorForm(forms.Form):
    code = forms.CharField(label="Authenticator or recovery code", max_length=80,
                           widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "autocapitalize": "none", "spellcheck": "false"}))


class SetupPasswordForm(forms.Form):
    password = forms.CharField(label="Current password", widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))


class RecoveryCodesForm(SetupPasswordForm):
    code = forms.CharField(label="Fresh authenticator or unused recovery code", required=False, max_length=80, widget=forms.TextInput(attrs={"autocomplete": "one-time-code"}))


class ChangePasswordForm(PasswordChangeForm):
    code = forms.CharField(label="Fresh authenticator or unused recovery code", required=False, max_length=80, widget=forms.TextInput(attrs={"autocomplete": "one-time-code"}))


class AccountRecoveryForm(SetPasswordForm):
    username = UsernameField(max_length=150)
    recovery_code = forms.CharField(label="Saved recovery code", max_length=80, widget=forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false"}))
    field_order = ["username", "recovery_code", "new_password1", "new_password2"]


def secure_account_page(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.is_secure():
            return failure(request, 403, "Open the HTTPS site to manage account security.")
        return view(request, *args, **kwargs)
    return wrapped


def limited(request, scope, identity, limit=5, seconds=300):
    address = request.META.get("REMOTE_ADDR", "unknown")
    if not throttle(scope + "-ip", address, 30, 900) or not throttle(scope, identity, limit, seconds):
        record(request.user, scope + ".throttled", outcome="denied")
        return True
    return False


def recovery_response(request, codes):
    return render(request, "recovery_codes.html", {"codes": codes})


@require_http_methods(["GET", "POST"])
@login_required
@secure_account_page
def mfa_setup(request):
    state = security_state(request.user)
    if state.enabled:
        return redirect("account_security" if is_verified(request, state) else "mfa_challenge")
    start_form = SetupPasswordForm()
    confirm_form = FactorForm()
    if request.method == "POST":
        if limited(request, "mfa.setup", request.user.pk):
            return failure(request, 429, "Too many setup attempts. Wait five minutes before trying again.")
        action = request.POST.get("action")
        form = SetupPasswordForm(request.POST) if action == "start" else FactorForm(request.POST)
        if form.is_valid():
            try:
                if action == "start":
                    request.session["mfa_setup_handle"] = begin_setup(request.user, form.cleaned_data["password"])
                elif action == "confirm":
                    state, codes = confirm_setup(request.user, form.cleaned_data["code"], request.session.get("mfa_setup_handle", ""))
                    request.session.pop("mfa_setup_handle", None)
                    mark_verified(request, state)
                    record(request.user, "auth.login")
                    return recovery_response(request, codes)
                else:
                    raise WorkflowError("Choose a setup action.", 400)
            except WorkflowError as error:
                form.add_error(None, str(error))
        if action == "start":
            start_form = form
        else:
            confirm_form = form
        state.refresh_from_db()
    secret = ""
    qr = ""
    confirm_form.fields["code"].label = "Six-digit authenticator code"
    confirm_form.fields["code"].widget.attrs["inputmode"] = "numeric"
    secret = pending_secret(state, request.session.get("mfa_setup_handle", ""))
    if secret:
        uri = pyotp.TOTP(secret).provisioning_uri(name=request.user.username, issuer_name="ClaimSafe")
        image = qrcode.make(uri, image_factory=SvgPathImage)
        stream = BytesIO()
        image.save(stream)
        qr = "data:image/svg+xml;base64," + base64.b64encode(stream.getvalue()).decode()
    return render(request, "mfa_setup.html", {"start_form": start_form, "confirm_form": confirm_form, "setup_secret": secret, "qr": qr})


@require_http_methods(["GET", "POST"])
@login_required
@secure_account_page
def mfa_challenge(request):
    state = security_state(request.user)
    if not state.enabled:
        return redirect("mfa_setup" if request.user.is_officer else "account_security")
    if is_verified(request, state):
        return redirect(landing(request.user))
    form = FactorForm(request.POST or None)
    if request.method == "POST":
        if limited(request, "mfa.challenge", request.user.pk):
            return failure(request, 429, "Too many verification attempts. Wait five minutes before trying again.")
        proof = verify_factor(request.user, form.cleaned_data["code"]) if form.is_valid() else None
        if proof:
            mark_verified(request, proof)
            record(request.user, "auth.login")
            return redirect(landing(request.user))
        record(request.user, "mfa.failed", outcome="denied")
        form.add_error(None, "Use a fresh authenticator code or an unused recovery code. Each code is accepted once.")
    return render(request, "form.html", {"form": form, "title": "Verify your sign-in", "intro": "Use a fresh code from your authenticator app or an unused recovery code.", "submit_label": "Verify sign in", "kind": "mfa"})


@require_http_methods(["GET", "POST"])
@login_required
@secure_account_page
def account_security(request):
    state = security_state(request.user)
    form = RecoveryCodesForm(request.POST or None)
    if not state.enabled:
        form.fields["code"].widget = forms.HiddenInput()
    if request.method == "POST":
        if limited(request, "account.codes", request.user.pk):
            return failure(request, 429, "Too many security changes. Wait five minutes before trying again.")
        if form.is_valid():
            try:
                state, codes = replace_recovery_codes(request.user, form.cleaned_data["password"], form.cleaned_data.get("code", ""))
                if state.enabled:
                    mark_verified(request, state)
                return recovery_response(request, codes)
            except WorkflowError as error:
                form.add_error(None, str(error))
    return render(request, "account_security.html", {"state": state, "form": form, "remaining_codes": RecoveryCode.objects.filter(user=request.user, used_at__isnull=True).count()})


@require_http_methods(["GET", "POST"])
@login_required
@secure_account_page
def password_change(request):
    state = security_state(request.user)
    form = ChangePasswordForm(request.user, request.POST or None)
    if not state.enabled:
        form.fields["code"].widget = forms.HiddenInput()
    if request.method == "POST":
        if limited(request, "account.password", request.user.pk):
            return failure(request, 429, "Too many password changes. Wait five minutes before trying again.")
        if form.is_valid():
            with transaction.atomic():
                current = User.objects.get(pk=request.user.pk)
                current_state = security_state(current)
                if not current.is_active or not secrets.compare_digest(current.password, request.user.password):
                    form.add_error(None, "Your account changed during this request. Sign in again before changing the password.")
                elif current_state.enabled and not verify_factor(request.user, form.cleaned_data.get("code", "")):
                    form.add_error("code", "Use a fresh authenticator code or an unused recovery code.")
                else:
                    user = form.save()
                    record(user, "account.password_changed")
            if not form.errors:
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed. Other signed-in sessions will need to sign in again.")
                return redirect("account_security")
    return render(request, "form.html", {"form": form, "title": "Change password", "intro": "Use at least 15 characters for your new password.", "submit_label": "Change password", "kind": "account"})


@require_http_methods(["GET", "POST"])
@secure_account_page
def account_recovery(request):
    # Invalid codes and unknown accounts get the same response. An email address alone
    # never authorises a reset, and recovery cannot reactivate a suspended account.
    form = AccountRecoveryForm(None, request.POST or None)
    if request.method == "POST":
        identity = form.fields["username"].to_python(request.POST.get("username", "")[:150]).casefold()
        if limited(request, "account.recovery", identity):
            return failure(request, 429, "Too many recovery attempts. Wait five minutes before trying again.")
        if form.is_valid():
            username = form.cleaned_data["username"]
            user = User.objects.filter(username=username).first()
            if user is None:
                matches = list(User.objects.filter(username__iexact=username)[:2])
                user = matches[0] if len(matches) == 1 else None
            try:
                recovered = recover_account(user, form.cleaned_data["recovery_code"], form.cleaned_data["new_password1"])
            except ValidationError as error:
                form.add_error("new_password2", error)
            else:
                if recovered:
                    logout(request)
                else:
                    record(None, "account.recovery_failed", outcome="denied")
                return render(request, "recovery_done.html")
    return render(request, "form.html", {"form": form, "title": "Recover account", "intro": "Use a saved code to reset your password and authenticator. Recovery invalidates your other codes. If you have no codes, contact the local operator.", "submit_label": "Recover account", "kind": "account"})
