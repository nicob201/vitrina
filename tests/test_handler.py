import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from vitrina import handler
from vitrina.handler import make_server


class HandlerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.web = root / "web"
        (self.web / "fonts").mkdir(parents=True)
        (self.web / "index.html").write_text("<!doctype html><title>v</title>")
        (self.web / "a.css").write_text("body{}")
        (self.web / "fonts" / "f.woff2").write_bytes(b"wOF2")
        (root / "secret.txt").write_text("secret")
        (self.web / "link.txt").symlink_to(root / "secret.txt")
        self.photo = root / "photo.jpg"
        self.photo.write_bytes(b"\xff\xd8jpeg")

        self.state_calls = []

        def get_state(accept_language, link):
            self.state_calls.append((accept_language, link))
            return {"panels": ["clock"], "text": "sin conexión"}

        self.server = make_server("127.0.0.1", 0, self.web, get_state,
                                  lambda i: self.photo if i == 0 else None)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self._tmp.cleanup()

    def get(self, path, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=5)
        conn.request("GET", path, headers=headers or {})
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        return resp, body

    def test_index(self):
        resp, body = self.get("/")
        self.assertEqual(resp.status, 200)
        self.assertTrue(resp.getheader("Content-Type").startswith("text/html"))
        self.assertIn(b"<title>v</title>", body)

    def test_static_files(self):
        resp, _ = self.get("/a.css?v=2")
        self.assertEqual((resp.status, resp.getheader("Content-Type").split(";")[0]), (200, "text/css"))
        resp, body = self.get("/fonts/f.woff2")
        self.assertEqual((resp.status, resp.getheader("Content-Type"), body), (200, "font/woff2", b"wOF2"))

    def test_state_passes_language_and_link(self):
        resp, body = self.get("/api/state", {"Accept-Language": "es-AR"})
        self.assertEqual(resp.status, 200)
        self.assertEqual(self.state_calls, [("es-AR", "usb")])
        self.assertEqual(resp.getheader("Cache-Control"), "no-store")
        self.assertTrue(resp.getheader("Content-Type").startswith("application/json"))
        self.assertEqual(json.loads(body.decode("utf-8")), {"panels": ["clock"], "text": "sin conexión"})

    def test_state_without_accept_language(self):
        self.get("/api/state")
        self.assertEqual(self.state_calls, [(None, "usb")])

    def test_photo(self):
        resp, body = self.get("/api/photo/0")
        self.assertEqual((resp.status, resp.getheader("Content-Type"), body), (200, "image/jpeg", b"\xff\xd8jpeg"))
        self.assertEqual(self.get("/api/photo/9")[0].status, 404)
        self.assertEqual(self.get("/api/photo/x")[0].status, 404)

    def test_no_path_traversal(self):
        for raw in ("/../secret.txt", "/%2e%2e/secret.txt", "/..%2fsecret.txt",
                    "/api/photo/../../secret.txt", "/link.txt", "//etc/passwd"):
            with self.subTest(raw=raw):
                resp, body = self.get(raw)
                self.assertEqual(resp.status, 404)
                self.assertNotIn(b"secret", body)

    def test_unknown_path_and_directories_404(self):
        for path in ("/nope.js", "/fonts", "/fonts/"):
            with self.subTest(path=path):
                self.assertEqual(self.get(path)[0].status, 404)

    def test_windows_style_and_nul_paths_404(self):
        # On Windows a path like \\host\share would make the PC reach out to that host.
        for raw in ("/%5C%5C127.0.0.1%5Cx", "/%00", "/a.css%00", "/C:%5Cwindows", "/%5Ca.css"):
            with self.subTest(raw=raw):
                self.assertEqual(self.get(raw)[0].status, 404)

    def test_foreign_host_names_are_refused(self):
        # DNS rebinding: a web page on evil.example pointing its name at this PC.
        self.assertEqual(self.get("/api/state", {"Host": "evil.example:8765"})[0].status, 403)
        for host in ("localhost:8765", "127.0.0.1:8765", "192.168.0.10:8765", "[::1]:8765", "mi-mac.local:8765"):
            with self.subTest(host=host):
                self.assertEqual(self.get("/api/state", {"Host": host})[0].status, 200)

    def test_content_types_do_not_depend_on_the_system(self):
        # Python reads MIME types from the Windows registry, which can say text/plain for .css.
        with mock.patch("mimetypes.guess_type", return_value=("text/plain", None)):
            self.assertTrue(self.get("/a.css")[0].getheader("Content-Type").startswith("text/css"))
            self.assertTrue(self.get("/")[0].getheader("Content-Type").startswith("text/html"))

    def test_second_server_on_same_port_fails(self):
        with self.assertRaises(OSError):
            make_server("127.0.0.1", self.server.server_address[1], self.web, lambda a, l: {}, lambda i: None)

    def test_windows_does_not_share_the_port(self):
        # On Windows SO_REUSEADDR lets a second server silently bind the same port.
        with mock.patch.object(handler.sys, "platform", "win32"):
            s = make_server("127.0.0.1", 0, self.web, lambda a, l: {}, lambda i: None)
        s.server_close()
        self.assertFalse(s.allow_reuse_address)


if __name__ == "__main__":
    unittest.main()
