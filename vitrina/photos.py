from __future__ import annotations

import random
import threading
from pathlib import Path

# What the phone's browser can show. HEIC (iPhone) is not among them.
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class PhotoLibrary:
    """The photos folder, shuffled once; the order holds until the files change."""

    def __init__(self, folder: Path | None, rng: random.Random | None = None) -> None:
        self._folder = folder
        self._rng = rng or random.Random()
        self._paths: list[Path] = []
        self._lock = threading.Lock()

    def rescan(self) -> None:
        found = set()
        if self._folder is not None and self._folder.is_dir():
            found = {
                p for p in self._folder.iterdir()
                if p.suffix.lower() in EXTENSIONS and not p.name.startswith(".") and p.is_file()
            }
        with self._lock:
            if found == set(self._paths):
                return
            paths = sorted(found)
            self._rng.shuffle(paths)
            self._paths = paths

    def count(self) -> int:
        with self._lock:
            return len(self._paths)

    def path(self, index: int) -> Path | None:
        with self._lock:
            return self._paths[index] if 0 <= index < len(self._paths) else None
