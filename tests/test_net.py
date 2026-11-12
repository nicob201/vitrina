import threading
import unittest
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from vitrina.net import fetch


def serve(handler_class):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_class)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class RedirectTest(unittest.TestCase):
    def setUp(self):
        self.seen = []
        seen = self.seen

        class Target(BaseHTTPRequestHandler):
            def do_GET(self):
                seen.append(self.headers.get("Authorization"))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")

            def log_message(self, *args):
                pass

        self.target = serve(Target)
        target_url = f"http://127.0.0.1:{self.target.server_address[1]}/x"

        class Redirect(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", target_url)
                self.end_headers()

            def log_message(self, *args):
                pass

        self.redirect = serve(Redirect)
        self.url = f"http://127.0.0.1:{self.redirect.server_address[1]}/"

    def tearDown(self):
        for s in (self.target, self.redirect):
            s.shutdown()
            s.server_close()

    def test_token_is_never_sent_to_a_redirect_target(self):
        with self.assertRaises(urllib.error.HTTPError):
            fetch(self.url, {"Authorization": "Bearer tok"})
        self.assertEqual(self.seen, [])

    def test_redirects_without_a_token_still_work(self):
        self.assertEqual(fetch(self.url), b"ok")
        self.assertEqual(self.seen, [None])


if __name__ == "__main__":
    unittest.main()
