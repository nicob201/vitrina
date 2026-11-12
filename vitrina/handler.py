from __future__ import annotations

import json
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urlsplit

_TYPES = {".woff2": "font/woff2", ".js": "text/javascript", ".svg": "image/svg+xml"}
# Requests from the PC itself arrive through `adb reverse`, i.e. over the cable.
_LOCAL = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}


def make_server(
    host: str,
    port: int,
    web_dir: Path,
    get_state: Callable[[str | None, str], dict],
    photo_path: Callable[[int], Path | None],
) -> ThreadingHTTPServer:
    root = web_dir.resolve()

    class Handler(BaseHTTPRequestHandler):
        # Read-only on purpose: only GET is defined, everything else gets 501.
        def do_GET(self) -> None:
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
            if path.startswith("/api/"):
                self._send_file(None)
                return
            # Static files: only what really lives inside web/ (no "..", no symlinks out).
            target = (root / ("index.html" if path == "/" else path.lstrip("/"))).resolve()
            self._send_file(target if target.is_relative_to(root) else None)

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
            except ConnectionError:
                pass  # the phone went away mid-response; nothing to do

        def log_message(self, format, *args) -> None:
            pass  # keep the console for things the user needs to see

    return ThreadingHTTPServer((host, port), Handler)
