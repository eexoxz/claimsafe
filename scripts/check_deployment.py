"""Gate the loopback HTTPS profile, preserving explicit HSTS policy exceptions."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.conf import settings
from django.core.checks import run_checks

if not settings.PRODUCTION or set(settings.ALLOWED_HOSTS) != {"localhost", "127.0.0.1"}:
    raise SystemExit("This check policy applies only to the explicit loopback HTTPS profile.")
exceptions = {
    "security.W005": "Localhost has no project-controlled subdomain estate; do not impose domain-wide HSTS.",
    "security.W021": "A local demonstration is not eligible for public browser HSTS preloading.",
}
messages = run_checks(include_deployment_checks=True)
unexpected = [m for m in messages if m.id not in exceptions]
for message in messages:
    print(f"{message.id}: {exceptions.get(message.id, str(message))}")
if unexpected:
    raise SystemExit("Unexpected deployment check finding; startup refused.")
print(f"Deployment checks passed with {len(messages)} documented localhost HSTS policy exceptions.")
