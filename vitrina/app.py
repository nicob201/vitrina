from __future__ import annotations

import errno
import socket
import sys
import threading
from datetime import datetime
from pathlib import Path

from . import adb, control, net
from .claude import USAGE_URL, parse_usage, read_token, usage_headers
from .config import ConfigError, load_config
from .github import contributions_url, parse_contributions
from .handler import make_server, tls_context
from .i18n import pick_language
from .loops import run_every
from .pairing import SECRETS_DIR, PairingError, pair, read_secret
from .photos import PhotoLibrary
from .state import Store, build_state
from .weather import forecast_url, geocode_url, parse_forecast, parse_place

ROOT = Path(__file__).resolve().parent.parent
_PORT_IN_USE = {errno.EADDRINUSE, getattr(errno, "WSAEADDRINUSE", errno.EADDRINUSE)}


def log(message: str) -> None:
    print(message, flush=True)


def main(argv: list[str] | None = None, root: Path = ROOT, secrets_dir: Path = SECRETS_DIR) -> int:
    argv = argv or []
    if argv == ["start"]:
        return control.start([sys.executable, str(root / "server.py")], secrets_dir)
    if argv == ["stop"]:
        return control.stop(secrets_dir)
    if argv not in ([], ["pair"]):
        log("Usage: python3 server.py [start | stop | pair]")
        return 2
    try:
        cfg, created = load_config(root / "config.json", root / "config.example.json")
    except ConfigError as e:
        log(f"config.json: {e}")
        return 1
    if created:
        log("Created config.json. Edit it to turn on GitHub, Claude, weather and photos, then restart.")

    if argv == ["pair"]:
        ip = net.lan_ip() if cfg.wifi else None
        try:
            pair(secrets_dir, cfg.port, ip)
        except PairingError as e:
            log(str(e))
            return 1
        log("Paired. If the server is running, restart it.")
        if ip:
            log(f"  WiFi:  https://{ip}:{cfg.port}")
        return 0

    # Nothing is served until a phone is paired: no key, no certificate, no open port.
    not_paired = "Not paired yet. Plug in the phone and run: python3 server.py pair"
    secret = read_secret(secrets_dir)
    cert, key = secrets_dir / "cert.pem", secrets_dir / "key.pem"
    if secret is None or not (cert.is_file() and key.is_file()):
        log(not_paired)
        return 1
    try:
        tls = tls_context(cert, key)
    except OSError:  # ssl.SSLError included: a damaged certificate or key
        log("Can't read the certificate. Plug in the phone and run: python3 server.py pair")
        return 1
    if control.running_pid(secrets_dir) is not None:
        log("vitrina is already running.")
        return 1

    store = Store()
    # A relative folder is beside config.json, whatever folder the server was started from.
    photos = PhotoLibrary(root / Path(cfg.photos_dir).expanduser() if cfg.photos_dir else None)

    def get_state(accept_language: str | None, link: str) -> dict:
        lang = pick_language(cfg.language, accept_language)
        return build_state(store, cfg, lang, link, datetime.now().astimezone(), photos.count())

    # Bind first: if the port is taken, say so before anything else starts.
    # macOS lets us bind 0.0.0.0 next to another app's 127.0.0.1 on the same port, so check that too.
    in_use = f'Port {cfg.port} is already in use. Change "port" in config.json.'
    if _answers_on_localhost(cfg.port):
        log(in_use)
        return 1
    try:
        server = make_server("0.0.0.0" if cfg.wifi else "127.0.0.1", cfg.port, root / "web", get_state, photos.path,
                             tls=tls, secret=secret)
    except OSError as e:
        log(in_use if e.errno in _PORT_IN_USE else f"Can't use port {cfg.port}: {e.strerror or e}")
        return 1

    stop = threading.Event()
    own_adb = not adb.daemon_running()  # if the server opens adb's daemon, it closes it when it stops
    _start_sources(cfg, store, photos, stop)

    def on_long_sleep() -> None:
        # The Mac may wake on another network (a café): don't come back listening there.
        log("The Mac slept for over an hour. Stopping.")
        server.shutdown()
    control.watch_sleep(on_long_sleep, stop)

    log("vitrina is running")
    ip = net.lan_ip() if cfg.wifi else None
    if ip:
        log(f"  WiFi:  https://{ip}:{cfg.port}")
    log(f"  Cable: https://localhost:{cfg.port}")
    log("To stop it: python3 server.py stop")
    lock = control.hold_lock(secrets_dir)  # after the lines above, so `start` can show all of them
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # Ctrl+C, or SIGTERM from `stop` (see server.py)
        pass
    finally:
        stop.set()
        server.server_close()
        adb.release(cfg.port, own_adb)
        if lock:
            lock.close()
        log("Stopped.")
    return 0


def _answers_on_localhost(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


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
