from __future__ import annotations

import threading
from typing import Callable


def run_every(
    interval: float,
    task: Callable[[], None],
    name: str,
    log: Callable[[str], None],
    stop: threading.Event,
) -> threading.Thread:
    """Run task now and then every interval seconds; a failure is logged and never stops the loop."""

    def loop() -> None:
        while not stop.is_set():
            try:
                task()
            except Exception as exc:
                log(f"{name}: {exc}")
            stop.wait(interval)

    thread = threading.Thread(target=loop, name=name, daemon=True)
    thread.start()
    return thread
