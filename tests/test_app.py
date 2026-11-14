import errno
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from tests.tls import make_cert
from vitrina.app import main
from vitrina.control import hold_lock, running_pid
from vitrina.pairing import PairingError, save_secret
from vitrina.photos import PhotoLibrary

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
        self.assertIn("Usage: python3 server.py [start | stop | pair]", out.getvalue())
        self.assertFalse((self.root / "config.json").exists())  # nothing done

    def test_stop_needs_no_config(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["stop"], self.root, self.secrets), 0)
        self.assertIn("vitrina isn't running.", out.getvalue())
        self.assertFalse((self.root / "config.json").exists())

    def test_start_launches_server_py(self):
        with mock.patch("vitrina.app.control.start", return_value=0) as start, redirect_stdout(io.StringIO()):
            self.assertEqual(main(["start"], self.root, self.secrets), 0)
        start.assert_called_once_with([sys.executable, str(self.root / "server.py")], self.secrets)
        self.assertFalse((self.root / "config.json").exists())

    def test_refuses_a_second_server(self):
        lock = hold_lock(self.secrets)
        port = self.free_port()
        try:
            code, out = self.run_main(port)
        finally:
            lock.close()
        self.assertEqual(code, 1)
        self.assertIn("already running", out)
        self.assert_port_free(port)

    def serve_until_long_sleep(self, config):
        """Run the real server until it holds the lock, then report a long sleep; returns what it did."""
        (self.root / "config.json").write_text(json.dumps(config))
        self.pair_for_tests()
        woke, out, result = {}, io.StringIO(), {}

        def target():
            with redirect_stdout(out):
                result["code"] = main([], self.root, self.secrets)

        with mock.patch("vitrina.app.control.watch_sleep", side_effect=lambda cb, stop: woke.setdefault("cb", cb)), \
                mock.patch("vitrina.app.adb.daemon_running", return_value=False), \
                mock.patch("vitrina.app.adb.ensure_reverse", return_value=False), \
                mock.patch("vitrina.app.adb.release") as release, \
                mock.patch("vitrina.app.PhotoLibrary", wraps=PhotoLibrary) as photos:
            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            for _ in range(300):
                if running_pid(self.secrets) == os.getpid():
                    break
                threading.Event().wait(0.01)
            self.assertEqual(running_pid(self.secrets), os.getpid(), "server never took the lock")
            woke["cb"]()
            thread.join(3)
        self.assertFalse(thread.is_alive(), "server kept running after the long sleep")
        return result["code"], out.getvalue(), release, photos

    def test_long_sleep_stops_and_releases_everything(self):
        port = self.free_port()
        code, out, release, _ = self.serve_until_long_sleep({"port": port, "wifi": False})
        self.assertEqual(code, 0)
        self.assertIn("slept for over an hour", out)
        self.assertIn("Stopped.", out)
        release.assert_called_once_with(port, True)  # vitrina opened adb's daemon, so it closes it
        self.assert_port_free(port)
        self.assertIsNone(running_pid(self.secrets))

    def test_relative_photos_dir_is_next_to_config(self):
        # Started from any folder, "fotos" still means the folder beside config.json.
        _, _, _, photos = self.serve_until_long_sleep({"port": self.free_port(), "wifi": False, "photos_dir": "fotos"})
        photos.assert_called_once_with(self.root / "fotos")

    def test_runs_through_a_link_from_another_folder(self):
        link = self.root / "vitrina"
        link.symlink_to(REPO / "server.py")
        done = subprocess.run([str(link), "nope"], cwd=self.root, capture_output=True, text=True, timeout=10)
        self.assertEqual(done.returncode, 2, done.stderr)
        self.assertIn("Usage: python3 server.py [start | stop | pair]", done.stdout)


if __name__ == "__main__":
    unittest.main()
