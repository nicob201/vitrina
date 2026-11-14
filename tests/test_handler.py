import http.client
import io
import json
import socket
import ssl
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

from tests.tls import make_cert
from vitrina import handler
from vitrina.handler import make_server, tls_context

KEY = "s3cret"


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

        self.cert, self.key = make_cert(root / "certs")
        self.tls = tls_context(self.cert, self.key)
        self.server = make_server("127.0.0.1", 0, self.web, get_state,
                                  lambda i: self.photo if i == 0 else None, tls=self.tls, secret=KEY)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self._tmp.cleanup()

    def get(self, path, headers=None, key=KEY):
        ctx = ssl.create_default_context(cafile=str(self.cert))
        ctx.check_hostname = False
        conn = http.client.HTTPSConnection("127.0.0.1", self.server.server_address[1], timeout=5, context=ctx)
        headers = dict(headers or {})
        if key is not None:
            headers.setdefault("Authorization", f"Bearer {key}")
        conn.request("GET", path, headers=headers)
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

    def test_idle_connections_are_closed(self):
        # A client that connects and says nothing must not hold a thread forever.
        with mock.patch.object(handler, "REQUEST_TIMEOUT", 0.3):
            s = make_server("127.0.0.1", 0, self.web, lambda a, l: {}, lambda i: None, tls=self.tls, secret=KEY)
        threading.Thread(target=s.serve_forever, daemon=True).start()
        try:
            with socket.create_connection(("127.0.0.1", s.server_address[1])) as sock:
                sock.settimeout(3)
                self.assertEqual(sock.recv(1), b"")
        finally:
            s.shutdown()
            s.server_close()

    def test_second_server_on_same_port_fails(self):
        with self.assertRaises(OSError):
            make_server("127.0.0.1", self.server.server_address[1], self.web, lambda a, l: {}, lambda i: None,
                        tls=self.tls, secret=KEY)

    def test_windows_does_not_share_the_port(self):
        # On Windows SO_REUSEADDR lets a second server silently bind the same port.
        with mock.patch.object(handler.sys, "platform", "win32"):
            s = make_server("127.0.0.1", 0, self.web, lambda a, l: {}, lambda i: None, tls=self.tls, secret=KEY)
        s.server_close()
        self.assertFalse(s.allow_reuse_address)

    def test_no_key_gets_401_everywhere(self):
        for path in ("/", "/a.css", "/api/state", "/api/photo/0", "/nope.js"):
            with self.subTest(path=path):
                resp, body = self.get(path, key=None)
                self.assertEqual((resp.status, body), (401, b""))
        self.assertEqual(self.state_calls, [])

    def test_wrong_key_gets_401(self):
        for cookie in ("vitrina_key=nope", "vitrina_key=", "vitrina_key=s3cret2", "other=s3cret", "vitrina_key=ñ",
                       'vitrina_key="unclosed'):
            with self.subTest(cookie=cookie):
                resp, body = self.get("/", {"Cookie": cookie}, key=None)
                self.assertEqual((resp.status, body), (401, b""))
        for auth in ("Bearer nope", "Bearer ", "Basic s3cret", "s3cret", "Bearer ñ"):
            with self.subTest(auth=auth):
                self.assertEqual(self.get("/", {"Authorization": auth}, key=None)[0].status, 401)

    def test_a_hostile_cookie_cannot_stall_the_server(self):
        # CVE-2024-7592: SimpleCookie in Python 3.9 takes quadratic time on quoted backslashes;
        # the server must never parse cookies at all.
        hostile = 'vitrina_key="' + "\\" * 30000 + '"'
        start = time.monotonic()
        resp, body = self.get("/api/state", {"Cookie": hostile}, key=None)
        self.assertEqual((resp.status, body), (401, b""))
        self.assertLess(time.monotonic() - start, 0.5)

    def test_strangers_learn_nothing_about_the_server(self):
        ctx = ssl.create_default_context(cafile=str(self.cert))
        ctx.check_hostname = False
        for method, path in (("GET", "/"), ("POST", "/"), ("HEAD", "/api/state"), ("GET", "/" + "x" * 70000)):
            with self.subTest(method=method, path=path[:10]):
                conn = http.client.HTTPSConnection("127.0.0.1", self.server.server_address[1], timeout=5, context=ctx)
                conn.request(method, path)
                resp = conn.getresponse()
                body = resp.read()
                conn.close()
                self.assertEqual(body, b"")
                self.assertNotIn("Python", resp.getheader("Server") or "")
                self.assertNotIn("BaseHTTP", resp.getheader("Server") or "")

    def test_a_cookie_no_longer_opens_anything(self):
        # The app sends the key only as a header; nothing about it is kept in a cookie store.
        for cookie in ("vitrina_key=s3cret", "a=1; vitrina_key=s3cret; b=2"):
            with self.subTest(cookie=cookie):
                self.assertEqual(self.get("/api/state", {"Cookie": cookie}, key=None)[0].status, 401)

    def test_bearer_header_works(self):
        resp, _ = self.get("/api/state", {"Authorization": "Bearer s3cret"}, key=None)
        self.assertEqual(resp.status, 200)

    def test_an_empty_key_is_refused(self):
        with self.assertRaises(ValueError):
            make_server("127.0.0.1", 0, self.web, lambda a, l: {}, lambda i: None, tls=self.tls, secret="")

    def test_tls_1_2_is_the_minimum(self):
        self.assertEqual(tls_context(self.cert, self.key).minimum_version, ssl.TLSVersion.TLSv1_2)

    def test_plain_http_is_dropped_quietly(self):
        with redirect_stderr(io.StringIO()) as err:
            with socket.create_connection(("127.0.0.1", self.server.server_address[1])) as s:
                s.sendall(b"GET / HTTP/1.1\r\nHost: x\r\n\r\n")
                s.settimeout(3)
                self.assertNotIn(b"HTTP/", _first_bytes(s))  # a close, reset or TLS alert; never an HTTP answer
            with socket.create_connection(("127.0.0.1", self.server.server_address[1])) as s:
                s.sendall(b"\x16\x03\x01garbage" * 10)
                s.settimeout(3)
                self.assertNotIn(b"HTTP/", _first_bytes(s))
            resp, _ = self.get("/")  # still serving
        self.assertEqual(resp.status, 200)
        self.assertNotIn("Traceback", err.getvalue())


def _first_bytes(sock):
    try:
        return sock.recv(100)
    except ConnectionResetError:  # the server hung up with our bytes unread
        return b""


if __name__ == "__main__":
    unittest.main()
