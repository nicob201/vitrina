from __future__ import annotations

import hmac
import ipaddress
import json
import mimetypes
import re
import ssl
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urlsplit

# Fixed here because Python also reads MIME types from the Windows registry, which can be wrong.
_TYPES = {
    ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".svg": "image/svg+xml",
    ".woff2": "font/woff2", ".txt": "text/plain", ".json": "application/json",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
}
# Seconds a client may stay silent before its connection (and thread) is dropped.
REQUEST_TIMEOUT = 30
# Requests from the PC itself arrive through `adb reverse`, i.e. over the cable.
_LOCAL = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}


def tls_context(cert: Path, key: Path) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(cert, key)
    return ctx


def make_server(
    host: str,
    port: int,
    web_dir: Path,
    get_state: Callable[[str | None, str], dict],
    photo_path: Callable[[int], Path | None],
    tls: ssl.SSLContext,
    secret: str,
) -> ThreadingHTTPServer:
    """HTTPS only, and only for whoever presents the paired key. There is no unencrypted mode."""
    if not secret:
        raise ValueError("a pairing key is required")
    expected = secret.encode("utf-8")
    root = web_dir.resolve()
    # The request path never touches the filesystem: only files listed here at startup are served.
    # (On Windows a path like \\host\share would otherwise make the PC connect to that host.)
    files = {
        "/" + p.relative_to(root).as_posix(): p
        for p in root.rglob("*")
        if p.is_file() and p.resolve().is_relative_to(root)
    }
    files["/"] = root / "index.html"

    class Handler(BaseHTTPRequestHandler):
        timeout = REQUEST_TIMEOUT
        error_message_format = ""  # errors before the key check (bad method, huge line) say nothing either

        def version_string(self) -> str:
            return "vitrina"  # not "BaseHTTP/0.6 Python/3.9.6"

        def setup(self) -> None:
            # The handshake runs in this connection's own thread, under the timeout,
            # so a slow or silent client never holds up the others.
            self.request.settimeout(self.timeout)
            self.request = tls.wrap_socket(self.request, server_side=True)
            super().setup()

        def finish(self) -> None:
            try:
                super().finish()
            finally:
                self.request.close()  # the server only knows the plain socket, which TLS took over

        # Read-only on purpose: only GET is defined, everything else gets 501.
        def do_GET(self) -> None:
            if not _local_host(self.headers.get("Host")):
                self._send(403, "text/plain; charset=utf-8", b"forbidden")
                return
            if not self._has_key():
                self._send(401, "text/plain; charset=utf-8", b"")
                return
            path = unquote(urlsplit(self.path).path)
            if path == "/api/state":
                link = "usb" if self.client_address[0] in _LOCAL else "wifi"
                state = get_state(self.headers.get("Accept-Language"), link)
                body = json.dumps(state, ensure_ascii=False).encode("utf-8")
                self._send(200, "application/json; charset=utf-8", body, {"Cache-Control": "no-store"})
                return
            photo = re.fullmatch(r"/api/photo/(\d+)", path)
            if photo:
                self._send_file(photo_path(int(photo.group(1))))
                return
            self._send_file(files.get(path))

        def _has_key(self) -> bool:
            offered = []
            # Parsed by hand: SimpleCookie takes quadratic time on some inputs (CVE-2024-7592),
            # and this runs before the key is known to be good.
            for part in (self.headers.get("Cookie") or "").split(";"):
                name, _, value = part.strip().partition("=")
                if name == "vitrina_key":
                    offered.append(value)
            auth = self.headers.get("Authorization") or ""
            if auth.startswith("Bearer "):
                offered.append(auth[len("Bearer "):])
            # Bytes, so a non-ASCII value is just a wrong key (compare_digest refuses non-ASCII str).
            return any(hmac.compare_digest(k.encode("utf-8"), expected) for k in offered)

        def _send_file(self, file: Path | None) -> None:
            if file is None or not file.is_file():
                self._send(404, "text/plain; charset=utf-8", b"not found")
                return
            ctype = _TYPES.get(file.suffix.lower()) or mimetypes.guess_type(file.name)[0] or "application/octet-stream"
            if ctype.startswith("text/"):
                ctype += "; charset=utf-8"
            self._send(200, ctype, file.read_bytes())

        def _send(self, status: int, ctype: str, body: bytes, headers: dict | None = None) -> None:
            try:
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(body)
            except OSError:
                pass  # the client went away or timed out mid-response; nothing to do

        def log_message(self, format, *args) -> None:
            pass  # keep the console for things the user needs to see

    class Server(ThreadingHTTPServer):
        # On Windows SO_REUSEADDR lets a second server silently share the port;
        # elsewhere it only allows a quick restart after Ctrl+C.
        allow_reuse_address = sys.platform != "win32"

        def handle_error(self, request, client_address) -> None:
            # Failed handshakes (plain HTTP, port scanners) and dropped connections are not news.
            if isinstance(sys.exc_info()[1], OSError):
                return
            super().handle_error(request, client_address)

    return Server((host, port), Handler)


def _local_host(host: str | None) -> bool:
    """Accept IP addresses, localhost and .local names; refuse other names (DNS rebinding)."""
    if not host:
        return True
    name = host[1:].split("]")[0] if host.startswith("[") else host.rsplit(":", 1)[0]
    if name == "localhost" or name.endswith(".local"):
        return True
    try:
        ipaddress.ip_address(name)
        return True
    except ValueError:
        return False
