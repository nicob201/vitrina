from __future__ import annotations

import errno
import sys
import threading
from datetime import datetime
from pathlib import Path

from . import adb, net
from .claude import USAGE_URL, parse_usage, read_token, usage_headers
from .config import ConfigError, load_config
from .github import contributions_url, parse_contributions
from .handler import make_server
from .i18n import pick_language
from .loops import run_every
from .photos import PhotoLibrary
from .state import Store, build_state
from .weather import forecast_url, geocode_url, parse_forecast, parse_place

ROOT = Path(__file__).resolve().parent.parent
_PORT_IN_USE = {errno.EADDRINUSE, getattr(errno, "WSAEADDRINUSE", errno.EADDRINUSE)}


def log(message: str) -> None:
    print(message, flush=True)


def main() -> int:
    try:
        cfg, created = load_config(ROOT / "config.json", ROOT / "config.example.json")
    except ConfigError as e:
        log(f"config.json: {e}")
        return 1
    if created:
        log("Created config.json. Edit it to turn on GitHub, Claude, weather and photos, then restart.")

    store = Store()
    photos = PhotoLibrary(Path(cfg.photos_dir).expanduser() if cfg.photos_dir else None)

    def get_state(accept_language: str | None, link: str) -> dict:
        lang = pick_language(cfg.language, accept_language)
        return build_state(store, cfg, lang, link, datetime.now().astimezone(), photos.count())

    # Bind first: if the port is taken, say so before anything else starts.
    try:
        server = make_server("0.0.0.0" if cfg.wifi else "127.0.0.1", cfg.port, ROOT / "web", get_state, photos.path)
    except OSError as e:
        if e.errno in _PORT_IN_USE:
            log(f'Port {cfg.port} is already in use. Change "port" in config.json.')
            return 1
        raise

    stop = threading.Event()
    _start_sources(cfg, store, photos, stop)

    log("vitrina is running")
    ip = net.lan_ip() if cfg.wifi else None
    if ip:
        log(f"  WiFi:  http://{ip}:{cfg.port}")
    log(f"  Cable: http://localhost:{cfg.port}")
    log("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Stopped.")
    finally:
        stop.set()
        server.server_close()
    return 0


def _start_sources(cfg, store: Store, photos: PhotoLibrary, stop: threading.Event) -> None:
    if cfg.github_user:
        def github() -> None:
            html = net.fetch(contributions_url(cfg.github_user)).decode("utf-8")
            store.set("github_days", parse_contributions(html))
        run_every(1800, github, "GitHub", log, stop)

    if cfg.claude:
        def claude() -> None:
            token = read_token(sys.platform, Path.home())
            if token is None:
                raise RuntimeError("Claude Code token not found")
            store.set("claude_usage", parse_usage(net.fetch_json(USAGE_URL, usage_headers(token))))
        run_every(300, claude, "Claude", log, stop)

    if cfg.city:
        place: dict = {}  # resolved once; a network error leaves it empty so the next round retries

        def weather() -> None:
            if "found" not in place:
                lang = cfg.language if cfg.language in ("es", "en") else "en"
                place["found"] = parse_place(net.fetch_json(geocode_url(cfg.city, lang)), cfg.country)
                found = place["found"]
                log(f"Weather: {found.label}" if found else f"Weather: city not found: {cfg.city}")
            if place["found"] is not None:
                store.set("weather", parse_forecast(net.fetch_json(forecast_url(place["found"], cfg.units))))
        run_every(900, weather, "Weather", log, stop)

    run_every(60, photos.rescan, "Photos", log, stop)

    usb = {"connected": False}

    def cable() -> None:
        connected = adb.ensure_reverse(cfg.port)
        if connected != usb["connected"]:
            usb["connected"] = connected
            log("USB: phone connected" if connected else "USB: phone disconnected")
    run_every(10, cable, "USB", log, stop)
