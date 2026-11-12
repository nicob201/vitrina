# vitrina — Plan 1: server y página

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `python3 server.py` en la PC sirve una página que el celu muestra en Chrome (cable o WiFi), rotando los paneles hora+clima, GitHub, Claude y fotos con la estética de la maqueta.

**Architecture:** Server en Python con solo la biblioteca estándar. Hilos de fondo traen cada fuente y guardan el último dato bueno en un `Store`; `build_state` arma en cada pedido el JSON listo para pintar (la PC calcula, el celu pinta). La página es HTML/CSS/JS sin build que consulta `/api/state` cada 30 s.

**Tech Stack:** Python 3.9 stdlib (`http.server`, `urllib`, `html.parser`, `unittest`), HTML + CSS + JS vanilla, Chrome headless para capturas.

**Spec:** `docs/superpowers/specs/2026-11-12-vitrina-design.md`. La app Android (spec §8) va en el **Plan 2**, después de este.

## Global Constraints

- Python **3.9+, solo stdlib**. Correr todo con `/usr/bin/python3` (3.9.6). Cada módulo empieza con `from __future__ import annotations`. Nada de `match`. `datetime.fromisoformat` de 3.9 no acepta `Z`: reemplazar por `+00:00` antes.
- Tests: `/usr/bin/python3 -m unittest -v` desde la raíz. **Ningún test toca la red**: las llamadas a internet y la hora entran como parámetros.
- Código, comentarios, mensajes de consola y commits **en inglés**. Commits convencionales (`feat:`, `test:`, `chore:`, `docs:`), **sin ningún trailer** (ni `Co-Authored-By` ni firmas).
- Al celu nunca va el token de Claude; el token nunca se imprime ni se loguea.
- El server no escribe nada pedido por la red: solo `GET`.
- Página: viewport real ~**890 × 396 px CSS**, dpr 1,75. Fuentes locales (sin Google Fonts en runtime). Paleta y tipografías: spec §7 "Dirección visual"; maqueta local `spike/preview.html` (fuera del repo). `prefers-reduced-motion` respetado.
- Orden fijo de paneles: `clock`, `github`, `claude`, `photos`.

## Review Focus

1. **Medianoche y zona horaria en GitHub:** el calendario de GitHub puede traer un día "de mañana" respecto de la hora local. "Hoy" y la racha se calculan con la fecha local de la PC e ignoran días posteriores → test en Task 4.
2. **Fotos de iPhone (`.HEIC`) y archivos raros en la carpeta:** se ignoran sin romper nada → test en Task 7.
3. **Puerto ocupado** (otro server corriendo): mensaje claro y salida con código 1, sin traceback → paso de verificación en Task 10.
4. **Ciudad que no existe o país que no coincide:** el server avisa y sigue sin clima; el panel de la hora queda como la maqueta → tests en Task 6, verificación en Task 10.
5. **Se corta la PC o el WiFi con la página abierta:** queda el último dato, aparece "sin conexión" y se recupera sola al volver, sin recargar → verificación en Task 11.

## Estructura de archivos

```
server.py                    entrada: python3 server.py
config.example.json
vitrina/__init__.py
vitrina/config.py            Config + load_config
vitrina/i18n.py              STRINGS es/en + pick_language
vitrina/github.py            parseo de contribuciones + github_view
vitrina/claude.py            token + parseo de uso + claude_view
vitrina/weather.py           Open-Meteo: lugar, pronóstico, condición
vitrina/photos.py            PhotoLibrary
vitrina/state.py             Store + build_state
vitrina/handler.py           make_server (HTTP)
vitrina/net.py               fetch, fetch_json, lan_ip
vitrina/adb.py               ensure_reverse
vitrina/loops.py             run_every
vitrina/app.py               main(): arma todo
web/index.html  web/styles.css  web/app.js  web/weather-icons.svg  web/fonts/
tests/__init__.py  tests/test_*.py  tests/fixtures/
```

---

### Task 1: Repo y arnés de tests

**Files:**
- Create: `.gitignore`, `LICENSE`, `vitrina/__init__.py`, `tests/__init__.py`

- [ ] **Step 1:** `git init -b main` en la raíz del proyecto.
- [ ] **Step 2:** `.gitignore` con: `config.json`, `__pycache__/`, `*.pyc`, `.DS_Store`, `NOTAS.md`, `spike/` (notas y maqueta quedan solo locales).
- [ ] **Step 3:** `LICENSE` MIT, año 2026, titular **`nicob201`**.
- [ ] **Step 4:** `vitrina/__init__.py` y `tests/__init__.py` vacíos.
- [ ] **Step 5:** Run `/usr/bin/python3 -m unittest -v` → Expected: `Ran 0 tests` / `OK` (o `NO TESTS RAN`), sin errores de import.
- [ ] **Step 6: Commit**

```bash
git add .gitignore LICENSE vitrina tests docs
git commit -m "chore: initial project skeleton, spec and plan"
```

---

### Task 2: Config

**Files:**
- Create: `vitrina/config.py`, `config.example.json`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Config` con campos y defaults: `port: int = 8765`, `wifi: bool = True`, `language: str = "auto"`, `seconds_per_panel: int = 15`, `github_user: str = ""`, `claude: bool = False`, `city: str = ""`, `country: str = ""`, `units: str = "celsius"`, `photos_dir: str = ""`.
  - `class ConfigError(Exception)` — su mensaje se muestra tal cual al usuario.
  - `load_config(path: Path, example: Path) -> tuple[Config, bool]` — el `bool` es `True` si creó `config.json` copiando el ejemplo.

- [ ] **Step 1: Write the failing tests** (cada uno usa un `tempfile.TemporaryDirectory`)

```python
def test_missing_file_is_created_from_example(self):
    cfg, created = load_config(tmp / "config.json", EXAMPLE)
    self.assertTrue(created)
    self.assertEqual(cfg, Config())
    self.assertEqual((tmp / "config.json").read_text(), EXAMPLE.read_text())

