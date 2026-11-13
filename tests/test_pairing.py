import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from vitrina.pairing import PairingError, ensure_cert, fingerprint, read_secret, save_secret


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


if __name__ == "__main__":
    unittest.main()
