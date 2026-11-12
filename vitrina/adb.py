from __future__ import annotations

import shutil
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