def test_example_matches_defaults(self):          # el ejemplo no se desincroniza
    self.assertEqual(json.loads(EXAMPLE.read_text()), dataclasses.asdict(Config()))

def test_reads_values(self):                      # {"port": 9000, "github_user": "octocat", "claude": true}
    self.assertEqual((cfg.port, cfg.github_user, cfg.claude, cfg.units), (9000, "octocat", True, "celsius"))

def test_invalid_json_reports_line(self):          # '{\n "port": 80,\n}'
    with self.assertRaisesRegex(ConfigError, "line 3"): ...

def test_unknown_key_is_rejected(self):            # {"github_usr": "x"}
    with self.assertRaisesRegex(ConfigError, "github_usr"): ...

def test_wrong_types_are_rejected(self):           # cada uno por separado
    for bad in ({"port": "8765"}, {"port": True}, {"claude": "yes"}, {"seconds_per_panel": 2.5}):
        with self.assertRaises(ConfigError): ...

def test_invalid_choices_are_rejected(self):
    for bad in ({"language": "pt"}, {"units": "kelvin"}, {"port": 0}, {"port": 70000}, {"seconds_per_panel": 4}):
        with self.assertRaises(ConfigError): ...
```

- [ ] **Step 2:** Run `/usr/bin/python3 -m unittest tests.test_config -v` → Expected: FAIL (`ModuleNotFoundError: vitrina.config`).
- [ ] **Step 3: Implement** `config.example.json` (exactamente los defaults de `Config`, mismo orden que la spec §6) y `load_config`. Reglas: tipo exacto por campo (`bool` no vale como `int`); `language ∈ {auto, es, en}`; `units ∈ {celsius, fahrenheit}`; `1 ≤ port ≤ 65535`; `seconds_per_panel ≥ 5`. JSON inválido → `ConfigError(f"invalid JSON at line {e.lineno}")`.
- [ ] **Step 4:** Run el mismo comando → Expected: PASS.
- [ ] **Step 5: Commit** `git add vitrina/config.py config.example.json tests/test_config.py && git commit -m "feat: load and validate config.json"`

---

### Task 3: Textos e idioma

**Files:**
- Create: `vitrina/i18n.py`
- Test: `tests/test_i18n.py`

**Interfaces:**
- Produces: `STRINGS: dict[str, dict[str, str]]` con claves `"es"` y `"en"`; `pick_language(setting: str, accept_language: str | None) -> str`.

Textos (copia exacta; `{x}` son reemplazos que hace la página):

| clave | es | en |
|---|---|---|
| github_title | Actividad en GitHub | GitHub activity |
| github_total | contribuciones en el último año | contributions in the last year |
| github_streak | días seguidos | day streak |
| github_today | hoy | today |
| github_less / github_more | menos / más | less / more |
| claude_title | Uso de Claude | Claude usage |
| claude_session | Sesión actual | Current session |
| claude_week | Esta semana | This week |
| claude_resets_in | Se reinicia en {duration} | Resets in {duration} |
| claude_resets_on | Se reinicia el {weekday} a las {time} | Resets {weekday} at {time} |
| claude_week_elapsed | pasó el {pct} % de la semana | {pct}% of the week elapsed |
| duration_hm / duration_m | {h} h {m} min / {m} min | {h} h {m} min / {m} min |
| link_usb / link_wifi / offline | USB / WiFi / sin conexión | USB / Wi-Fi / offline |
| weather_clear, weather_partly_cloudy, weather_cloudy, weather_fog, weather_drizzle, weather_rain, weather_snow, weather_storm | despejado, algo nublado, nublado, niebla, llovizna, lluvia, nieve, tormenta | clear, partly cloudy, cloudy, fog, drizzle, rain, snow, storm |

- [ ] **Step 1: Write the failing tests**

```python
def test_both_languages_have_the_same_keys(self):
    self.assertEqual(set(STRINGS["es"]), set(STRINGS["en"]))

def test_pick_language(self):
    cases = [(("es", None), "es"), (("en", "es-AR"), "en"),
             (("auto", "es-AR,es;q=0.9,en;q=0.8"), "es"), (("auto", "ES"), "es"),
             (("auto", "en-US,en;q=0.9"), "en"), (("auto", "pt-BR,pt;q=0.9,es;q=0.8"), "en"),
             (("auto", None), "en"), (("auto", ""), "en")]
    for args, expected in cases:
        self.assertEqual(pick_language(*args), expected, args)
```

- [ ] **Step 2:** Run `/usr/bin/python3 -m unittest tests.test_i18n -v` → Expected: FAIL.
- [ ] **Step 3: Implement.** `pick_language`: si `setting` es `es`/`en`, gana; si no, mira solo el **primer** idioma de `Accept-Language` (subetiqueta principal, sin importar mayúsculas): `es` → `"es"`, cualquier otro o vacío → `"en"`.
- [ ] **Step 4:** Run → Expected: PASS.
- [ ] **Step 5: Commit** `feat: add es/en strings and language selection`

---

### Task 4: Fuente GitHub

**Files:**
- Create: `vitrina/github.py`, `tests/fixtures/github_contributions.html`
- Test: `tests/test_github.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Day: date: datetime.date; level: int; count: int`
  - `contributions_url(user: str) -> str` → `https://github.com/users/<user URL-quoted>/contributions`
  - `parse_contributions(html: str) -> list[Day]` ordenada por fecha; `ValueError` si no encuentra ningún día.
  - `github_view(days: list[Day], today: datetime.date) -> dict` con `total: int`, `streak: int`, `today: int`, `weeks: list[list[int | None]]`, `months: list[dict]` (`{"week": int, "month": int 1-12}`).

