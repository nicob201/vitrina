import errno
import io
import json
import shutil
import socket
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from tests.tls import make_cert
from vitrina.app import main
from vitrina.pairing import PairingError, save_secret

REPO = Path(__file__).resolve().parent.parent


class PortTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        shutil.copy(REPO / "config.example.json", self.root / "config.example.json")
        (self.root / "web").mkdir()
        (self.root / "web" / "index.html").write_text("<!doctype html>")
        self.secrets = self.root / "secrets"

    def tearDown(self):
        self._tmp.cleanup()

    def pair_for_tests(self):
        make_cert(self.secrets)
        save_secret(self.secrets, "k" * 43)

    def run_main(self, port, argv=(), paired=True, wifi=True):
        (self.root / "config.json").write_text(json.dumps({"port": port, "wifi": wifi}))
        if paired:
            self.pair_for_tests()
        out, result = io.StringIO(), {}

        def target():
            with redirect_stdout(out):
                result["code"] = main(list(argv), self.root, self.secrets)

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(3)
        self.assertFalse(thread.is_alive(), "server started instead of refusing the port")
        return result["code"], out.getvalue()

    def test_port_held_by_another_app_on_localhost(self):
        # macOS lets 0.0.0.0:P bind next to someone else's 127.0.0.1:P; the cable would reach the other app.
        other = socket.socket()
        other.bind(("127.0.0.1", 0))
        other.listen()
        try:
            code, out = self.run_main(other.getsockname()[1])
        finally:
            other.close()
        self.assertEqual(code, 1)
        self.assertIn("already in use", out)

    def test_other_bind_errors_are_reported_without_traceback(self):
        with mock.patch("vitrina.app.make_server", side_effect=OSError(errno.EACCES, "Permission denied")):
            code, out = self.run_main(8999)
        self.assertEqual(code, 1)
        self.assertIn("Can't use port 8999", out)

    def assert_port_free(self, port):
        with socket.socket() as s:
            s.bind(("0.0.0.0", port))

    def free_port(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def test_refuses_to_start_unpaired(self):
        port = self.free_port()
        code, out = self.run_main(port, paired=False)
        self.assertEqual(code, 1)
        self.assertIn("python3 server.py pair", out)
        self.assert_port_free(port)

    def test_a_missing_certificate_counts_as_unpaired(self):
        self.pair_for_tests()
        (self.secrets / "key.pem").unlink()
        port = self.free_port()
        code, out = self.run_main(port, paired=False)
        self.assertEqual(code, 1)
        self.assertIn("python3 server.py pair", out)
        self.assert_port_free(port)

    def test_a_broken_certificate_is_a_message(self):
        self.pair_for_tests()
        (self.secrets / "cert.pem").write_text("not a certificate")
        code, out = self.run_main(self.free_port(), paired=False)
        self.assertEqual(code, 1)
        self.assertIn("python3 server.py pair", out)
        self.assertNotIn("Traceback", out)

    def test_pair_errors_are_messages(self):
        with mock.patch("vitrina.app.pair", side_effect=PairingError("Plug in the phone and allow USB debugging.")):
            code, out = self.run_main(8765, ["pair"], paired=False)
        self.assertEqual(code, 1)
        self.assertIn("Plug in the phone and allow USB debugging.", out)

    def test_pair_success_says_restart(self):
        with mock.patch("vitrina.app.pair", return_value="fp") as pair, \
                mock.patch("vitrina.app.net.lan_ip", return_value="192.168.0.10"):
            code, out = self.run_main(8765, ["pair"], paired=False)
        self.assertEqual(code, 0)
        pair.assert_called_once_with(self.secrets, 8765, "192.168.0.10")
        self.assertIn("restart", out)
        self.assertIn("https://192.168.0.10:8765", out)

    def test_pair_without_wifi_sends_no_address(self):
        with mock.patch("vitrina.app.pair", return_value="fp") as pair, \
                mock.patch("vitrina.app.net.lan_ip", return_value="192.168.0.10"):
            code, out = self.run_main(8765, ["pair"], paired=False, wifi=False)
        self.assertEqual(code, 0)
        pair.assert_called_once_with(self.secrets, 8765, None)
        self.assertNotIn("192.168.0.10", out)

    def test_unknown_argument(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["nope"], self.root, self.secrets), 2)
        self.assertIn("Usage: python3 server.py [pair]", out.getvalue())
        self.assertFalse((self.root / "config.json").exists())  # nothing done


if __name__ == "__main__":
    unittest.main()
