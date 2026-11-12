from __future__ import annotations

import json
import socket
import urllib.request


class _KeepTokenHome(urllib.request.HTTPRedirectHandler):
    """urllib copies Authorization to wherever a redirect points; a token must never leave like that."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if req.has_header("Authorization"):
            return None  # urllib then raises HTTPError for the 3xx
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_KeepTokenHome)


def fetch(url: str, headers: dict[str, str] | None = None, timeout: float = 15) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "vitrina", **(headers or {})})
    with _opener.open(request, timeout=timeout) as response:
        return response.read()


def fetch_json(url: str, headers: dict[str, str] | None = None):
    return json.loads(fetch(url, headers).decode("utf-8"))


def lan_ip() -> str | None:
    """This PC's address on the local network. Connecting a UDP socket sends nothing."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        return None if ip.startswith("127.") else ip
    except OSError:
        return None
    finally:
        s.close()