**Formato real de GitHub** (verificado 2026-11-12): las celdas vienen por filas de día de semana (no por fecha) y la cantidad está en un `<tool-tip>` aparte, unido por `for` = `id` de la celda:

```html
<td tabindex="0" data-ix="0" aria-selected="false" aria-describedby="contribution-graph-legend-level-2" style="width: 10px" data-date="2026-11-01" id="contribution-day-component-0-0" data-level="2" role="gridcell" data-view-component="true" class="ContributionCalendar-day"></td>
<tool-tip style="pointer-events: none;" id="tooltip-1" for="contribution-day-component-0-0" popover="manual" data-direction="n" data-type="label" data-view-component="true" class="sr-only position-absolute">4 contributions on November 1st.</tool-tip>
```

Textos del tooltip: `No contributions on …`, `1 contribution on …`, `1,024 contributions on …`.

- [ ] **Step 1: Write the fixture** `tests/fixtures/github_contributions.html`: una `<table><tbody>` con 7 `<tr>` (domingo a sábado) y las celdas en ese orden de filas, con estos 12 días (domingo 2026-11-01 a jueves 2026-11-12), cada uno con su `<tool-tip>` después de la tabla:

| fecha | level | count | fecha | level | count |
|---|---|---|---|---|---|
| 11-01 | 2 | 4 | 11-07 | 0 | 0 |
| 11-02 | 0 | 0 | 11-08 | 1 | 3 |
| 11-03 | 1 | 1 | 11-09 | 3 | 6 |
| 11-04 | 0 | 0 | 11-10 | 1 | 1 |
| 11-05 | 4 | 1,024 | 11-11 | 1 | 2 |
| 11-06 | 1 | 2 | 11-12 | 0 | 0 |

- [ ] **Step 2: Write the failing tests**

```python
def test_parses_days_sorted_with_counts(self):
    days = parse_contributions(FIXTURE)
    self.assertEqual(len(days), 12)
    self.assertEqual(days[0], Day(date(2026, 11, 1), 2, 4))
    self.assertEqual(days[4], Day(date(2026, 11, 5), 4, 1024))
    self.assertEqual(days[-1], Day(date(2026, 11, 12), 0, 0))

def test_unknown_html_raises(self):
    with self.assertRaises(ValueError): parse_contributions("<html>rate limited</html>")

def test_view_from_fixture(self):
    v = github_view(parse_contributions(FIXTURE), date(2026, 11, 12))
    self.assertEqual((v["total"], v["streak"], v["today"]), (1043, 4, 0))   # hoy 0 → racha desde ayer
    self.assertEqual(v["weeks"], [[2, 0, 1, 0, 4, 1, 0], [1, 3, 1, 1, 0]])
    self.assertEqual(v["months"], [{"week": 0, "month": 11}])

def test_streak_includes_today_when_today_has_contributions(self): ...  # hoy=11-11 → racha 4, today 2

def test_days_after_today_are_ignored(self):      # Review Focus 1
    days = parse_contributions(FIXTURE) + [Day(date(2026, 11, 13), 4, 9)]
    v = github_view(days, date(2026, 11, 12))
    self.assertEqual((v["total"], v["today"], v["streak"]), (1043, 0, 4))

def test_first_week_is_padded_when_it_starts_midweek(self):   # primer día miércoles 2026-11-04
    self.assertEqual(v["weeks"][0][:3], [None, None, None])

def test_month_labels(self):    # días con count 0 del 2026-09-27 (domingo) al 2026-11-12
    self.assertEqual(v["months"], [{"week": 1, "month": 10}, {"week": 5, "month": 11}])

def test_real_page(self):       # tests/fixtures/github_contributions_real.html
    days = parse_contributions(REAL)
    self.assertTrue(365 <= len(days) <= 371)
    self.assertTrue(all(0 <= d.level <= 4 for d in days))
    self.assertTrue(all(d.count == 0 for d in days if d.level == 0))
```

Además del fixture sintético, guardar la página real del usuario: `curl -s https://github.com/users/<github_user>/contributions -o tests/fixtures/github_contributions_real.html` (usuario `nicob201`; datos públicos).

- [ ] **Step 3:** Run `/usr/bin/python3 -m unittest tests.test_github -v` → Expected: FAIL.
- [ ] **Step 4: Implement.** Parseo con `html.parser.HTMLParser`: junta `id → (date, level)` de los `td.ContributionCalendar-day` y `for → texto` de los `tool-tip`; la cantidad es el primer número del texto sin comas (`No` = 0). `github_view` descarta días `> today` antes de todo. Semanas empiezan en domingo; la primera se rellena con `None` adelante. Racha: hacia atrás desde `today` (desde ayer si hoy es 0); un día que falta cuenta 0. Meses: etiqueta en la semana `w` cuando el mes de su primer día real difiere del de la semana `w-1` (la semana 0 siempre etiqueta), y se borra la etiqueta de la semana 0 si la siguiente cae en la semana 1 o 2.
- [ ] **Step 5:** Run → Expected: PASS.
- [ ] **Step 6: Commit** `feat: parse GitHub contributions calendar`

