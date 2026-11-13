import time

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .crypto import decrypt_text, encrypt_text
from .account_security import needs_mfa, security_state
from .forms import ClaimForm, CollectionForm, ItemForm, RegistrationForm, ReviewForm
from .models import AuditEvent, Claim, FoundItem, User
from .services import WorkflowError, collect_item, issue_collection_code, record, review_claim, submit_claim, throttle


def failure(request, status, message):
    return render(request, "error.html", {"error_status": status, "error_message": message}, status=status)


def denied(request, action, target=""):
    record(request.user, action, target, "denied")
    raise PermissionDenied


def staff_only(request):
    if not request.user.is_officer:
        denied(request, "access.staff_denied")


def admin_only(request):
    if not request.user.is_administrator:
        denied(request, "access.admin_denied")


def scoped_claim(request, pk):
    claims = Claim.objects.select_related("item", "claimant", "reviewed_by")
    if not request.user.is_officer:
        claims = claims.filter(claimant=request.user)
    claim = claims.filter(pk=pk).first()
    if claim is None:
        record(request.user, "access.claim_denied", pk, "denied")
        raise Http404
    return claim


@require_http_methods(["GET"])
def home(request):
    items = FoundItem.objects.exclude(status=FoundItem.Status.RETURNED)
    query = request.GET.get("q", "").strip()[:80]
    category = request.GET.get("category", "")[:20]
    if query:
        items = items.filter(Q(title__icontains=query) | Q(location__icontains=query) | Q(public_description__icontains=query))
    if category in FoundItem.Category.values:
        items = items.filter(category=category)
    else:
        category = ""
    return render(request, "home.html", {
        "items": Paginator(items, 9).get_page(request.GET.get("page")), "query": query,
        "category": category, "categories": FoundItem.Category.choices,
        "open_count": FoundItem.objects.filter(status=FoundItem.Status.AVAILABLE).count(),
    })


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST":
        if not throttle("registration", request.META.get("REMOTE_ADDR", "unknown"), 10, 3600):
            record(None, "registration.throttled", outcome="denied")
            return failure(request, 429, "Too many registration attempts. Please try again later.")
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.Role.STUDENT
            with transaction.atomic():
                # Initial form validation happened before hashing the password.
                # Recheck inside the write transaction before inserting the account.
                if User.objects.filter(Q(username__iexact=user.username) | Q(email__iexact=user.email)).exists():
                    form.add_error(None, "That username or email is unavailable. Use different details or sign in.")
                else:
                    user.save()
                    record(user, "account.registered")
            if not form.errors:
                messages.success(request, "Your student account is ready. You can now sign in.")
                return redirect("login")
    return render(request, "form.html", {"form": form, "title": "Create a student account", "submit_label": "Create account", "kind": "register"})


