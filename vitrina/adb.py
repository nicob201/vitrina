from __future__ import annotations

import shutil
import socket
import subprocess


def ensure_reverse(port: int, run=subprocess.run, which=shutil.which) -> bool:
    """Make the phone's localhost:<port> reach this PC over the USB cable. Safe to repeat."""
    if which("adb") is None:
        return False
    try:
        out = run(["adb", "devices"], capture_output=True, text=True, timeout=5).stdout
        # "unauthorized" or "offline" phones can't take the reverse; only "device" can.
        if not any(line.split("\t")[-1].strip() == "device" for line in out.splitlines()[1:]):
            return False
        done = run(["adb", "reverse", f"tcp:{port}", f"tcp:{port}"], capture_output=True, text=True, timeout=5)
        return done.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def daemon_running() -> bool:
    """adb's background daemon answers on its usual port."""
    try:
        with socket.create_connection(("127.0.0.1", 5037), timeout=0.5):
            return True
    except OSError:
        return False


def release(port: int, kill_daemon: bool, run=subprocess.run, which=shutil.which, running=daemon_running) -> None:
    """Undo what the server did with adb: close the daemon if vitrina opened it, else just drop the reverse."""
    # With no daemon up there's nothing to undo, and any adb command would start one.
    if which("adb") is None or not running():
        return
    cmd = ["adb", "kill-server"] if kill_daemon else ["adb", "reverse", "--remove", f"tcp:{port}"]
    try:
        run(cmd, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        pass