---

### Task 5: Fuente Claude

**Files:**
- Create: `vitrina/claude.py`, `tests/fixtures/claude_usage.json`
- Test: `tests/test_claude.py`

**Interfaces:**
- Produces:
  - `USAGE_URL = "https://api.anthropic.com/api/oauth/usage"`
  - `read_token(platform: str, home: Path, run=subprocess.run) -> str | None`
  - `usage_headers(token: str) -> dict[str, str]` → `{"Authorization": f"Bearer {token}", "anthropic-beta": "oauth-2025-04-20"}`
  - `parse_usage(data: dict) -> dict` → `{"session": Window | None, "week": Window | None}`, con `Window = {"pct": float, "resets_at": datetime | None}`
  - `claude_view(usage: dict, now: datetime) -> dict` → `{"session": {"pct": int, "resets_at": str | None} | None, "week": {"pct": int, "resets_at": str | None, "elapsed_pct": int | None} | None}`

Fixture (forma de la respuesta según los campos del binario de Claude Code; se confirma contra la respuesta real en Task 10):

```json
{"five_hour": {"utilization": 42.0, "resets_at": "2026-11-12T14:13:00.123456+00:00"},
 "seven_day": {"utilization": 67.4, "resets_at": "2026-11-15T12:00:00Z"},
 "seven_day_opus": null}
```

- [ ] **Step 1: Write the failing tests** (`NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)`)

```python
def test_view_before_reset(self):
    v = claude_view(parse_usage(FIXTURE), NOW)
    self.assertEqual(v["session"], {"pct": 42, "resets_at": "2026-11-12T14:13:00.123456+00:00"})
    self.assertEqual(v["week"], {"pct": 67, "resets_at": "2026-11-15T12:00:00+00:00", "elapsed_pct": 57})

def test_session_after_reset_is_zero(self):     # now = 15:00 UTC
    self.assertEqual(v["session"], {"pct": 0, "resets_at": None})

def test_week_after_reset_is_zero(self):        # now = 2026-11-16
    self.assertEqual(v["week"], {"pct": 0, "resets_at": None, "elapsed_pct": None})

def test_missing_windows_are_none(self):
    self.assertEqual(parse_usage({"five_hour": None}), {"session": None, "week": None})

def test_read_token_from_keychain_on_macos(self):   # run falso: returncode 0, stdout '{"claudeAiOauth": {"accessToken": "tok"}}'
    self.assertEqual(read_token("darwin", tmp_home, run=fake), "tok")
    # y verifica que se llamó con ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"]

def test_read_token_falls_back_to_credentials_file(self):  # run falla; existe tmp_home/.claude/.credentials.json
    self.assertEqual(read_token("darwin", tmp_home, run=failing), "tok")

def test_read_token_on_windows_never_runs_security(self): ...
def test_read_token_returns_none_when_missing_or_malformed(self): ...   # sin archivo; JSON roto; sin accessToken
```

- [ ] **Step 2:** Run `/usr/bin/python3 -m unittest tests.test_claude -v` → Expected: FAIL.
- [ ] **Step 3: Implement.** Redondeo `math.floor(x + 0.5)`. `elapsed_pct = (now - (resets_at - 7 días)) / 7 días × 100`, limitado a 0–100. Reinicio pasado: `now >= resets_at`. `read_token` traga cualquier error y devuelve `None`; nunca imprime el token. El `run` va con `capture_output=True, text=True, timeout=10`.
- [ ] **Step 4:** Run → Expected: PASS.
- [ ] **Step 5: Commit** `feat: read Claude usage without refreshing the token`

---

### Task 6: Fuente clima

**Files:**
- Create: `vitrina/weather.py`, `tests/fixtures/geocode.json`, `tests/fixtures/forecast.json`
- Test: `tests/test_weather.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Place: label: str; latitude: float; longitude: float`
  - `geocode_url(city: str, lang: str) -> str` → `https://geocoding-api.open-meteo.com/v1/search?name=…&count=10&language=…&format=json`
  - `parse_place(data: dict, country: str) -> Place | None`
  - `forecast_url(place: Place, units: str) -> str` → `https://api.open-meteo.com/v1/forecast?latitude=…&longitude=…&current=temperature_2m,weather_code,is_day&daily=temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=1` (+ `&temperature_unit=fahrenheit` solo si `units == "fahrenheit"`)
  - `parse_forecast(data: dict) -> dict` → `{"temp": int, "max": int, "min": int, "condition": str, "is_day": bool}`
  - `condition_for(code: int) -> str` → una de `clear, partly_cloudy, cloudy, fog, drizzle, rain, snow, storm`

Fixtures (respuestas reales recortadas, 2026-11-12):
- `geocode.json`: `{"results": [{"name": "Berlín", "latitude": 52.52437, "longitude": 13.41053, "country_code": "DE", "admin1": "Estado de Berlín", "country": "Alemania"}, {"name": "Berlin", "latitude": 44.46867, "longitude": -71.18508, "country_code": "US", "admin1": "New Hampshire", "country": "Estados Unidos"}], "generationtime_ms": 0.6}`
- `forecast.json`: `{"current": {"time": "2026-11-12T21:30", "interval": 900, "temperature_2m": 3.9, "weather_code": 0, "is_day": 0}, "daily": {"time": ["2026-11-12"], "temperature_2m_max": [6.2], "temperature_2m_min": [3.4]}}`

- [ ] **Step 1: Write the failing tests**

