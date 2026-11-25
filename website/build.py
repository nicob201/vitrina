"""Builds dist/: the site, plus web/ as a live demo under dist/demo/. Standard library only.

    python3 website/build.py            # output in <repo>/dist; SITE_URL overrides the public URL
"""
from __future__ import annotations

import json
import os
import random
import re
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DEFAULT_SITE_URL = "https://vitrina.nicolasboscasso.workers.dev"
PHOTOS = ["bariloche.jpg", "estrellas.jpg", "lago-vertical.jpg"]
SHIM_TAG = '<script src="demo-shim.js"></script>'
APP_TAG = '<script src="app.js"></script>'
TEXT_SUFFIXES = {".html", ".js", ".css", ".json", ".svg", ".tsv"}


class BuildError(Exception):
    pass


def read_version(repo: Path) -> str:
    gradle = repo / "android" / "app" / "build.gradle.kts"
    match = re.search(r'versionName\s*=\s*"([^"]+)"', gradle.read_text(encoding="utf-8"))
    if not match:
        raise BuildError(f"no versionName in {gradle}")
    return match.group(1)


def demo_pairs() -> list[list[int]]:
    """365 [level, count] pairs, oldest first, with a 12-day streak up to the last one."""
    rng = random.Random(7)
    pairs = []
    for _ in range(365):
        level = rng.choice([1, 1, 2, 2, 3, 4]) if rng.random() < 0.5 else 0
        pairs.append([level, level * 3])
    for pair in pairs[-12:]:
        pair[0] = max(pair[0], 2)
        pair[1] = 6
    return pairs


def pairs_to_days(pairs: list[list[int]], today: date) -> list:
    from vitrina.github import Day

    last = len(pairs) - 1
    return [Day(today - timedelta(days=last - i), level, count) for i, (level, count) in enumerate(pairs)]


def demo_state(repo: Path, lang: str, now: datetime) -> dict:
    _import_vitrina(repo)
    from vitrina.config import Config
    from vitrina.state import Store, build_state

    store = Store()
    store.set("weather", {"temp": 18, "max": 22, "min": 11, "condition": "partly_cloudy", "is_day": True})
    store.set("github_days", pairs_to_days(demo_pairs(), now.date()))
    store.set("claude_usage", {
        "session": {"pct": 42.0, "resets_at": now + timedelta(hours=2, minutes=14)},
        "week": {"pct": 51.0, "resets_at": now + timedelta(days=3, hours=5)},
    })
    store.set("mac", {"name": "Mi Mac" if lang == "es" else "My Mac"})
    state = build_state(store, Config(github_user="demo", claude=True, mac=True), lang, "wifi", now, len(PHOTOS))
    # The shim recomputes "github" and "claude" in the browser, and answers /api/metrics; the rest is final.
    state["photos"] = ["photos/" + name for name in PHOTOS]
    return state


def build(repo: Path, out: Path, site_url: str = DEFAULT_SITE_URL) -> None:
    _import_vitrina(repo)
    site, demo = repo / "website", out / "demo"
    version = read_version(repo)
    app_html = (repo / "web" / "index.html").read_text(encoding="utf-8")
    if app_html.count(APP_TAG) != 1:
        raise BuildError(f'web/index.html must have exactly one {APP_TAG}')
    if "fetch('/api/state'" not in (repo / "web" / "app.js").read_text(encoding="utf-8"):
        raise BuildError("web/app.js no longer does fetch('/api/state'; update demo-shim.js")

    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(site, out, ignore=shutil.ignore_patterns(
        "build.py", "demo-shim.js", "demo-photos", "__pycache__"))
    shutil.copytree(repo / "web", demo)
    shutil.copy(site / "demo-shim.js", demo / "demo-shim.js")
    (demo / "photos").mkdir()
    for name in PHOTOS:
        shutil.copy(site / "demo-photos" / name, demo / "photos" / name)
    (demo / "index.html").write_text(app_html.replace(APP_TAG, SHIM_TAG + APP_TAG), encoding="utf-8")

    now = datetime.now(timezone.utc)
    for lang in ("es", "en"):
        (demo / f"state.{lang}.json").write_text(json.dumps(demo_state(repo, lang, now)), encoding="utf-8")
    (demo / "demo-days.json").write_text(json.dumps(demo_pairs()), encoding="utf-8")

    index = out / "index.html"
    index.write_text(
        index.read_text(encoding="utf-8").replace("__VERSION__", version).replace("__SITE_URL__", site_url.rstrip("/")),
        encoding="utf-8",
    )
    _fail_on_placeholders(out)


def _import_vitrina(repo: Path) -> None:
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))


def _fail_on_placeholders(out: Path) -> None:
    for path in out.rglob("*"):
        if path.is_file() and (path.suffix in TEXT_SUFFIXES or path.name == "_headers"):
            left = re.search(r"__[A-Z][A-Z_]*__", path.read_text(encoding="utf-8"))
            if left:
                raise BuildError(f"{left.group(0)} was not replaced in {path.relative_to(out)}")


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    try:
        build(repo, repo / "dist", os.environ.get("SITE_URL") or DEFAULT_SITE_URL)
    except BuildError as e:
        print(f"build failed: {e}", file=sys.stderr)
        return 1
    print("ok", repo / "dist")
    return 0


if __name__ == "__main__":
    sys.exit(main())
