import time

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import Resolver404, resolve


class SessionBoundaryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            started = request.session.get("authenticated_at")
            if (not started or time.time() - started > settings.SESSION_ABSOLUTE_SECONDS
                    or request.session.get("session_version", 0) != request.user.session_version):
                logout(request)
                return redirect("login")
        return self.get_response(request)


class ResponseSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Validate Host even on routes that never construct an absolute URL.
        request.get_host()
        response = self.get_response(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'none'; style-src 'self'; img-src 'self' data:; "
            "font-src 'self'; connect-src 'self'; base-uri 'none'; object-src 'none'; "
            "frame-ancestors 'none'; form-action 'self'"
        )
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store, private"
        return response


class MFABoundaryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            from .account_security import is_verified, needs_mfa, security_state
            state = security_state(request.user)
            if needs_mfa(request.user, state) and not is_verified(request, state):
                try:
                    route = resolve(request.path_info).url_name
                except Resolver404:
                    route = None
                if route not in {"mfa_setup", "mfa_challenge", "account_recovery", "privacy", "logout"}:
                    return redirect("mfa_challenge" if state.enabled else "mfa_setup")
        return self.get_response(request)