```python
def test_first_place_without_country(self):
    self.assertEqual(parse_place(GEO, ""), Place("Berlín, Estado de Berlín, Alemania", 52.52437, 13.41053))

def test_country_filter_is_case_insensitive(self):
    self.assertEqual(parse_place(GEO, "us").label, "Berlin, New Hampshire, Estados Unidos")

def test_no_place(self):                      # Review Focus 4: la API omite "results" si no encuentra nada
    self.assertIsNone(parse_place({"generationtime_ms": 0.5}, ""))
    self.assertIsNone(parse_place(GEO, "AR"))

def test_label_skips_admin1_equal_to_name(self): ...   # {"name": "Madrid", "admin1": "Madrid", "country": "España"} → "Madrid, España"

def test_parse_forecast(self):
    self.assertEqual(parse_forecast(FORECAST), {"temp": 4, "max": 6, "min": 3, "condition": "clear", "is_day": False})

def test_rounding_half_up(self): ...          # 2.5→3, -2.5→-2, -0.4→0

def test_condition_codes(self):
    table = {0: "clear", 1: "partly_cloudy", 2: "partly_cloudy", 3: "cloudy", 45: "fog", 48: "fog",
             51: "drizzle", 57: "drizzle", 61: "rain", 67: "rain", 80: "rain", 82: "rain",
             71: "snow", 77: "snow", 85: "snow", 86: "snow", 95: "storm", 99: "storm", 1234: "cloudy"}

def test_urls(self):
    self.assertIn("name=C%C3%B3rdoba", geocode_url("Córdoba", "es"))
    self.assertIn("temperature_unit=fahrenheit", forecast_url(PLACE, "fahrenheit"))
    self.assertNotIn("temperature_unit", forecast_url(PLACE, "celsius"))
```

- [ ] **Step 2:** Run `/usr/bin/python3 -m unittest tests.test_weather -v` → Expected: FAIL.
- [ ] **Step 3: Implement.** Etiqueta = `name, admin1, country` sin partes vacías ni `admin1 == name`. Redondeo `math.floor(x + 0.5)`. Código desconocido → `cloudy`.
- [ ] **Step 4:** Run → Expected: PASS.
- [ ] **Step 5: Commit** `feat: add Open-Meteo weather source`

---

### Task 7: Fotos

**Files:**
- Create: `vitrina/photos.py`
- Test: `tests/test_photos.py`

**Interfaces:**
- Produces: `EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}`; `class PhotoLibrary` con `__init__(self, folder: Path | None, rng: random.Random | None = None)`, `rescan(self) -> None`, `count(self) -> int`, `path(self, index: int) -> Path | None`. Thread-safe (un `threading.Lock`).

- [ ] **Step 1: Write the failing tests** (carpeta temporal con archivos vacíos)

```python
def test_only_supported_images(self):     # a.jpg B.JPEG c.png d.webp e.HEIC f.txt .hidden.jpg sub/g.jpg   (Review Focus 2)
    lib.rescan()
    self.assertEqual(sorted(p.name for p in all_paths(lib)), ["B.JPEG", "a.jpg", "c.png", "d.webp"])

def test_order_is_kept_when_files_do_not_change(self):
    first = all_paths(lib); lib.rescan(); self.assertEqual(all_paths(lib), first)

def test_new_file_is_picked_up(self): ...
def test_missing_or_unset_folder_is_empty(self): ...           # PhotoLibrary(None) y carpeta inexistente → count 0
def test_path_out_of_range_is_none(self): ...                  # -1, count(), 999
```

- [ ] **Step 2:** Run `/usr/bin/python3 -m unittest tests.test_photos -v` → Expected: FAIL.
- [ ] **Step 3: Implement.** No recursivo; ignora nombres que empiezan con `.`; extensión sin importar mayúsculas. Si el conjunto de archivos cambió, mezcla de nuevo con `rng.shuffle`; si no, conserva el orden.
- [ ] **Step 4:** Run → Expected: PASS.
- [ ] **Step 5: Commit** `feat: add photo library`

---

### Task 8: Estado para el celu

**Files:**
- Create: `vitrina/state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: `Config` (T2), `STRINGS` (T3), `Day`/`github_view` (T4), `claude_view` (T5), salida de `parse_forecast` (T6).
- Produces:
  - `class Store` thread-safe: `set(self, key: str, value) -> None`, `get(self, key: str, default=None)`. Claves: `"github_days"` (`list[Day]`), `"claude_usage"` (salida de `parse_usage`), `"weather"` (salida de `parse_forecast`).
  - `build_state(store: Store, config: Config, lang: str, link: str, now: datetime, photo_count: int) -> dict` — el JSON de `/api/state`:

```
{"lang", "link", "seconds_per_panel", "strings": STRINGS[lang],
 "panels": [...],                       # orden fijo; solo los que tienen datos; "clock" siempre
 "clock":  {"weather": {temp, max, min, condition, is_day, label} | None},
 "github": github_view(days, now.date())          # solo si está en panels
 "claude": claude_view(usage, now)                # solo si está en panels
 "photos": ["/api/photo/0", ...]}                 # solo si está en panels
```

- [ ] **Step 1: Write the failing tests**

```python
def test_empty_store_shows_only_clock(self):
    s = build_state(Store(), Config(), "es", "wifi", NOW, 0)
    self.assertEqual(s["panels"], ["clock"]); self.assertIsNone(s["clock"]["weather"])
    self.assertEqual((s["lang"], s["link"], s["seconds_per_panel"]), ("es", "wifi", 15))
    self.assertEqual(s["strings"], STRINGS["es"])
    for k in ("github", "claude", "photos"): self.assertNotIn(k, s)

