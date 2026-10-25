import time

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect


class SessionBoundaryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            started = request.session.get("authenticated_at")
            if not started or time.time() - started > settings.SESSION_ABSOLUTE_SECONDS:
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
