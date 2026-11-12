import subprocess
import unittest

from vitrina.adb import ensure_reverse


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


if __name__ == "__main__":
    unittest.main()