def test_full_store_in_fixed_order(self):     # Config(github_user="x", claude=True), store completo, 3 fotos
    self.assertEqual(s["panels"], ["clock", "github", "claude", "photos"])
    self.assertEqual(s["photos"], ["/api/photo/0", "/api/photo/1", "/api/photo/2"])
    self.assertEqual(s["clock"]["weather"]["label"], "despejado")

def test_claude_disabled_in_config_is_hidden_even_with_data(self): ...
def test_github_without_user_is_hidden_even_with_data(self): ...
def test_state_is_json_serializable(self): json.dumps(s)
```

- [ ] **Step 2:** Run `/usr/bin/python3 -m unittest tests.test_state -v` → Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** Run → Expected: PASS.
- [ ] **Step 5: Commit** `feat: assemble display state`

---

### Task 9: Server HTTP

**Files:**
- Create: `vitrina/handler.py`
- Test: `tests/test_handler.py`

**Interfaces:**
- Produces: `make_server(host: str, port: int, web_dir: Path, get_state: Callable[[str | None, str], dict], photo_path: Callable[[int], Path | None]) -> ThreadingHTTPServer`. `get_state(accept_language, link)`.

Rutas (solo `GET`; query string ignorado):
- `/` → `web_dir/index.html`
- `/api/state` → JSON UTF-8, `Cache-Control: no-store`
- `/api/photo/<dígitos>` → bytes del archivo con su tipo; `404` si `photo_path` da `None`
- cualquier otra → archivo dentro de `web_dir` (resuelto con `Path.resolve()` y `is_relative_to`); si no, `404`
- `link = "usb"` si el cliente es `127.0.0.1`, `::1` o `::ffff:127.0.0.1`; si no, `"wifi"`
- Tipos: `mimetypes` más `.woff2 → font/woff2`, `.js → text/javascript`, `.svg → image/svg+xml`. `log_message` silenciado.

- [ ] **Step 1: Write the failing tests** (server real en `127.0.0.1`, puerto `0`, en un hilo; `web_dir` temporal con `index.html` y `a.css`; un `secret.txt` **fuera** de `web_dir`)

```python
def test_index(self):        # 200, text/html
def test_static_file(self):  # /a.css → 200, text/css
def test_state_passes_language_and_link(self):
    # header Accept-Language: es-AR → get_state recibió ("es-AR", "usb"); JSON; Cache-Control: no-store
def test_photo(self):        # /api/photo/0 → bytes del archivo; /api/photo/9 → 404; /api/photo/x → 404
def test_no_path_traversal(self):
    for raw in ("/../secret.txt", "/%2e%2e/secret.txt", "/..%2fsecret.txt", "/api/photo/../../secret.txt"):
        self.assertEqual(raw_get(raw).status, 404)      # http.client, para que la ruta no se normalice
def test_unknown_path_404(self): ...
```

- [ ] **Step 2:** Run `/usr/bin/python3 -m unittest tests.test_handler -v` → Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** Run → Expected: PASS.
- [ ] **Step 5: Commit** `feat: serve page, state and photos over HTTP`

---

### Task 10: Arranque (red, adb, bucles, main)

**Files:**
- Create: `vitrina/net.py`, `vitrina/adb.py`, `vitrina/loops.py`, `vitrina/app.py`, `server.py`
- Test: `tests/test_adb.py`, `tests/test_loops.py`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces:
  - `net.fetch(url: str, headers: dict[str, str] | None = None, timeout: float = 15) -> bytes` (User-Agent `vitrina`), `net.fetch_json(url, headers=None)`, `net.lan_ip() -> str | None` (truco del socket UDP a `10.255.255.255:1`, sin mandar paquetes).
  - `adb.ensure_reverse(port: int, run=subprocess.run, which=shutil.which) -> bool` — `True` si hay un celu en estado `device` y `adb reverse tcp:P tcp:P` salió bien.
  - `loops.run_every(interval: float, task: Callable[[], None], name: str, log: Callable[[str], None], stop: threading.Event) -> threading.Thread` — hilo daemon: corre `task` ya y después cada `interval` hasta `stop`; una excepción → `log(f"{name}: {exc}")` y sigue.
  - `app.main() -> int`; `server.py` = `raise SystemExit(main())`.

- [ ] **Step 1: Write the failing tests**

```python
# test_adb.py
def test_no_adb_installed(self):            # which → None: False y run nunca se llama
def test_no_device(self):                   # "List of devices attached\n\n" → False, sin reverse
def test_unauthorized_is_not_a_device(self):# "ABC\tunauthorized\n" → False
def test_device_gets_reverse(self):         # "ABC\tdevice\n" → True; run llamado con ["adb", "reverse", "tcp:8765", "tcp:8765"]
def test_adb_errors_are_false(self):        # run lanza TimeoutExpired / FileNotFoundError, o reverse con returncode 1 → False

