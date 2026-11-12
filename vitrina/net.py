from __future__ import annotations

import json
import socket
import urllib.request


def fetch(url: str, headers: dict[str, str] | None = None, timeout: float = 15) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "vitrina", **(headers or {})})
    with urllib.request.urlopen(request, timeout=timeout) as response:
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