@require_http_methods(["GET", "POST"])
def sign_in(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST":
        ip_ok = throttle("login-ip", request.META.get("REMOTE_ADDR", "unknown"), 30)
        identity = form.fields["username"].to_python(request.POST.get("username", "")[:150]).casefold()
        account_ok = ip_ok and throttle("login-account", identity, 5)
        if not ip_ok or not account_ok:
            record(None, "auth.throttled", outcome="denied")
            return failure(request, 429, "Too many sign-in attempts. Please wait 15 minutes before trying again.")
        if form.is_valid():
            login(request, form.get_user())
            request.session["authenticated_at"] = time.time()
            request.session["session_version"] = request.user.session_version
            state = security_state(request.user)
            if needs_mfa(request.user, state):
                record(request.user, "auth.password_verified")
                return redirect("mfa_challenge" if state.enabled else "mfa_setup")
            record(request.user, "auth.login")
            if request.user.is_administrator:
                return redirect("audit")
            if request.user.is_officer:
                return redirect("staff_queue")
            return redirect("dashboard")
        record(None, "auth.login_failed", outcome="denied")
    return render(request, "form.html", {"form": form, "title": "Sign in", "submit_label": "Sign in", "kind": "login"})


@require_POST
@login_required
def sign_out(request):
    record(request.user, "auth.logout")
    logout(request)
    return redirect("home")


@require_http_methods(["GET"])
@login_required
def dashboard(request):
    claims = Claim.objects.filter(claimant=request.user).select_related("item")
    events = AuditEvent.objects.filter(actor=request.user)[:6]
    counts = claims.aggregate(
        pending_count=Count("pk", filter=Q(status=Claim.Status.PENDING)),
        approved_count=Count("pk", filter=Q(status=Claim.Status.APPROVED)),
        collected_count=Count("pk", filter=Q(status=Claim.Status.COLLECTED)),
    )
    return render(request, "dashboard.html", {
        "claims": Paginator(claims, 10).get_page(request.GET.get("page")), "events": events, **counts,
    })


@require_http_methods(["GET"])
def item_detail(request, pk):
    item = get_object_or_404(FoundItem, pk=pk)
    own_claim = Claim.objects.filter(item=item, claimant=request.user).first() if request.user.is_authenticated else None
    private_details = None
    if request.user.is_authenticated and request.user.is_officer:
        private_details = decrypt_text(item.identifying_details_ciphertext)
        record(request.user, "evidence.item_viewed", item.id)
    return render(request, "item_detail.html", {"item": item, "own_claim": own_claim, "private_details": private_details})


@require_http_methods(["GET", "POST"])
@login_required
def claim_new(request, pk):
    item = get_object_or_404(FoundItem, pk=pk)
    form = ClaimForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not throttle("claim-submit", request.user.pk, 20, 3600):
            record(request.user, "claim.throttled", outcome="denied")
            return failure(request, 429, "Too many claims. Please try again later.")
        try:
            claim = submit_claim(request.user, item.id, form.cleaned_data["proof"])
        except WorkflowError as error:
            record(request.user, "claim.submit_denied", item.id, "denied")
            return failure(request, error.status, str(error))
        messages.success(request, "Your private claim has been sent to the property desk.")
        return redirect("claim_detail", pk=claim.pk)
    return render(request, "form.html", {"form": form, "title": f"Claim {item.title}", "intro": "Only you and authorised property staff can view your evidence.", "submit_label": "Submit private claim"})


@require_http_methods(["GET", "POST"])
@login_required
def item_new(request):
    staff_only(request)
    form = ItemForm(request.POST or None, initial={"found_on": timezone.localdate()})
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            item = form.save(commit=False)
            item.recorded_by = request.user
            item.identifying_details_ciphertext = encrypt_text(form.cleaned_data["identifying_details"])
            item.save()
            record(request.user, "item.recorded", item.id)
        messages.success(request, "Item recorded. Check the public listing for identifying details before sharing it.")
        return redirect("item_detail", pk=item.pk)
    return render(request, "form.html", {"form": form, "title": "Record found item", "intro": "Record items already in the property desk’s custody.", "submit_label": "Record item"})


def claim_context(request, claim, token=None):
    private_details = None
    if request.user.is_officer:
        private_details = decrypt_text(claim.item.identifying_details_ciphertext)
        record(request.user, "evidence.claim_viewed", claim.id)
    return {
        "claim": claim, "proof": decrypt_text(claim.proof_ciphertext),
        "review_note": decrypt_text(claim.review_note_ciphertext), "private_details": private_details,
        "review_form": ReviewForm(), "collection_form": CollectionForm(), "collection_token": token,
    }


@require_http_methods(["GET"])
@login_required
def claim_detail(request, pk):
    claim = scoped_claim(request, pk)
    return render(request, "claim_detail.html", claim_context(request, claim))


@require_POST
@login_required
def review(request, pk):
    staff_only(request)
    claim = scoped_claim(request, pk)
    form = ReviewForm(request.POST)
    if not form.is_valid():
        return failure(request, 400, "Provide a valid decision and a message of 10 to 1,000 characters.")
    try:
        review_claim(request.user, claim.pk, form.cleaned_data["decision"], form.cleaned_data["note"])
    except WorkflowError as error:
        record(request.user, "claim.review_denied", pk, "denied")
        return failure(request, error.status, str(error))
    messages.success(request, "Claim reviewed. The claimant can now see the outcome.")
    return redirect("claim_detail", pk=pk)


@require_POST
@login_required
def issue_code(request, pk):
    claim = scoped_claim(request, pk)
    if claim.claimant_id != request.user.pk:
        denied(request, "collection.issue_denied", pk)
    if not throttle("code-issue", request.user.pk, 5):
        record(request.user, "collection.issue_throttled", pk, "denied")
        return failure(request, 429, "Too many new collection codes. Try again in 15 minutes.")
    try:
        token = issue_collection_code(request.user, pk)
    except WorkflowError as error:
        record(request.user, "collection.issue_denied", pk, "denied")
        return failure(request, error.status, str(error))
    return render(request, "claim_detail.html", claim_context(request, claim, token))


@require_POST
@login_required
def collect(request, pk):
    staff_only(request)
    scoped_claim(request, pk)
    if not throttle("collection-attempt", f"{request.user.pk}:{pk}", 10):
        record(request.user, "collection.throttled", pk, "denied")
        return failure(request, 429, "Too many collection attempts. Please try again later.")
    form = CollectionForm(request.POST)
    if not form.is_valid():
        return failure(request, 400, "Enter a valid collection code and confirm the physical handover.")
    try:
        collect_item(request.user, pk, form.cleaned_data["token"], form.cleaned_data["identity_checked"])
    except WorkflowError as error:
        record(request.user, "collection.denied", pk, "denied")
        return failure(request, error.status, str(error))
    messages.success(request, "Handover recorded. This collection code can no longer be used.")
    return redirect("claim_detail", pk=pk)


@require_http_methods(["GET"])
@login_required
def staff_queue(request):
    staff_only(request)
    status = request.GET.get("status", "pending")
    if status not in Claim.Status.values:
        status = "pending"
    claims = Claim.objects.filter(status=status).select_related("item", "claimant")
    counts = Claim.objects.filter(status__in=[Claim.Status.PENDING, Claim.Status.APPROVED]).aggregate(
        pending_count=Count("pk", filter=Q(status=Claim.Status.PENDING)),
        approved_count=Count("pk", filter=Q(status=Claim.Status.APPROVED)),
    )
    return render(request, "staff_queue.html", {
        "claims": Paginator(claims, 15).get_page(request.GET.get("page")), "status": status,
        "statuses": Claim.Status.choices, **counts,
        "returned_count": FoundItem.objects.filter(status=FoundItem.Status.RETURNED).count(),
    })


@require_http_methods(["GET"])
@login_required
def audit_dashboard(request):
    admin_only(request)
    events = AuditEvent.objects.select_related("actor")
    outcome = request.GET.get("outcome", "")
    if outcome in ("success", "denied"):
        events = events.filter(outcome=outcome)
    else:
        outcome = ""
    counts = AuditEvent.objects.aggregate(total=Count("id"), denied=Count("id", filter=Q(outcome="denied")),
                                          handovers=Count("id", filter=Q(action="collection.completed")))
    return render(request, "audit.html", {"events": Paginator(events, 20).get_page(request.GET.get("page")), "counts": counts, "outcome": outcome})


@require_http_methods(["GET"])
@login_required
def users(request):
    admin_only(request)
    accounts = User.objects.order_by("username")
    return render(request, "users.html", {"accounts": Paginator(accounts, 25).get_page(request.GET.get("page"))})


@require_POST
@login_required
def toggle_user(request, pk):
    admin_only(request)
    desired = {"0": False, "1": True}.get(request.POST.get("active"))
    with transaction.atomic():
        target = get_object_or_404(User, pk=pk)
        protected = target.role == User.Role.ADMIN or target.pk == request.user.pk
        if not protected and desired is not None and target.is_active != desired:
            target.is_active = desired
            # Reactivation also invalidates sessions from before this field existed.
            target.session_version += 1
            target.save(update_fields=["is_active", "session_version"])
            record(request.user, "account.activated" if desired else "account.deactivated", target.pk)
    if protected:
        denied(request, "account.change_denied", target.pk)
    if desired is None:
        return failure(request, 400, "Refresh the accounts page and choose whether to activate or deactivate this account.")
    messages.success(request, "Account access updated.")
    page = request.GET.get("page")
    return redirect(reverse("users", query={"page": page}) if page else "users")


@require_http_methods(["GET"])
def privacy(request):
    return render(request, "privacy.html")


def error400(request, exception):
    return failure(request, 400, "We could not process that request. Check your input and try again.")


def error403(request, exception):
    return failure(request, 403, "This request is not permitted. Sign in with an authorised account and use a fresh form.")


def csrf_failure(request, reason=""):
    return failure(request, 403, "This form could not be verified. Reload the page and submit a fresh form.")


def error404(request, exception):
    return failure(request, 404, "This page is unavailable or you do not have access to it.")


def error500(request):
    return failure(request, 500, "Something went wrong. Please try again later or contact the property desk.")