# test_loops.py
def test_keeps_running_after_errors(self):  # task falla la 1ª vez, anda la 2ª; interval 0.01 → log recibió "x: boom" y task corrió ≥ 2 veces
def test_stop_ends_thread(self):            # stop.set() → thread termina (join(1))
```

- [ ] **Step 2:** Run `/usr/bin/python3 -m unittest tests.test_adb tests.test_loops -v` → Expected: FAIL.
- [ ] **Step 3: Implement** `net.py`, `adb.py`, `loops.py`.
- [ ] **Step 4:** Run → Expected: PASS.
- [ ] **Step 5: Implement `app.main()`:**
  1. `load_config(root / "config.json", root / "config.example.json")`; `ConfigError` → `print(f"config.json: {e}")`, `return 1`; si se creó → avisar que lo edite.
  2. `Store`, `PhotoLibrary(Path(cfg.photos_dir).expanduser() if cfg.photos_dir else None)`, `stop = threading.Event()`.
  3. Bucles con `run_every`: GitHub cada 1800 s (si hay `github_user`); Claude cada 300 s (si `cfg.claude`; sin token → excepción `"Claude Code token not found"`); clima cada 900 s (si hay `city`: la primera vez resuelve el lugar e imprime `Weather: <label>`, o `Weather: city not found: <city>` y deja de intentar; idioma del geocoding = `cfg.language` si es `es`/`en`, si no `en`); fotos cada 60 s; adb cada 10 s, imprimiendo solo cuando cambia (`USB: phone connected` / `USB: phone disconnected`).
  4. `make_server("0.0.0.0" if cfg.wifi else "127.0.0.1", cfg.port, root / "web", get_state, photos.path)`; `get_state` = `build_state(store, cfg, pick_language(cfg.language, accept_language), link, datetime.now().astimezone(), photos.count())`. `OSError` de puerto ocupado → `print(f'Port {cfg.port} is already in use. Change "port" in config.json.')`, `return 1`.
  5. Imprime `vitrina is running` + `WiFi:  http://<lan_ip>:<port>` (si `wifi` y hay IP) + `Cable: http://localhost:<port>`. `serve_forever()`; `KeyboardInterrupt` → `stop.set()`, cerrar, `return 0`.
- [ ] **Step 6: Verify manualmente** (crea `config.json` con tu `github_user`, `"claude": true`, `city` y `photos_dir` reales)
  - `/usr/bin/python3 server.py` → imprime el lugar del clima y las dos direcciones, sin errores.
  - `curl -s localhost:8765/api/state | /usr/bin/python3 -m json.tool` → `panels` con los 4 paneles; `claude.session.pct` coincide con lo que muestra `/usage` en Claude Code (**esto confirma la forma real de la respuesta**; si difiere, corregir el fixture de Task 5 y `parse_usage`).
  - Con el server corriendo, otra terminal: `/usr/bin/python3 server.py` → `Port 8765 is already in use…` y código de salida 1 (Review Focus 3).
  - `"city": "Ciudadinexistente"` → `Weather: city not found…` y el server sigue (Review Focus 4).
  - `"port": "abc"` → `config.json: …` sin traceback.
  - Guardar el HTML real de tu calendario (`curl -s https://github.com/users/<user>/contributions`) y comprobar en un REPL que `parse_contributions` da 365–371 días con niveles 0–4. No se guarda en el repo.
- [ ] **Step 7:** Run `/usr/bin/python3 -m unittest -v` → Expected: todo PASS.
- [ ] **Step 8: Commit** `feat: wire up server startup, adb reverse and background refresh`

---

### Task 11: Página: base, hora y clima

**Files:**
- Create: `web/index.html`, `web/styles.css`, `web/app.js`, `web/weather-icons.svg`, `web/fonts/big-shoulders-display.woff2`, `web/fonts/atkinson-hyperlegible-next.woff2`, `web/fonts/OFL-BigShouldersDisplay.txt`, `web/fonts/OFL-AtkinsonHyperlegibleNext.txt`

Partir de `spike/preview.html` (local, fuera del repo) y de spec §7 "Dirección visual" (tokens, tipografías, layout de la hora, esquina, barra de progreso, fundido), sin copiar sus datos falsos ni Google Fonts.

- [ ] **Step 1: Fuentes.** Pedir `https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible+Next:wght@400;700&family=Big+Shoulders+Display:wght@300;500;700&display=swap` con un User-Agent de Chrome y bajar el `woff2` del bloque `/* latin */` de cada familia (son variables: un archivo por familia cubre todos los pesos). Licencias desde `https://raw.githubusercontent.com/google/fonts/main/ofl/<bigshouldersdisplay|atkinsonhyperlegiblenext>/OFL.txt`. `@font-face` con `font-weight: 100 900`.
- [ ] **Step 2: `index.html` + `styles.css`.** Secciones `#clock`, `#github`, `#claude`, `#photos` (las tres últimas vacías por ahora), `.corner` (hora + estado), `.progress`. En `#clock`, bloque de clima arriba a la derecha (ícono + temperatura grande en Big Shoulders; debajo `label · max° / min°` en `--mist`), oculto si `weather` es `null`. Estado "sin conexión": punto en `--haze` y texto `strings.offline` en la esquina.
- [ ] **Step 3: `weather-icons.svg`.** Sprite con `<symbol>` ids `clear-day`, `clear-night`, `partly_cloudy-day`, `partly_cloudy-night`, `cloudy`, `fog`, `drizzle`, `rain`, `snow`, `storm`: trazo de línea con `stroke="currentColor"`, sin relleno, mismo grosor en todos; el sol en `--lamp-3`, el resto en `--moon`. Se usa con `<svg><use href="weather-icons.svg#id"/></svg>`; id = `condition` + (`-day`/`-night` solo para `clear` y `partly_cloudy`).
- [ ] **Step 4: `app.js`.**
  - `poll()` al cargar y cada 30 s: `fetch('/api/state', {cache: 'no-store'})` con `AbortController` de 10 s. Bien → `render(state)` y quita "sin conexión". Falla → muestra "sin conexión" y conserva todo lo demás.
  - Rotación sobre `state.panels`, `seconds_per_panel` cada uno; si cambia la lista, sigue en el panel actual si todavía está. Tocar = siguiente panel (y, en Chrome, `requestFullscreen` + `wakeLock`, ignorando errores).
  - `?panel=<id>` fija ese panel y frena la rotación (para capturas y para revisar).
  - Antes del primer dato se muestra solo `clock`, sin clima ni barra de progreso.
  - Reloj y fecha cada segundo con `Intl.DateTimeFormat(state.lang)` (antes del primer dato: idioma del navegador). `document.documentElement.lang = state.lang`.
  - `.corner` oculta en `clock`; texto `strings.link_usb`/`link_wifi` según `state.link`.
