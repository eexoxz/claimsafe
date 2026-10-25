"""Prepare a local HTTPS profile while holding its maintenance lease."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config.state_lock import StateLock


def main():
    state = Path(os.environ["CLAIMSAFE_STATE_DIR"]).resolve()
    commands = [
        ["scripts/initialize.py", "--proxy-token"],
        ["manage.py", "migrate", "--noinput"],
        ["manage.py", "prune_security_state"],
    ]
    if not (state / "demo-accounts.txt").exists() and not (state / "RESTORE_NOTES.txt").exists():
        commands.append(["manage.py", "seed_demo"])
    commands.append(["manage.py", "collectstatic", "--noinput"])
    with StateLock(state):
        for command in commands:
            subprocess.run([sys.executable, *command], cwd=ROOT, check=True)
    if (state / "RESTORE_NOTES.txt").exists():
        print("Restored profile: review RESTORE_NOTES.txt and reconcile account/custody changes before use. No demo records were added.")


if __name__ == "__main__":
    main()
