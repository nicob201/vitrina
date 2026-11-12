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

from vitrina.app import main

REPO = Path(__file__).resolve().parent.parent


class PortTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        shutil.copy(REPO / "config.example.json", self.root / "config.example.json")
        (self.root / "web").mkdir()
        (self.root / "web" / "index.html").write_text("<!doctype html>")

    def tearDown(self):
        self._tmp.cleanup()

    def run_main(self, port):
        (self.root / "config.json").write_text(json.dumps({"port": port}))
        out, result = io.StringIO(), {}

        def target():
            with redirect_stdout(out):
                result["code"] = main(self.root)

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


if __name__ == "__main__":
    unittest.main()
