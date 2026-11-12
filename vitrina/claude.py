from __future__ import annotations

import json
import math
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Undocumented endpoint behind Claude Code's /usage. If it changes, the panel just disappears.
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
WEEK = timedelta(days=7)


def read_token(platform: str, home: Path, run=subprocess.run) -> str | None:
    """Read Claude Code's OAuth token. Read-only: refreshing it could log Claude Code out."""
    sources = []
    if platform == "darwin":
        sources.append(lambda: run(
            ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
            capture_output=True, text=True, timeout=10,
        ))
    sources.append(lambda: (home / ".claude" / ".credentials.json").read_text(encoding="utf-8"))

    for source in sources:
        try:
            out = source()
            if isinstance(out, subprocess.CompletedProcess):
                if out.returncode != 0:
                    continue
                out = out.stdout
            token = json.loads(out)["claudeAiOauth"]["accessToken"]
            if isinstance(token, str) and token:
                return token
        except Exception:  # missing, unreadable or malformed: try the next source
            continue
    return None


def usage_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "anthropic-beta": "oauth-2025-04-20"}


def parse_usage(data: dict) -> dict:
    return {"session": _window(data.get("five_hour")), "week": _window(data.get("seven_day"))}


def _window(raw) -> dict | None:
    if not isinstance(raw, dict) or raw.get("utilization") is None:
        return None
    resets = raw.get("resets_at")
    if resets:
        # Python 3.9's fromisoformat doesn't take a trailing Z; a time with no zone is taken as UTC.
        resets = datetime.fromisoformat(resets.replace("Z", "+00:00"))
        if resets.tzinfo is None:
            resets = resets.replace(tzinfo=timezone.utc)
    return {"pct": float(raw["utilization"]), "resets_at": resets or None}


def claude_view(usage: dict, now: datetime) -> dict:
    session = _view(usage.get("session"), now)
    week = _view(usage.get("week"), now)
    if week is not None:
        resets = usage["week"]["resets_at"]
        week["elapsed_pct"] = None
        if week["resets_at"] is not None:
            elapsed = (now - (resets - WEEK)) / WEEK * 100
            week["elapsed_pct"] = _round(min(max(elapsed, 0), 100))
    return {"session": session, "week": week}


def _view(window: dict | None, now: datetime) -> dict | None:
    if window is None:
        return None
    resets = window["resets_at"]
    if resets is not None and now >= resets:
        # The window already reset: nothing used since, no need to ask the API.
        return {"pct": 0, "resets_at": None}
    return {"pct": _round(window["pct"]), "resets_at": resets.isoformat() if resets else None}


def _round(x: float) -> int:
    return int(math.floor(x + 0.5))
