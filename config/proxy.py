"""Authenticate the local reverse proxy before the WSGI app sees a request."""
from secrets import compare_digest


class ProxyGuard:
    def __init__(self, application, token):
        if not isinstance(token, str) or len(token) < 40:
            raise ValueError("The HTTPS backend requires a generated proxy token.")
        self.application = application
        self.token = token

    def __call__(self, environ, start_response):
        supplied = environ.pop("HTTP_X_CLAIMSAFE_PROXY", "")
        # Remove the credential before passing control to Django or its error logging.
        if not isinstance(supplied, str) or not compare_digest(supplied.encode(), self.token.encode()):
            body = b"This endpoint is unavailable."
            start_response("404 Not Found", [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
            ])
            return [body]
        return self.application(environ, start_response)
