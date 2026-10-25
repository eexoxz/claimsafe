"""Fetch a pinned Caddy build and verify the publisher's SHA-512 checksum."""
import hashlib
from pathlib import Path
import urllib.request
import zipfile

VERSION = "2.11.7"
NAME = f"caddy_{VERSION}_windows_amd64.zip"
URL = f"https://github.com/caddyserver/caddy/releases/download/v{VERSION}/{NAME}"
SHA512 = "c308154504e53755958ffc62d8a2657ab17eefd6dd25c45dbb2c3d93d29519971f77ca652f7d0f2bcb7f980b9ba3822478865e29969d0272d7613550a43152b1"
directory = Path(__file__).resolve().parents[1] / ".local/tools"
directory.mkdir(parents=True, exist_ok=True)
archive = directory / NAME
if not archive.exists():
    with urllib.request.urlopen(URL, timeout=120) as response, archive.open("xb") as stream:
        while block := response.read(1024 * 1024):
            stream.write(block)
if hashlib.sha512(archive.read_bytes()).hexdigest() != SHA512:
    raise SystemExit("Caddy archive checksum mismatch. The download was not executed.")
target = directory / "caddy/caddy.exe"
with zipfile.ZipFile(archive) as package:
    executable = package.read("caddy.exe")
    if not target.exists() or hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(executable).digest():
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(executable)
print(f"Verified Caddy {VERSION}: {target}")
