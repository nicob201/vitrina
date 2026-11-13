from __future__ import annotations

from pathlib import Path

from vitrina.pairing import ensure_cert


def make_cert(folder: Path) -> tuple[Path, Path]:
    """A throwaway certificate for tests, in a temporary folder (never the real secrets folder)."""
    return ensure_cert(folder)
