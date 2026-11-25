from __future__ import annotations

import re
import threading
import time
from typing import Callable

INTERVAL = 5     # seconds between readings
WINDOW = 300     # seconds of history the phone draws
MAX_GAP = 15     # a longer silence (sleep, pause) starts the history over
IDLE = 60        # no request for this long: nobody is looking, stop reading
SLOW = 1800      # disk and battery barely move

_WRAP = 2**32    # the kernel's tick and byte counters are 32-bit


def cpu_percent(prev: tuple[int, int, int, int], cur: tuple[int, int, int, int]) -> float | None:
    """Busy share of the ticks (user, system, idle, nice) between two readings."""
    user, system, idle, nice = ((c - p) % _WRAP for p, c in zip(prev, cur))
    total = user + system + idle + nice
    return (user + system + nice) / total * 100 if total else None


def rate(prev: int, cur: int, seconds: float) -> int | None:
    """Bytes per second between two readings of a 32-bit counter."""
    return round((cur - prev) % _WRAP / seconds) if seconds > 0 else None


def memory_used(internal: int, purgeable: int, wired: int, compressor: int, page_size: int) -> int:
    """App memory + wired + compressed, like "Memory Used" in Activity Monitor."""
    return (internal - purgeable + wired + compressor) * page_size


def parse_battery(text: str) -> dict | None:
    """`pmset -g batt` → {"pct", "state"}; None on a Mac without a battery."""
    found = re.search(r"InternalBattery.*?\t(\d+)%;\s*([^;]*)", text)
    if not found:
        return None
    status = found.group(2).strip()
    if status in ("charging", "finishing charge"):
        state = "charging"
    elif "'Battery Power'" in text.split("\n", 1)[0]:
        state = "battery"
    else:
        state = "ac"
    return {"pct": int(found.group(1)), "state": state}


def read_all(readers: dict[str, Callable[[], object]], log: Callable[[str], None], failing: set[str]) -> dict[str, object]:
    """Every reader's value; one that fails gives None and is logged when it starts failing, not every time."""
    values: dict[str, object] = {}
    for name, read in readers.items():
        try:
            values[name] = read()
            failing.discard(name)
        except Exception as exc:
            values[name] = None
            if name not in failing:
                failing.add(name)
                log(f"Mac panel: {name}: {exc}")
    return values


class Metrics:
    """The last WINDOW seconds of readings, for /api/metrics. tick() runs in its own thread; seen() and body()
    in the server's. The reader is injected so all of this is testable without macOS."""

    def __init__(self, read: Callable[[], dict], ram_total: int, clock: Callable[[], float] = time.time) -> None:
        self._read = read
        self._ram_total = ram_total
        self._clock = clock
        self._lock = threading.Lock()
        self._samples: list[dict] = []
        self._prev: tuple[float, dict] | None = None  # time and raw values of the last reading
        self._disk: dict | None = None
        self._battery: dict | None = None
        self._ready = False
        self._seen = clock()  # starting up counts as a request

    def seen(self) -> None:
        with self._lock:
            self._seen = self._clock()

    def tick(self) -> None:
        with self._lock:
            if self._clock() - self._seen > IDLE:
                return  # nobody is looking; the gap will start the history over
        raw = self._read()  # outside the lock: requests never wait on a reading
        now = self._clock()
        with self._lock:
            prev = self._prev
            if prev is None or not 0 <= now - prev[0] <= MAX_GAP:
                self._samples.clear()  # first reading, a sleep, a pause or a clock change
                prev = None
            sample = {"t": int(now), "cpu": None, "gpu": _round(raw["gpu"]), "ram": raw["ram"], "down": None, "up": None}
            if prev is not None:
                before = prev[1]
                if before["cpu"] is not None and raw["cpu"] is not None:
                    sample["cpu"] = _round(cpu_percent(before["cpu"], raw["cpu"]))
                if before["net"] is not None and raw["net"] is not None:
                    seconds = now - prev[0]
                    sample["down"] = rate(before["net"][0], raw["net"][0], seconds)
                    sample["up"] = rate(before["net"][1], raw["net"][1], seconds)
            self._prev = (now, raw)
            self._samples.append(sample)
            self._samples = [s for s in self._samples if s["t"] > now - WINDOW]
            if any(v is not None for v in raw.values()):
                self._ready = True

    def set_slow(self, disk: dict | None, battery: dict | None) -> None:
        with self._lock:
            self._disk, self._battery = disk, battery

    @property
    def ready(self) -> bool:
        with self._lock:
            return self._ready

    def body(self) -> dict:
        with self._lock:
            return {"interval": INTERVAL, "samples": [dict(s) for s in self._samples], "ram_total": self._ram_total,
                    "disk": self._disk, "battery": self._battery}


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 1)
