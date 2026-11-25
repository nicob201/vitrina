from __future__ import annotations

import dataclasses
import json
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    port: int = 8765
    wifi: bool = True
    language: str = "auto"
    seconds_per_panel: int = 15
    github_user: str = ""
    claude: bool = False
    mac: bool = False
    city: str = ""
    country: str = ""
    units: str = "celsius"
    photos_dir: str = ""


class ConfigError(Exception):
    """A problem in config.json; the message is shown to the user as is."""


_TYPES = {f.name: type(f.default) for f in dataclasses.fields(Config)}
_CHOICES = {"language": {"auto", "es", "en"}, "units": {"celsius", "fahrenheit"}}


def load_config(path: Path, example: Path) -> tuple[Config, bool]:
    created = not path.exists()
    if created:
        shutil.copyfile(example, path)
    try:
        # utf-8-sig also accepts the byte-order mark some Windows editors add.
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError:
        raise ConfigError("save the file as UTF-8 (accents and ñ need it)") from None
    except json.JSONDecodeError as e:
        raise ConfigError(f"invalid JSON at line {e.lineno}") from None
    if not isinstance(data, dict):
        raise ConfigError("must be a JSON object like {\"port\": 8765}")

    for key, value in data.items():
        if key not in _TYPES:
            raise ConfigError(f'unknown option "{key}"')
        expected = _TYPES[key]
        # type() rather than isinstance(): JSON true must not pass as an int.
        if type(value) is not expected:
            raise ConfigError(f'"{key}" must be {_type_name(expected)}')
        if key in _CHOICES and value not in _CHOICES[key]:
            options = ", ".join(sorted(_CHOICES[key]))
            raise ConfigError(f'"{key}" must be one of: {options}')

    cfg = Config(**data)
    if not 1 <= cfg.port <= 65535:
        raise ConfigError('"port" must be between 1 and 65535')
    if cfg.seconds_per_panel < 5:
        raise ConfigError('"seconds_per_panel" must be at least 5')
    return cfg, created


def _type_name(t: type) -> str:
    return {int: "a whole number", bool: "true or false", str: "text"}[t]
