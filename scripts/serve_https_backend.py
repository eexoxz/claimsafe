"""Loopback-only WSGI backend, reached through the authenticated HTTPS proxy."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.conf import settings
from waitress import serve
from config.proxy import ProxyGuard
from config.wsgi import application

if not settings.PRODUCTION:
    raise SystemExit("Use run-https.ps1 to supply the secure deployment configuration.")

serve(
    ProxyGuard(application, settings.LOCAL_SECRETS.get("proxy_token")),
    listen="127.0.0.1:9010",
    threads=4,
    trusted_proxy="127.0.0.1",
    trusted_proxy_count=1,
    trusted_proxy_headers={"x-forwarded-proto", "x-forwarded-for"},
    clear_untrusted_proxy_headers=True,
    max_request_body_size=64 * 1024,
    max_request_header_size=32 * 1024,
    connection_limit=100,
    channel_timeout=30,
    expose_tracebacks=False,
    ident="ClaimSafe",
)
