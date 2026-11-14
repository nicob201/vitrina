from __future__ import annotations

import fcntl
import os
import signal
import threading
import time
from pathlib import Path
from typing import IO, Callable

from .pairing import _private_dir

# The running server holds a lock on this file; the system lets go when the process ends, however it ends.
PIDFILE = "server.pid"
LOGFILE = "server.log"


def hold_lock(folder: Path) -> IO[str] | None:
    """Mark this process as the running server for as long as the returned file stays open."""
    _private_dir(folder)
    fd = os.open(folder / PIDFILE, os.O_RDWR | os.O_CREAT, 0o600)
    os.fchmod(fd, 0o600)
    f = os.fdopen(fd, "r+")
    # running_pid() takes a shared lock for an instant; a few tries tell that apart from a real server.
    for _ in range(10):
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            time.sleep(0.05)
    else:
        f.close()
        return None
    f.truncate(0)
    f.write(str(os.getpid()))
    f.flush()
    return f


def running_pid(folder: Path) -> int | None:
    """The running server's process id, or None. A pid file nobody holds is left over, not running."""
    try:
        f = open(folder / PIDFILE)
    except FileNotFoundError:
        return None
    with f:
        try:
            fcntl.flock(f, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            text = f.read().strip()
            return int(text) if text.isdigit() else None
        return None  # we got the lock, so no server holds it; closing lets go


def start(cmd: list[str], folder: Path, timeout: float = 10.0) -> int:
    """Launch the server in the background, detached from this terminal, and wait until it serves."""
    if running_pid(folder) is not None:
        print("vitrina is already running.")
        return 0
    _private_dir(folder)
    log_path = folder / LOGFILE
    fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    try:
        # Its own session (setsid): closing the terminal or Ctrl+C here doesn't reach it.
        pid = os.posix_spawn(cmd[0], cmd, os.environ, setsid=True, file_actions=[
            (os.POSIX_SPAWN_OPEN, 0, os.devnull, os.O_RDONLY, 0),
            (os.POSIX_SPAWN_DUP2, fd, 1),
            (os.POSIX_SPAWN_DUP2, fd, 2),
        ])
    finally:
        os.close(fd)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        done, status = os.waitpid(pid, os.WNOHANG)
        if done:
            print(_read(log_path), end="")
            return os.waitstatus_to_exitcode(status) or 1
        if running_pid(folder) == pid:
            print(_read(log_path), end="")
            print(f"Log: {log_path}")
            return 0
        time.sleep(0.1)
    print(_read(log_path), end="")
    print(f"vitrina is taking long to start. Log: {log_path}")
    return 1


def stop(folder: Path, timeout: float = 10.0) -> int:
    """Stop the running server wherever it was started; kill it if it doesn't stop in time."""
    pid = running_pid(folder)
    if pid is None:
        print("vitrina isn't running.")
        return 0
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            break  # already gone
        if _gone(folder, timeout):
            break
    else:
        print(f"Couldn't stop vitrina (process {pid}).")
        return 1
    print("Stopped.")
    return 0


def _clocks() -> tuple[float, float]:
    # The second clock stops while the Mac sleeps, so the difference is time spent asleep.
    return time.time(), time.clock_gettime(time.CLOCK_UPTIME_RAW)


def watch_sleep(
    on_long_sleep: Callable[[], None],
    stop: threading.Event,
    clock: Callable[[], tuple[float, float]] = _clocks,
    every: float = 5.0,
    limit: float = 3600.0,
    settle: float = 300.0,
) -> threading.Thread:
    """Call on_long_sleep once when the Mac has slept more than limit seconds without really waking up.

    While asleep, macOS wakes for a few seconds every so often (Power Nap); those don't count as waking:
    only settle seconds awake in a row start the count over.
    """

    def watch() -> None:
        last_wall, last_awake = clock()
        slept = awake_run = 0.0
        while not stop.wait(every):
            wall, awake = clock()
            awake_gap = awake - last_awake
            slept_gap = (wall - last_wall) - awake_gap
            last_wall, last_awake = wall, awake
            if slept_gap > 1.0:
                slept += slept_gap
                awake_run = 0.0
            else:
                awake_run += awake_gap
                if awake_run >= settle:
                    slept = 0.0
            if slept > limit:
                on_long_sleep()
                return

    thread = threading.Thread(target=watch, name="Sleep", daemon=True)
    thread.start()
    return thread


def _gone(folder: Path, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if running_pid(folder) is None:
            return True
        time.sleep(0.1)
    return False


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")