- [ ] **Step 5: Verify** con el server corriendo:

```sh
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --hide-scrollbars --window-size=890,396 --force-device-scale-factor=1.75 \
  --virtual-time-budget=4000 --screenshot=/tmp/vitrina-clock.png 'http://localhost:8765/?panel=clock'
```

  Expected (mirar la captura): hora enorme abajo a la izquierda, día y fecha a la derecha, clima arriba a la derecha con ícono, temperatura y `label · max° / min°`, fuentes correctas (Big Shoulders angosta, no Arial). Repetir con `"city": ""` → sin bloque de clima y sin hueco raro.
- [ ] **Step 6: Verify sin conexión (Review Focus 5):** abrir `http://localhost:8765` en Chrome de escritorio, cortar el server → en ≤ 40 s aparece "sin conexión" y el reloj sigue; volver a arrancarlo → desaparece solo, sin recargar.
- [ ] **Step 7: Commit** `feat: add display page with clock and weather`

---

### Task 12: Página: GitHub, Claude y fotos

**Files:**
- Modify: `web/index.html`, `web/styles.css`, `web/app.js`

- [ ] **Step 1: GitHub.** Como la maqueta: título, tres números (`total` con separador de miles de `Intl.NumberFormat(lang)`, `streak`, `today`), meses (`Intl.DateTimeFormat(lang, {month: 'short'})` sin el punto, en la columna `week`), grilla de 53 columnas con `weeks` (`None` → celda invisible), leyenda menos/más.
- [ ] **Step 2: Claude.** Como la maqueta (este panel "le encantó" al usuario: no cambiar su estilo). Nota de sesión: `claude_resets_in` con `duration_hm` (≥ 1 h) o `duration_m`, recalculada cada segundo desde `resets_at`; si `resets_at` es `null`, sin nota. Semana: `claude_resets_on` con día (`weekday: 'long'`) y hora (`HH:MM`, 24 h) y, si `elapsed_pct` no es `null`, la marca de ritmo + `claude_week_elapsed`. Si `session` o `week` es `null`, ese medidor no se muestra.
- [ ] **Step 3: Fotos.** Una foto por vuelta, avanzando por `state.photos` en orden (índice módulo largo). Antes de mostrar el panel, la foto ya está cargada (`img.decode()`); si falla, se saltea el panel en esa vuelta. Horizontal → `object-fit: cover`. Vertical (`naturalHeight > naturalWidth`) → `contain` encima de la misma foto con `cover` + `filter: blur(24px) brightness(.55)`. Degradé superior de la maqueta para que la esquina se lea.
- [ ] **Step 4: Verify** con capturas como en Task 11 para `?panel=github`, `?panel=claude` y `?panel=photos` (en la carpeta, una foto horizontal y una vertical). Expected: igual a la maqueta con datos reales; números sin cortarse; la vertical entera sobre fondo desenfocado. Con `"github_user": ""` y `"claude": false` → solo hora y fotos en la rotación.
- [ ] **Step 5: Commit** `feat: render GitHub, Claude and photo panels`

---

### Task 13: README y prueba en el Nokia

**Files:**
- Create: `README.md` (inglés), `README.es.md` (castellano)

- [ ] **Step 1: README** (los dos con el mismo contenido): qué es; requisitos (Python 3.9+, nada para instalar); arranque (`git clone`, `python3 server.py`, editar `config.json`); tabla de opciones de `config.json`; conectar el celu por cable (`adb`, se hace solo) y por WiFi (usar la dirección que imprime el server; fijar la IP de la PC en el router); **por ahora en Chrome** (la app llega con el Plan 2); panel de Claude (opt-in, endpoint no documentado, macOS pide permiso del Keychain la primera vez, el token no sale de la PC); privacidad (con `"wifi": true` cualquiera en tu red puede ver la página y tus fotos; `"wifi": false` para solo cable); "Weather data by Open-Meteo.com"; fuentes OFL; licencia MIT.
- [ ] **Step 2: Verify en el Nokia por cable:** server corriendo con el celu enchufado → la consola imprime `USB: phone connected`; abrir `http://localhost:8765` en Chrome del celu, tocar para pantalla completa; `adb exec-out screencap -p > /tmp/n-<panel>.png` en cada panel. Expected: igual que las capturas de escritorio, esquina dice `USB`. Poner en la carpeta una foto de cámara de ≥ 12 MP: si el fundido a esa foto se traba en el Nokia, agregar al README la recomendación de fotos de ~1600 px (spec §10).
- [ ] **Step 3: Verify en el Nokia por WiFi:** `adb kill-server`, abrir la dirección `WiFi:` en Chrome del celu → anda igual, esquina dice `WiFi`. Cortar el server → "sin conexión"; arrancarlo → se recupera solo.
- [ ] **Step 4: Commit** `docs: add README in English and Spanish`
