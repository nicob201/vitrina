from __future__ import annotations

# {placeholders} are filled in by the page.
STRINGS: dict[str, dict[str, str]] = {
    "es": {
        "github_title": "Actividad en GitHub",
        "github_total": "contribuciones en el último año",
        "github_streak": "días seguidos",
        "github_today": "hoy",
        "github_less": "menos",
        "github_more": "más",
        "claude_title": "Uso de Claude",
        "claude_session": "Sesión actual",
        "claude_week": "Esta semana",
        "claude_resets_in": "Se reinicia en {duration}",
        "claude_resets_on": "Se reinicia el {weekday} a las {time}",
        "claude_week_elapsed": "pasó el {pct} % de la semana",
        "duration_hm": "{h} h {m} min",
        "duration_m": "{m} min",
        "link_usb": "USB",
        "link_wifi": "WiFi",
        "offline": "sin conexión",
        "weather_clear": "despejado",
        "weather_partly_cloudy": "algo nublado",
        "weather_cloudy": "nublado",
        "weather_fog": "niebla",
        "weather_drizzle": "llovizna",
        "weather_rain": "lluvia",
        "weather_snow": "nieve",
        "weather_storm": "tormenta",
    },
    "en": {
        "github_title": "GitHub activity",
        "github_total": "contributions in the last year",
        "github_streak": "day streak",
        "github_today": "today",
        "github_less": "less",
        "github_more": "more",
        "claude_title": "Claude usage",
        "claude_session": "Current session",
        "claude_week": "This week",
        "claude_resets_in": "Resets in {duration}",
        "claude_resets_on": "Resets {weekday} at {time}",
        "claude_week_elapsed": "{pct}% of the week elapsed",
        "duration_hm": "{h} h {m} min",
        "duration_m": "{m} min",
        "link_usb": "USB",
        "link_wifi": "Wi-Fi",
        "offline": "offline",
        "weather_clear": "clear",
        "weather_partly_cloudy": "partly cloudy",
        "weather_cloudy": "cloudy",
        "weather_fog": "fog",
        "weather_drizzle": "drizzle",
        "weather_rain": "rain",
        "weather_snow": "snow",
        "weather_storm": "storm",
    },
}


def pick_language(setting: str, accept_language: str | None) -> str:
    if setting in ("es", "en"):
        return setting
    # Only the phone's first-choice language counts; anything but Spanish gets English.
    first = (accept_language or "").split(",")[0].split(";")[0].split("-")[0]
    return "es" if first.strip().lower() == "es" else "en"
