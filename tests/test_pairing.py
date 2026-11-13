import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from vitrina.pairing import PairingError, ensure_cert, fingerprint, pair, read_secret, save_secret


class SecretsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_cert_is_created_once_with_private_permissions(self):
        cert, key = ensure_cert(self.dir / "v")
        first = cert.read_bytes()
        self.assertEqual(ensure_cert(self.dir / "v"), (cert, key))
        self.assertEqual(cert.read_bytes(), first)  # not regenerated
        self.assertEqual(stat.S_IMODE((self.dir / "v").stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(key.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(cert.stat().st_mode), 0o600)

    def test_existing_folder_is_made_private(self):
        folder = self.dir / "v"
        folder.mkdir(mode=0o755)
        ensure_cert(folder)
        self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)

    def test_fingerprint_matches_openssl(self):
        cert, _ = ensure_cert(self.dir / "v")
        out = subprocess.run(["/usr/bin/openssl", "x509", "-in", str(cert), "-noout", "-fingerprint", "-sha256"],
                             capture_output=True, text=True, check=True).stdout
        self.assertEqual(fingerprint(cert), out.split("=")[1].strip().replace(":", "").lower())
        self.assertRegex(fingerprint(cert), r"^[0-9a-f]{64}$")

    def test_secret_round_trip_is_private(self):
        folder = self.dir / "v"
        save_secret(folder, "abc")
        save_secret(folder, "def")
        self.assertEqual(read_secret(folder), "def")
        self.assertEqual(stat.S_IMODE((folder / "secret").stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)
        self.assertEqual([p.name for p in folder.iterdir()], ["secret"])  # no temp files left behind

    def test_missing_or_empty_secret_is_none(self):
        # An empty key would let an empty cookie in, so it counts as "not paired".
        folder = self.dir / "v"
        self.assertIsNone(read_secret(folder))
        folder.mkdir()
        (folder / "secret").write_text(" \n")
        self.assertIsNone(read_secret(folder))

    def test_openssl_failure_raises_pairing_error(self):
        failed = subprocess.CompletedProcess([], 1, "", "req: unknown option\n")
        with mock.patch("vitrina.pairing.subprocess.run", return_value=failed):
            with self.assertRaises(PairingError):
                ensure_cert(self.dir / "v")


DEVICE = "List of devices attached\nR58M123\tdevice\n\n"


class FakeAdb:
    """Answers adb by subcommand and records every command line and stdin."""

    def __init__(self, devices=DEVICE, pm="package:/data/app/~~x/io.github.nicob201.vitrina/base.apk\n",
                 am="Starting: Intent { cmp=io.github.nicob201.vitrina/.PairActivity }\nStatus: ok\n", am_code=0):
        self.devices, self.pm, self.am, self.am_code = devices, pm, am, am_code
        self.calls, self.inputs = [], []

    def __call__(self, cmd, input=None, **kwargs):
        self.calls.append(cmd)
        self.inputs.append(input)
        if cmd[1:] == ["devices"]:
            return subprocess.CompletedProcess(cmd, 0, self.devices, "")
        if cmd[1:3] == ["shell", "pm"]:
            return subprocess.CompletedProcess(cmd, 0, self.pm, "")
        return subprocess.CompletedProcess(cmd, self.am_code, self.am, "")


def has_adb(name):
    return "/opt/homebrew/bin/adb"


class PairTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name) / "v"

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_adb_device_or_app_raise_and_keep_the_old_secret(self):
        save_secret(self.folder, "old")
        cases = {
            "no adb": dict(adb=FakeAdb(), which=lambda name: None),
            "no device": dict(adb=FakeAdb(devices="List of devices attached\n\n"), which=has_adb),
            "unauthorized": dict(adb=FakeAdb(devices="List of devices attached\nR58M123\tunauthorized\n"),
                                 which=has_adb),
            "two phones": dict(adb=FakeAdb(devices=DEVICE.strip() + "\nemulator-5554\tdevice\n"), which=has_adb),
            "app missing": dict(adb=FakeAdb(pm=""), which=has_adb),
        }
        for name, fake in cases.items():
            with self.subTest(name):
                with self.assertRaises(PairingError):
                    pair(self.folder, 8765, "192.168.0.10", **fake)
                self.assertEqual(read_secret(self.folder), "old")
                self.assertFalse(any("PairActivity" in " ".join(c) for c in fake["adb"].calls))

    def test_secret_goes_through_stdin_never_argv(self):
        fake = FakeAdb()
        fp = pair(self.folder, 8765, "192.168.0.10", adb=fake, which=has_adb)
        secret = read_secret(self.folder)
        self.assertGreaterEqual(len(secret), 32)
        self.assertTrue(all(secret not in " ".join(c) for c in fake.calls))
        self.assertEqual(fake.inputs[-1], secret + "\n")
        self.assertEqual(fp, fingerprint(self.folder / "cert.pem"))
        script = fake.calls[-1][2]
        self.assertIn("io.github.nicob201.vitrina/.PairActivity", script)
        self.assertIn(f"--es fingerprint {fp}", script)
        self.assertIn("--ei port 8765", script)
        self.assertIn("--es wifi_ip 192.168.0.10", script)

    def test_each_pairing_rotates_the_secret(self):
        pair(self.folder, 8765, None, adb=FakeAdb(), which=has_adb)
        first = read_secret(self.folder)
        pair(self.folder, 8765, None, adb=FakeAdb(), which=has_adb)
        self.assertNotEqual(read_secret(self.folder), first)

    def test_failed_send_keeps_the_old_secret(self):
        save_secret(self.folder, "old")
        for fake in (FakeAdb(am="Error: Activity not started\n"), FakeAdb(am_code=1)):
            with self.subTest(am=fake.am, code=fake.am_code):
                with self.assertRaises(PairingError):
                    pair(self.folder, 8765, "192.168.0.10", adb=fake, which=has_adb)
                self.assertEqual(read_secret(self.folder), "old")

    def test_adb_crash_or_hang_is_a_pairing_error(self):
        save_secret(self.folder, "old")
        for error in (OSError("boom"), subprocess.TimeoutExpired("adb", 30)):
            def broken(cmd, **kwargs):
                raise error
            with self.subTest(error=error):
                with self.assertRaises(PairingError):
                    pair(self.folder, 8765, None, adb=broken, which=has_adb)
                self.assertEqual(read_secret(self.folder), "old")

    def test_no_wifi_ip_sends_empty(self):
        fake = FakeAdb()
        pair(self.folder, 8765, None, adb=fake, which=has_adb)
        self.assertIn('--es wifi_ip ""', fake.calls[-1][2])


if __name__ == "__main__":
    unittest.main()
