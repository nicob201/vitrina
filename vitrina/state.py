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
    """Everything the page needs, ready to paint. Panels without data are left out."""
    weather = store.get("weather")
    state = {
        "lang": lang,
        "link": link,
        "seconds_per_panel": config.seconds_per_panel,
        "strings": STRINGS[lang],
        "panels": ["clock"],
        "clock": {
            "weather": dict(weather, label=STRINGS[lang]["weather_" + weather["condition"]]) if weather else None,
        },
    }

    days = store.get("github_days")
    if config.github_user and days:
        state["panels"].append("github")
        state["github"] = github_view(days, now.date())

    usage = store.get("claude_usage")
    if config.claude and usage and (usage.get("session") or usage.get("week")):
        state["panels"].append("claude")
        state["claude"] = claude_view(usage, now)

    if photo_count:
        state["panels"].append("photos")
        state["photos"] = [f"/api/photo/{i}" for i in range(photo_count)]

    return state
