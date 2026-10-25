import os
import atexit
import json
from pathlib import Path
from django.core.wsgi import get_wsgi_application
from .state_lock import StateLock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
_state = Path(os.environ.get("CLAIMSAFE_STATE_DIR", Path(__file__).resolve().parents[1] / ".local")).resolve()
_lease = StateLock(_state).acquire()
atexit.register(_lease.close)
application = get_wsgi_application()
# runserver may load settings before obtaining the lease. Refresh the field-key
# snapshot after the lease so it cannot start with keys read before a rotation.
if not os.environ.get("CLAIMSAFE_ENCRYPTION_KEY"):
    from django.conf import settings
    _live = json.loads(settings.SECRETS_FILE.read_text(encoding="utf-8"))
    settings.FIELD_ENCRYPTION_KEY = _live["encryption_key"]
    settings.FIELD_ENCRYPTION_FALLBACK_KEYS = _live.get("retired_encryption_keys", [])
