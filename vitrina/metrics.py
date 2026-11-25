from __future__ import annotations

import re
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
