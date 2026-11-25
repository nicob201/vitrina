from __future__ import annotations

import threading
from datetime import datetime

from .claude import claude_view
from .config import Config
from .github import github_view
from .i18n import STRINGS


class Store:
    """Latest good value of each source; written by background threads, read per request."""

    def __init__(self) -> None:
        self._values: dict = {}
        self._lock = threading.Lock()

    def set(self, key: str, value) -> None:
        with self._lock:
            self._values[key] = value

    def get(self, key: str, default=None):
        with self._lock:
            return self._values.get(key, default)


def build_state(
    store: Store, config: Config, lang: str, link: str, now: datetime, photo_count: int
) -> dict:
    """Everything the page needs, ready to paint. Panels without data are left out,
    and so is a panel whose data turns out to be broken: the rest of the page keeps working."""
    state = {
        "lang": lang,
        "link": link,
        "seconds_per_panel": config.seconds_per_panel,
        "strings": STRINGS[lang],
        "panels": ["clock"],
        "clock": {"weather": _safe(lambda: _weather(store.get("weather"), lang))},
    }

    days = store.get("github_days")
    if config.github_user and days:
        _add(state, "github", lambda: github_view(days, now.date()))

    usage = store.get("claude_usage")
    if config.claude and usage and (usage.get("session") or usage.get("week")):
        _add(state, "claude", lambda: claude_view(usage, now))

    mac = store.get("mac")
    if config.mac and mac:
        _add(state, "mac", lambda: {"name": mac["name"]})

    if photo_count:
        state["panels"].append("photos")
        state["photos"] = [f"/api/photo/{i}" for i in range(photo_count)]

    return state


def _weather(weather: dict | None, lang: str) -> dict | None:
    if not weather:
        return None
    return dict(weather, label=STRINGS[lang]["weather_" + weather["condition"]])


def _add(state: dict, panel: str, view) -> None:
    value = _safe(view)
    if value is not None:
        state["panels"].append(panel)
        state[panel] = value


def _safe(build):
    try:
        return build()
    except Exception:  # e.g. the undocumented Claude API changing shape
        return None
