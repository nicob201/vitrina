import subprocess
import unittest

from vitrina.adb import ensure_reverse, release


class FakeRun:
    def __init__(self, devices_out, reverse_code=0, error=None):
        self.calls = []
        self.devices_out, self.reverse_code, self.error = devices_out, reverse_code, error

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        if self.error:
            raise self.error
        if cmd[1] == "devices":
            return subprocess.CompletedProcess(cmd, 0, self.devices_out, "")
        return subprocess.CompletedProcess(cmd, self.reverse_code, "", "")


def which(name):
    return "/usr/local/bin/adb"


class EnsureReverseTest(unittest.TestCase):
    def test_no_adb_installed(self):
        run = FakeRun("")
        self.assertFalse(ensure_reverse(8765, run=run, which=lambda name: None))
        self.assertEqual(run.calls, [])

    def test_no_device(self):
        run = FakeRun("List of devices attached\n\n")
        self.assertFalse(ensure_reverse(8765, run=run, which=which))
        self.assertEqual(len(run.calls), 1)

    def test_unauthorized_is_not_a_device(self):
        run = FakeRun("List of devices attached\nABC\tunauthorized\n\n")
        self.assertFalse(ensure_reverse(8765, run=run, which=which))
        self.assertEqual(len(run.calls), 1)

    def test_device_gets_reverse(self):
        run = FakeRun("List of devices attached\nABC\tdevice\n\n")
        self.assertTrue(ensure_reverse(8765, run=run, which=which))
        self.assertEqual(run.calls[-1], ["adb", "reverse", "tcp:8765", "tcp:8765"])

    def test_adb_errors_are_false(self):
        for run in (
            FakeRun("", error=subprocess.TimeoutExpired("adb", 5)),
            FakeRun("", error=FileNotFoundError("adb")),
            FakeRun("List of devices attached\nABC\tdevice\n", reverse_code=1),
        ):
            with self.subTest(run=run):
                self.assertFalse(ensure_reverse(8765, run=run, which=which))


class ReleaseTest(unittest.TestCase):
    def test_release_without_adb_or_daemon_runs_nothing(self):
        # Running adb with no daemon up would start one: the opposite of releasing.
        for kwargs in ({"which": lambda name: None, "running": lambda: True},
                       {"which": which, "running": lambda: False}):
            with self.subTest(kwargs=kwargs):
                run = FakeRun("")
                release(8765, True, run=run, **kwargs)
                self.assertEqual(run.calls, [])

    def test_release_kills_the_daemon_vitrina_opened(self):
        run = FakeRun("")
        release(8765, True, run=run, which=which, running=lambda: True)
        self.assertEqual(run.calls[-1], ["adb", "kill-server"])

    def test_release_leaves_someone_elses_daemon(self):
        run = FakeRun("")
        release(8765, False, run=run, which=which, running=lambda: True)
        self.assertEqual(run.calls, [["adb", "reverse", "--remove", "tcp:8765"]])

    def test_release_ignores_errors(self):
        for error in (subprocess.TimeoutExpired("adb", 5), FileNotFoundError("adb")):
            with self.subTest(error=error):
                release(8765, True, run=FakeRun("", error=error), which=which, running=lambda: True)


if __name__ == "__main__":
    unittest.main()
