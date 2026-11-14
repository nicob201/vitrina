import io
import os
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from vitrina.control import hold_lock, running_pid, start, stop, watch_sleep

REPO = Path(__file__).resolve().parent.parent

# A stand-in for server.py: says it's up, then holds the lock like the real server does.
CHILD = """
import signal, sys, time
from pathlib import Path
sys.path.insert(0, {repo!r})
from vitrina.control import hold_lock
{before}
print("vitrina is running", flush=True)
lock = hold_lock(Path({folder!r}))
time.sleep(60)
"""
FAILING = "print('Not paired yet', flush=True); raise SystemExit(1)"


class LockTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name) / "secrets"

    def tearDown(self):
        self._tmp.cleanup()

    def test_lock_names_the_holder(self):
        lock = hold_lock(self.folder)
        self.assertEqual(running_pid(self.folder), os.getpid())
        self.assertEqual((self.folder / "server.pid").stat().st_mode & 0o777, 0o600)
        lock.close()
        self.assertIsNone(running_pid(self.folder))

    def test_second_lock_is_refused(self):
        lock = hold_lock(self.folder)
        try:
            self.assertIsNone(hold_lock(self.folder))
        finally:
            lock.close()

    def test_stale_pid_file_is_not_running(self):
        self.assertIsNone(running_pid(self.folder))  # no folder, no file
        self.folder.mkdir()
        (self.folder / "server.pid").write_text("12345")  # a server that died without letting go
        self.assertIsNone(running_pid(self.folder))


class StartStopTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name) / "secrets"

    def tearDown(self):
        with redirect_stdout(io.StringIO()):
            stop(self.folder, timeout=1)  # never leave a child behind
        self._tmp.cleanup()

    def child(self, before=""):
        return [sys.executable, "-c", CHILD.format(repo=str(REPO), folder=str(self.folder), before=before)]

    def call(self, fn, *args, **kwargs):
        out = io.StringIO()
        with redirect_stdout(out):
            code = fn(*args, **kwargs)
        return code, out.getvalue()

    def test_start_then_stop(self):
        code, out = self.call(start, self.child(), self.folder)
        self.assertEqual(code, 0)
        self.assertIn("vitrina is running", out)
        self.assertIn("Log: ", out)
        pid = running_pid(self.folder)
        self.assertIsNotNone(pid)
        self.assertNotEqual(os.getsid(pid), os.getsid(0))  # its own session: closing the terminal won't stop it
        self.assertEqual((self.folder / "server.log").stat().st_mode & 0o777, 0o600)

        code, out = self.call(stop, self.folder)
        self.assertEqual(code, 0)
        self.assertIn("Stopped.", out)
        self.assertIsNone(running_pid(self.folder))

    def test_start_reports_a_failed_server(self):
        code, out = self.call(start, [sys.executable, "-c", FAILING], self.folder)
        self.assertEqual(code, 1)
        self.assertIn("Not paired yet", out)

    def test_start_when_running_launches_nothing(self):
        lock = hold_lock(self.folder)
        marker = Path(self._tmp.name) / "launched"
        try:
            code, out = self.call(start, [sys.executable, "-c", f"open({str(marker)!r}, 'w')"], self.folder)
        finally:
            lock.close()
        self.assertEqual(code, 0)
        self.assertIn("vitrina is already running.", out)
        self.assertFalse(marker.exists())

    def test_log_is_replaced_each_start(self):
        self.folder.mkdir()
        (self.folder / "server.log").write_text("old")
        self.call(start, self.child(), self.folder)
        self.assertNotIn("old", (self.folder / "server.log").read_text())

    def test_stop_when_nothing_runs(self):
        code, out = self.call(stop, self.folder)
        self.assertEqual(code, 0)
        self.assertIn("vitrina isn't running.", out)

    def test_stop_kills_a_server_that_ignores_sigterm(self):
        self.call(start, self.child("signal.signal(signal.SIGTERM, signal.SIG_IGN)"), self.folder)
        self.assertIsNotNone(running_pid(self.folder))
        code, _ = self.call(stop, self.folder, timeout=1)
        self.assertEqual(code, 0)
        self.assertIsNone(running_pid(self.folder))


AWAKE = (5, 5)  # (wall-clock seconds, awake seconds) between two looks


def nap(seconds):
    return (5 + seconds, 5)


class Timeline:
    """Fake clocks: each look returns (wall, awake) after the next step; awake forever afterwards."""

    def __init__(self, *steps):
        self.steps, self.looks, self.wall, self.awake = list(steps), 0, 0.0, 0.0

    def __call__(self):
        if self.looks:
            w, a = self.steps.pop(0) if self.steps else AWAKE
            self.wall, self.awake = self.wall + w, self.awake + a
        self.looks += 1
        return self.wall, self.awake


class WatchSleepTest(unittest.TestCase):
    def watch(self, *steps):
        """Run the watcher through the steps plus a stretch awake; returns how many times it called back."""
        calls, stop_event, clock = [], threading.Event(), Timeline(*steps)
        thread = watch_sleep(lambda: calls.append(1), stop_event, clock=clock, every=0.001)
        for _ in range(5000):
            if clock.looks > len(steps) + 20 or not thread.is_alive():
                break
            stop_event.wait(0.001)
        stop_event.set()
        thread.join(1)
        self.assertFalse(thread.is_alive())
        return len(calls)

    def test_long_sleep_calls_back_once(self):
        self.assertEqual(self.watch(AWAKE, AWAKE, nap(4000)), 1)

    def test_dark_wakes_dont_count_as_waking(self):
        # Power Nap wakes the Mac for a few seconds every ~20 min while it sleeps.
        dark_wake = [AWAKE] * 4
        self.assertEqual(self.watch(nap(1000), *dark_wake, nap(1000), *dark_wake, nap(1000), *dark_wake, nap(1000)), 1)

    def test_five_minutes_awake_resets_the_count(self):
        self.assertEqual(self.watch(nap(3000), *[AWAKE] * 61, nap(3000)), 0)

    def test_short_gaps_never_call_back(self):
        self.assertEqual(self.watch(*[AWAKE] * 20), 0)

if __name__ == "__main__":
    unittest.main()
