from __future__ import annotations

import hashlib
import ipaddress
import os
import secrets
import shutil
import ssl
import subprocess
from pathlib import Path

# Certificate, private key and the pairing key live here, never in the repo or config.json.
SECRETS_DIR = Path.home() / "Library" / "Application Support" / "vitrina"
APP_ID = "io.github.nicob201.vitrina"


class PairingError(Exception):
    """Something the user has to fix; the message is shown as is."""


def _private_dir(folder: Path) -> None:
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    folder.chmod(0o700)  # mkdir leaves an existing folder as it was


def ensure_cert(folder: Path) -> tuple[Path, Path]:
    """Create the self-signed certificate the first time; reuse it afterwards."""
    _private_dir(folder)
    cert, key = folder / "cert.pem", folder / "key.pem"
    if _usable(cert, key):
        return cert, key
    cert.unlink(missing_ok=True)  # damaged or half made: start over (pairing sends the new fingerprint)
    key.unlink(missing_ok=True)
    try:
        done = subprocess.run(
            ["/usr/bin/openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:prime256v1",
             "-pkeyopt", "ec_param_enc:named_curve",
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


def _usable(cert: Path, key: Path) -> bool:
    try:
        fingerprint(cert)
        ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER).load_cert_chain(cert, key)  # what the server will do
        return True
    except (OSError, ValueError):  # missing, unreadable, not PEM, or not a matching pair
        return False


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


def pair(folder: Path, port: int, wifi_ip: str | None, adb=subprocess.run, which=shutil.which) -> str:
    """Hand a new key, the certificate fingerprint, the port and the WiFi address to the app over USB.

    The old key is only replaced once the app has taken the new one. Returns the fingerprint.
    """
    if which("adb") is None:
        raise PairingError("adb not found. Install it with: brew install android-platform-tools")
    try:
        out = adb(["adb", "devices"], capture_output=True, text=True, timeout=10).stdout
        # "unauthorized" or "offline" phones can't be used; only "device" can.
        ready = [line for line in out.splitlines()[1:] if line.split("\t")[-1].strip() == "device"]
        if not ready:
            raise PairingError("Plug in the phone and allow USB debugging.")
        if len(ready) > 1:
            raise PairingError("More than one phone is plugged in. Leave only the one to pair.")
        installed = adb(["adb", "shell", "pm", "path", APP_ID], capture_output=True, text=True, timeout=10).stdout
        if not installed.strip():
            raise PairingError("Install the vitrina app on the phone first.")

        fp = fingerprint(ensure_cert(folder)[0])
        secret = secrets.token_urlsafe(32)
        ip = str(ipaddress.IPv4Address(wifi_ip)) if wifi_ip else '""'
        # The key reaches the phone through stdin: it never shows up in this Mac's process list.
        # --activity-clear-task: otherwise a task left by an earlier pairing is just brought to the front
        # and the pairing screen never opens, while am still says "Status: ok".
        script = (f'read -r k; am start -W --activity-clear-task -n {APP_ID}/.PairActivity --es key "$k" '
                  f"--es fingerprint {fp} --ei port {int(port)} --es wifi_ip {ip}")
        done = adb(["adb", "shell", script], input=secret + "\n", capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        raise PairingError(f"Pairing failed: {e}") from None
    lines = done.stdout.splitlines()
    opened = "Status: ok" in lines and f"Activity: {APP_ID}/.PairActivity" in lines
    if done.returncode != 0 or not opened or "Warning: Activity not started" in done.stdout:
        raise PairingError("The phone didn't accept the pairing.")
    save_secret(folder, secret)
    return fp
