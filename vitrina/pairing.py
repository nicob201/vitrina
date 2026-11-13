from __future__ import annotations

import hashlib
import os
import ssl
import subprocess
from pathlib import Path

# Certificate, private key and the pairing key live here, never in the repo or config.json.
SECRETS_DIR = Path.home() / "Library" / "Application Support" / "vitrina"


class PairingError(Exception):
    """Something the user has to fix; the message is shown as is."""


def _private_dir(folder: Path) -> None:
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    folder.chmod(0o700)  # mkdir leaves an existing folder as it was


def ensure_cert(folder: Path) -> tuple[Path, Path]:
    """Create the self-signed certificate the first time; reuse it afterwards."""
    _private_dir(folder)
    cert, key = folder / "cert.pem", folder / "key.pem"
    if cert.is_file() and key.is_file():
        return cert, key
    try:
        done = subprocess.run(
            ["/usr/bin/openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1",
             "-nodes", "-days", "3650", "-subj", "/CN=vitrina", "-keyout", str(key), "-out", str(cert)],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise PairingError(f"Couldn't create the certificate: {e}") from None
    if done.returncode != 0 or not (cert.is_file() and key.is_file()):
        detail = (done.stderr or "").strip().splitlines()
        raise PairingError("Couldn't create the certificate" + (f": {detail[-1]}" if detail else "."))
    cert.chmod(0o600)  # the folder is already 0700, so nobody else could read them in between
    key.chmod(0o600)
    return cert, key


def fingerprint(cert: Path) -> str:
    """SHA-256 of the certificate's DER bytes, lowercase hex: what the app pins."""
    return hashlib.sha256(ssl.PEM_cert_to_DER_cert(cert.read_text())).hexdigest()


def save_secret(folder: Path, secret: str) -> None:
    _private_dir(folder)
    tmp = folder / "secret.tmp"
    tmp.unlink(missing_ok=True)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)  # private from the first byte
    with os.fdopen(fd, "w") as f:
        f.write(secret)
    os.replace(tmp, folder / "secret")


def read_secret(folder: Path) -> str | None:
    try:
        secret = (folder / "secret").read_text().strip()
    except FileNotFoundError:
        return None
    return secret or None  # an empty key would match an empty cookie
