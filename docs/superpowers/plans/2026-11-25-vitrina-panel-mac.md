# vitrina — panel "Mac" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sumar a la rotación un panel "Mac" con CPU, GPU, memoria y red de los últimos 5 min, más disco y batería, con una carga despreciable sobre la Mac.

**Architecture:** La Mac lee con `ctypes` cada 5 s (`vitrina/macstats.py`), hace las cuentas y guarda 5 min de historia (`vitrina/metrics.py`); la sirve en `GET /api/metrics`. El celu pide esa dirección cada 5 s solo con el panel en pantalla y dibuja todo (`web/`). La lectura se pausa si nadie consultó en 60 s.

**Tech Stack:** Python 3.9 (solo biblioteca estándar: `ctypes`, `unittest`), HTML/CSS/JS sin build; Chrome sin ventana y `node --check` para verificar.

**Spec:** `docs/superpowers/specs/2026-11-25-vitrina-panel-mac-design.md` (léela entera antes de empezar: el diseño visual está en su §5 y los textos en su Apéndice A).

## Global Constraints

- **Frenar antes de lo irreversible.** Todo va en la rama **`feat/mac-panel`** (desde `main`). No hagas `git push`, no mergees a `main`, no hagas release, hasta que la auditoría del Task 8 pase y el usuario diga que sí.
- **Commits sin atribución:** nunca `Co-Authored-By` ni líneas de "generated with". Mensajes en inglés, estilo del repo: `feat(mac): …`, `docs(mac): …`.
- Python **3.9.6** (`/usr/bin/python3`), solo biblioteca estándar, `from __future__ import annotations` en archivos nuevos. Sin dependencias, sin `sudo`, sin permisos nuevos de macOS.
- **Nada de abrir programas en la lectura de 5 s.** Solo `pmset -g batt` (cada 30 min) y `scutil --get ComputerName` (una vez), los dos con `timeout=10` y lista de argumentos (nunca `shell=True`).
- Constantes de la spec: lectura cada **5 s**, ventana **300 s**, salto que vacía la historia **> 15 s**, pausa sin pedidos **> 60 s**, disco y batería cada **1800 s**, tope mínimo de la escala de red **1 000 000 B/s**.
- Colores (spec §5): fondo del panel `#0D1126`, card `#1A2142`, CPU `#338ced`, GPU `#e76624`, memoria `#00a888`, red bajada `#d28e05`, red subida `#e24d8b`, disco `#0aac23`, batería `#9887ef`. Números y textos en `--moon`/`--mist`, nunca en el color del dato.
- `web/index.html` sin atributos `style=""` ni `<style>`/`<script>` en línea (la CSP de la demo del sitio los bloquea): los colores van como clases en `styles.css`; desde JS, `element.style.setProperty` sí vale.
- Datos del servidor en la página **siempre con `textContent`**, nunca `innerHTML` (el nombre de la Mac lo elige el usuario).
- Tests: `/usr/bin/python3 -m unittest` tiene que quedar en verde al final de cada task; usan carpetas temporales, nunca la config real.
- No se tocan `android/` ni `website/`. Los scripts temporales y capturas van al scratchpad de la sesión que ejecute (abajo `$S`), nunca al repo.
- Referencias (no están en git, sí en esta máquina): `spike/panel-mac/maqueta-b2.html` (diseño), `mach.py`, `vm.py`, `gpu.py`, `net.py` (lecturas probadas en esta Mac M4).

## Review Focus

1. **Intervalo que se filtra:** `setPanels()` vuelve a llamar `show(current)` en cada `/api/state`; si `show('mac')` arranca otro `setInterval` sin mirar si ya hay uno, los pedidos se multiplican. → Task 6, paso de conteo de pedidos.
2. **Reloj que vuelve atrás o Mac que durmió:** la historia se vacía y la muestra siguiente es solo punto de partida. → Task 2, `test_clock_going_back_resets_history` y `test_gap_over_15s_resets_history`.
3. **Contadores de 32 bits que vuelven a cero y dos lecturas en el mismo instante:** nada de porcentajes negativos ni divisiones por cero. → Task 1, `test_cpu_percent_wraps`, `test_rate_wraps`, `test_rate_without_elapsed_time`.
4. **Nombre de la Mac con caracteres de HTML** (`<b>x</b> & "y"`): se ve tal cual. → Task 6, paso de vista previa.
5. **Datos vacíos o incompletos** (recién arrancó, sin GPU, Mac de escritorio sin batería): el panel muestra `–` o esconde la card, sin errores en la consola. → Task 6, paso de vista previa con la variante vacía.

---

## Mapa de archivos

| Archivo | Responsabilidad |
|---|---|
| `vitrina/metrics.py` (nuevo) | Cuentas puras, lectura de `pmset`, tolerancia a fallas y la clase `Metrics` (historia, pausa, cuerpo de `/api/metrics`). Sin `ctypes`: se testea en cualquier sistema. |
| `vitrina/macstats.py` (nuevo) | Lecturas de macOS (`ctypes` a Mach, IOKit y `getifaddrs`; `pmset`; `scutil`; disco). Se importa solo en macOS. La spec decía un solo `metrics.py`; se separa para que los tests de las cuentas no carguen frameworks de macOS (spec §10 deja la forma al constructor). |
| `vitrina/config.py`, `config.example.json` | Opción `"mac": false`. |
| `vitrina/handler.py` | Ruta `/api/metrics`. |
| `vitrina/state.py` | Panel `mac` en la rotación. |
| `vitrina/app.py` | Arranca las lecturas y anota cada pedido. |
| `vitrina/i18n.py` | Textos del Apéndice A. |
| `web/index.html`, `web/app.js`, `web/styles.css` | El panel. |
| `README.md`, `README.es.md` | La opción y una sección corta del panel. |
| `tests/test_metrics.py`, `tests/test_macstats.py` (nuevos) + `test_config`, `test_handler`, `test_state`, `test_app`, `test_i18n`, `test_website_build` | Pruebas. |

---

### Task 0: Rama y documentos

- [ ] **Step 1:** `git switch -c feat/mac-panel` desde `main` limpio.
- [ ] **Step 2:** Commit de la spec y este plan:

```bash
git add docs/superpowers/specs/2026-11-25-vitrina-panel-mac-design.md docs/superpowers/plans/2026-11-25-vitrina-panel-mac.md
git commit -m "docs(mac): spec and plan for the Mac panel"
```

---

### Task 1: Cuentas y lectura de `pmset` (`vitrina/metrics.py`)

**Files:**
- Create: `vitrina/metrics.py`, `tests/test_metrics.py`

**Interfaces:**
- Produces (en `vitrina/metrics.py`):
  - `INTERVAL = 5`, `WINDOW = 300`, `MAX_GAP = 15`, `IDLE = 60`, `SLOW = 1800`
  - `cpu_percent(prev: tuple[int, int, int, int], cur: tuple[int, int, int, int]) -> float | None` — ticks `(user, system, idle, nice)`; % = Δ(user+system+nice) / Δ(total) × 100; cada Δ módulo 2³²; `None` si Δtotal es 0.
  - `rate(prev: int, cur: int, seconds: float) -> int | None` — bytes/s, Δ módulo 2³², redondeado a entero; `None` si `seconds <= 0`.
  - `memory_used(internal: int, purgeable: int, wired: int, compressor: int, page_size: int) -> int` — `(internal − purgeable + wired + compressor) × page_size`.
  - `parse_battery(text: str) -> dict | None` — `{"pct": int, "state": "ac" | "charging" | "battery"}`; `None` sin línea `InternalBattery`.
  - `read_all(readers: dict[str, Callable[[], object]], log: Callable[[str], None], failing: set[str]) -> dict[str, object]` — llama cada lector; si uno lanza, su valor es `None` y se loguea `f"Mac panel: {name}: {exc}"` solo si `name` no estaba en `failing` (y se agrega); si vuelve a andar, se saca de `failing`.

- [ ] **Step 1: Write the failing tests** (`tests/test_metrics.py`, clase `MathTest` y `BatteryTest` y `ReadAllTest`)

```python
REAL_PMSET = "Now drawing from 'AC Power'\n -InternalBattery-0 (id=23134307)\t80%; AC attached; not charging present: true\n"

def test_cpu_percent(self):
    self.assertEqual(cpu_percent((100, 50, 850, 0), (130, 60, 900, 10)), 50.0)
def test_cpu_percent_wraps(self):
    self.assertEqual(cpu_percent((2**32 - 10, 0, 0, 0), (10, 0, 20, 0)), 50.0)
def test_cpu_percent_without_elapsed_ticks(self):
    self.assertIsNone(cpu_percent((1, 1, 1, 1), (1, 1, 1, 1)))
def test_rate(self):
    self.assertEqual(rate(1000, 6000, 5), 1000)
def test_rate_wraps(self):
    self.assertEqual(rate(2**32 - 1000, 4000, 5), 1000)
def test_rate_without_elapsed_time(self):
    self.assertIsNone(rate(1, 2, 0))
    self.assertIsNone(rate(1, 2, -5))
def test_memory_used(self):
    self.assertEqual(memory_used(600_000, 50_000, 200_000, 100_000, 16384), 13_926_400_000)

def test_battery_on_ac_not_charging(self):   # the real output of the M4
    self.assertEqual(parse_battery(REAL_PMSET), {"pct": 80, "state": "ac"})
def test_battery_charging(self):
    text = "Now drawing from 'AC Power'\n -InternalBattery-0 (id=1)\t45%; charging; 1:20 remaining present: true\n"
    self.assertEqual(parse_battery(text), {"pct": 45, "state": "charging"})
def test_battery_discharging_is_not_charging(self):   # "discharging" contains "charging"
    text = "Now drawing from 'Battery Power'\n -InternalBattery-0 (id=1)\t72%; discharging; 5:10 remaining present: true\n"
    self.assertEqual(parse_battery(text), {"pct": 72, "state": "battery"})
def test_battery_charged_on_ac(self):
    text = "Now drawing from 'AC Power'\n -InternalBattery-0 (id=1)\t100%; charged; 0:00 remaining present: true\n"
    self.assertEqual(parse_battery(text), {"pct": 100, "state": "ac"})
def test_desktop_mac_has_no_battery(self):
    self.assertIsNone(parse_battery("Now drawing from 'AC Power'\n"))
    self.assertIsNone(parse_battery(""))

def test_read_all_tolerates_and_logs_once(self):
    logs, failing = [], set()
    def boom(): raise OSError("nope")
    readers = {"a": lambda: 1, "b": boom}
    self.assertEqual(read_all(readers, logs.append, failing), {"a": 1, "b": None})
    read_all(readers, logs.append, failing)
    self.assertEqual(logs, ["Mac panel: b: nope"])
def test_read_all_logs_again_after_recovering(self):
    logs, failing, ok = [], set(), [False]
    def flaky():
        if not ok[0]: raise OSError("nope")
        return 2
    read_all({"b": flaky}, logs.append, failing)
    ok[0] = True
    self.assertEqual(read_all({"b": flaky}, logs.append, failing), {"b": 2})
    ok[0] = False
    read_all({"b": flaky}, logs.append, failing)
    self.assertEqual(len(logs), 2)
```

- [ ] **Step 2:** `/usr/bin/python3 -m unittest tests.test_metrics -v` → FAIL (`No module named 'vitrina.metrics'`).
- [ ] **Step 3:** Implementar las cinco funciones y las constantes en `vitrina/metrics.py`. `parse_battery`: el estado sale del segundo campo separado por `;` de la línea `InternalBattery` (`charging` o `finishing charge` → `"charging"`); si no, `'Battery Power'` en la primera línea → `"battery"`; si no, `"ac"`.
- [ ] **Step 4:** `/usr/bin/python3 -m unittest tests.test_metrics -v` → PASS; `/usr/bin/python3 -m unittest` → OK.
- [ ] **Step 5:** `git add vitrina/metrics.py tests/test_metrics.py && git commit -m "feat(mac): CPU, network and memory math, and pmset parsing"`

---

### Task 2: Historia, pausa y cuerpo de `/api/metrics` (`Metrics`)

**Files:**
- Modify: `vitrina/metrics.py`, `tests/test_metrics.py`

**Interfaces:**
- Consumes: `cpu_percent`, `rate`, las constantes (Task 1).
- Produces: `class Metrics` en `vitrina/metrics.py`:
  - `__init__(self, read: Callable[[], dict], ram_total: int, clock: Callable[[], float] = time.time)` — `read()` devuelve `{"cpu": (u, s, i, n) | None, "ram": int | None, "gpu": float | None, "net": (rx, tx) | None}`. El arranque cuenta como un pedido (`seen` = `clock()`).
  - `seen(self) -> None` — anota `clock()` como último pedido.
  - `tick(self) -> None` — si `clock() − último pedido > IDLE`, no llama a `read()`. Si no, lee y agrega una muestra `{"t": int, "cpu": float | None, "gpu": float | None, "ram": int | None, "down": int | None, "up": int | None}` (`cpu` y `gpu` redondeados a 1 decimal). Si es la primera, si pasaron más de `MAX_GAP` s desde la anterior o si el reloj volvió atrás: vacía la historia y la muestra es punto de partida (`cpu`, `down`, `up` en `None`). Descarta las muestras con `t <= ahora − WINDOW`.
  - `set_slow(self, disk: dict | None, battery: dict | None) -> None`
  - `ready` (propiedad, `bool`) — `True` desde la primera muestra con algún dato que no sea `None`; no vuelve a `False`.
  - `body(self) -> dict` — `{"interval": INTERVAL, "samples": [...copia...], "ram_total": int, "disk": dict | None, "battery": dict | None}`.
  - Todo protegido con un `threading.Lock` (`tick` corre en un hilo, `body` y `seen` en los del servidor).

- [ ] **Step 1: Write the failing tests** (clase `MetricsTest`; reloj falso `clock = lambda: now[0]`, lector falso que cuenta llamadas y devuelve, para el tick k, `cpu=(100+30k, 50+10k, 850+50k, 10k)`, `ram=12_000_000_000`, `gpu=6.0`, `net=(1000+5000k, 2000+500k)`):

```python
def test_first_tick_is_a_baseline(self):
    m = self.metrics(); m.tick()
    s = m.body()["samples"]
    self.assertEqual(len(s), 1)
    self.assertEqual((s[0]["cpu"], s[0]["down"], s[0]["up"]), (None, None, None))
    self.assertEqual((s[0]["ram"], s[0]["gpu"]), (12_000_000_000, 6.0))
    self.assertTrue(m.ready)
def test_second_tick_has_rates(self):
    m = self.metrics(); m.tick(); self.advance(5); m.tick()
    last = m.body()["samples"][-1]
    self.assertEqual((last["cpu"], last["down"], last["up"]), (50.0, 1000, 100))
def test_keeps_the_last_300_seconds(self):
    m = self.metrics()
    for _ in range(70): m.tick(); self.advance(5); m.seen()
    s = m.body()["samples"]
    self.assertEqual(len(s), 60)
    self.assertEqual(s[-1]["t"] - s[0]["t"], 295)
def test_gap_over_15s_resets_history(self):
    m = self.metrics(); m.tick(); self.advance(5); m.tick(); self.advance(16); m.tick()
    s = m.body()["samples"]
    self.assertEqual(len(s), 1); self.assertIsNone(s[0]["cpu"])
def test_clock_going_back_resets_history(self):
    m = self.metrics(); m.tick(); self.advance(5); m.tick(); self.advance(-30); m.tick()
    self.assertEqual(len(m.body()["samples"]), 1)
def test_pauses_without_requests_and_resumes(self):
    m = self.metrics(); self.advance(61); m.tick()
    self.assertEqual(self.reads, 0)
    m.seen(); m.tick()
    self.assertEqual(self.reads, 1)
def test_start_counts_as_a_request(self):
    m = self.metrics(); self.advance(60); m.tick()
    self.assertEqual(self.reads, 1)
def test_not_ready_without_any_data(self):
    m = Metrics(lambda: {"cpu": None, "ram": None, "gpu": None, "net": None}, 1, clock=lambda: 0.0)
    m.tick(); self.assertFalse(m.ready)
def test_body_shape(self):
    m = self.metrics(); m.tick()
    m.set_slow({"free": 3, "total": 5}, {"pct": 80, "state": "ac"})
    b = m.body()
    self.assertEqual(set(b), {"interval", "samples", "ram_total", "disk", "battery"})
    self.assertEqual((b["interval"], b["disk"], b["battery"]["state"]), (5, {"free": 3, "total": 5}, "ac"))
    json.dumps(b)
def test_body_is_a_copy(self):
    m = self.metrics(); m.tick()
    m.body()["samples"].clear()
    self.assertEqual(len(m.body()["samples"]), 1)
```

- [ ] **Step 2:** `/usr/bin/python3 -m unittest tests.test_metrics -v` → FAIL (`cannot import name 'Metrics'`).
- [ ] **Step 3:** Implementar `Metrics` según la interfaz.
- [ ] **Step 4:** `/usr/bin/python3 -m unittest tests.test_metrics -v` → PASS; suite completa → OK.
- [ ] **Step 5:** `git commit -am "feat(mac): five-minute history that pauses without a phone"` (agregá el test si `-a` no lo toma).

---

### Task 3: Lecturas de macOS (`vitrina/macstats.py`)

**Files:**
- Create: `vitrina/macstats.py`, `tests/test_macstats.py`

**Interfaces:**
- Consumes: `memory_used`, `parse_battery` (Task 1).
- Produces (en `vitrina/macstats.py`; **ningún framework se carga al importar**: un cargador con `functools.lru_cache` los abre en el primer uso):
  - `read_cpu_ticks() -> tuple[int, int, int, int]` — `host_statistics(mach_host_self(), HOST_CPU_LOAD_INFO=3, …)`, 4 × `c_uint` (como `spike/panel-mac/mach.py`).
  - `read_memory_used() -> int` — `host_statistics64(…, HOST_VM_INFO64=4, …)` con la estructura de `spike/panel-mac/vm.py` (152 bytes, count 38; ya verificada en el M4), página `os.sysconf("SC_PAGESIZE")`, y `memory_used(...)`.
  - `read_gpu() -> float | None` — IOKit como `spike/panel-mac/gpu.py`, liberando cada objeto (`IOObjectRelease`, `CFRelease`); la mayor de las utilizaciones; `None` si ningún servicio la informa.
  - `read_net() -> tuple[int, int]` — `getifaddrs` como `spike/panel-mac/net.py`, sumando solo interfaces `AF_LINK` cuyo nombre empieza con `b"en"`; siempre `freeifaddrs`.
  - `ram_total() -> int` — `os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGESIZE")`.
  - `read_disk() -> dict` — `shutil.disk_usage("/")` → `{"free": int, "total": int}`.
  - `read_battery(run=subprocess.run) -> dict | None` — `run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=10)` → `parse_battery(stdout)`; código de salida ≠ 0 → `None`.
  - `computer_name(run=subprocess.run) -> str` — `run(["scutil", "--get", "ComputerName"], …, timeout=10)`; nombre vacío, error o excepción (incluido `TimeoutExpired`) → `"Mac"`.
  - `READERS = {"cpu": read_cpu_ticks, "ram": read_memory_used, "gpu": read_gpu, "net": read_net}` y `SLOW_READERS = {"disk": read_disk, "battery": read_battery}`.

- [ ] **Step 1: Write the failing tests** (`tests/test_macstats.py`; `REAL_PMSET` es la misma constante del Task 1):

```python
def test_battery_uses_pmset(self):
    run = mock.Mock(return_value=subprocess.CompletedProcess([], 0, stdout=REAL_PMSET))
    self.assertEqual(read_battery(run), {"pct": 80, "state": "ac"})
    self.assertEqual(run.call_args.args[0], ["pmset", "-g", "batt"])
    self.assertEqual(run.call_args.kwargs["timeout"], 10)
def test_battery_failure_is_none(self):
    self.assertIsNone(read_battery(mock.Mock(return_value=subprocess.CompletedProcess([], 1, stdout=""))))
def test_computer_name(self):
    run = mock.Mock(return_value=subprocess.CompletedProcess([], 0, stdout="MacBook Air de Nico\n"))
    self.assertEqual(computer_name(run), "MacBook Air de Nico")
def test_computer_name_falls_back_to_mac(self):
    for run in (mock.Mock(side_effect=subprocess.TimeoutExpired("scutil", 10)),
                mock.Mock(return_value=subprocess.CompletedProcess([], 0, stdout="  \n")),
                mock.Mock(side_effect=FileNotFoundError())):
        self.assertEqual(computer_name(run), "Mac")
def test_importing_loads_no_framework(self):   # runs everywhere
    with mock.patch("ctypes.CDLL") as cdll:
        importlib.reload(macstats)
    cdll.assert_not_called()

@unittest.skipUnless(sys.platform == "darwin", "macOS only")
class RealReadersTest(unittest.TestCase):
    def test_values_in_range(self):
        a = read_cpu_ticks(); time.sleep(0.2); b = read_cpu_ticks()
        pct = cpu_percent(a, b)
        self.assertTrue(pct is None or 0 <= pct <= 100)
        self.assertTrue(0 < read_memory_used() < ram_total())
        gpu = read_gpu()
        self.assertTrue(gpu is None or 0 <= gpu <= 100)
        rx, tx = read_net()
        self.assertTrue(rx >= 0 and tx >= 0)
        d = read_disk()
        self.assertTrue(0 <= d["free"] <= d["total"])
```

- [ ] **Step 2:** `/usr/bin/python3 -m unittest tests.test_macstats -v` → FAIL (no existe el módulo).
- [ ] **Step 3:** Implementar `vitrina/macstats.py` portando los prototipos del spike (declarar `restype`/`argtypes` de cada función de C, como en `gpu.py`).
- [ ] **Step 4:** `/usr/bin/python3 -m unittest tests.test_macstats -v` → PASS (en esta Mac corre `RealReadersTest`); suite completa → OK.
- [ ] **Step 5:** `git add vitrina/macstats.py tests/test_macstats.py && git commit -m "feat(mac): read CPU, memory, GPU and network straight from macOS"`

---

### Task 4: Opción, ruta y panel en el estado

**Files:**
- Modify: `vitrina/config.py`, `config.example.json`, `vitrina/handler.py`, `vitrina/state.py`
- Test: `tests/test_config.py`, `tests/test_handler.py`, `tests/test_state.py`

**Interfaces:**
- Produces:
  - `Config.mac: bool = False` (y `"mac": false` en `config.example.json`, después de `"claude"`).
  - `make_server(..., tls, secret, get_metrics: Callable[[], dict | None] = lambda: None)` — `GET /api/metrics`, después del chequeo de `Host` y de clave: `None` → 404; si no, 200 JSON con `Cache-Control: no-store`.
  - `build_state`: si `config.mac` y `store.get("mac")` (un `{"name": str}`), agrega `"mac"` a `panels` después de `claude` y antes de `photos`, y `state["mac"] = {"name": ...}` (con `_add`, así un dato roto solo saca ese panel).

- [ ] **Step 1: Write the failing tests**

```python
# test_config.py
def test_mac_must_be_boolean(self):
    self.write('{"mac": "yes"}')
    with self.assertRaisesRegex(ConfigError, '"mac" must be true or false'):
        load_config(self.path, EXAMPLE)
# (test_example_matches_defaults ya obliga a sumar "mac": false al ejemplo)

# test_handler.py — el setUp pasa get_metrics=lambda: self.metrics, con self.metrics = {"interval": 5, "samples": []}
def test_metrics(self):
    resp, body = self.get("/api/metrics")
    self.assertEqual((resp.status, resp.getheader("Cache-Control")), (200, "no-store"))
    self.assertEqual(json.loads(body), {"interval": 5, "samples": []})
def test_metrics_turned_off_is_404(self):
    self.metrics = None
    self.assertEqual(self.get("/api/metrics")[0].status, 404)
def test_metrics_needs_the_key_and_a_local_host(self):
    self.assertEqual(self.get("/api/metrics", key=None)[0].status, 401)
    self.assertEqual(self.get("/api/metrics", {"Host": "evil.example"})[0].status, 403)

# test_state.py
def test_mac_panel_goes_after_claude(self):
    store = full_store(); store.set("mac", {"name": "MacBook Air de Nico"})
    s = build_state(store, Config(github_user="x", claude=True, mac=True), "es", "usb", NOW, 2)
    self.assertEqual(s["panels"], ["clock", "github", "claude", "mac", "photos"])
    self.assertEqual(s["mac"], {"name": "MacBook Air de Nico"})
def test_mac_panel_needs_the_option_and_a_reading(self):
    store = Store(); store.set("mac", {"name": "x"})
    self.assertNotIn("mac", build_state(store, Config(), "es", "usb", NOW, 0)["panels"])
    self.assertNotIn("mac", build_state(Store(), Config(mac=True), "es", "usb", NOW, 0)["panels"])
```

- [ ] **Step 2:** `/usr/bin/python3 -m unittest tests.test_config tests.test_handler tests.test_state -v` → FAIL.
- [ ] **Step 3:** Implementar los tres cambios y el ejemplo.
- [ ] **Step 4:** Esos tests → PASS; suite completa → OK (incluye `test_website_build`: la demo no prende `"mac"`).
- [ ] **Step 5:** `git commit -am "feat(mac): mac option, /api/metrics route and the panel in the rotation"`

---

### Task 5: Arranque de las lecturas (`vitrina/app.py`)

**Files:**
- Modify: `vitrina/app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `Metrics`, `read_all`, `INTERVAL`, `SLOW` (Tasks 1–2); `READERS`, `SLOW_READERS`, `ram_total`, `computer_name` (Task 3); `make_server(get_metrics=…)` (Task 4).
- Produces: en `main()`, si `cfg.mac`:
  - fuera de macOS (`sys.platform != "darwin"`): `log("The Mac panel only works on macOS.")` y nada más;
  - en macOS, con `from . import macstats` **dentro** del `if`: `metrics = Metrics(lambda: read_all(macstats.READERS, log, failing), macstats.ram_total())`; `name = macstats.computer_name()`; `run_every(INTERVAL, tick, "Mac", log, stop)` donde `tick` llama `metrics.tick()` y, si `metrics.ready`, `store.set("mac", {"name": name})`; `run_every(SLOW, slow, "Mac disk and battery", log, stop)` donde `slow` hace `metrics.set_slow(**read_all(macstats.SLOW_READERS, log, failing_slow))`.
  - `get_state` llama `metrics.seen()` antes de armar el estado (si hay `metrics`); `get_metrics = lambda: (metrics.seen(), metrics.body())[1]` o `lambda: None` sin `metrics`.
  - Las lecturas arrancan **después** de que `make_server` haya tomado el puerto (como las otras fuentes), para que `get_metrics` no se use antes de existir: armá `metrics` antes de `make_server` y arrancá los `run_every` en `_start_sources`.

- [ ] **Step 1: Write the failing tests** (`tests/test_app.py`, usando `serve_until_long_sleep`):

```python
def test_mac_panel_outside_macos_is_reported(self):
    with mock.patch("vitrina.app.sys.platform", "linux"):
        code, out, *_ = self.serve_until_long_sleep({"port": self.free_port(), "wifi": False, "mac": True})
    self.assertEqual(code, 0)
    self.assertIn("The Mac panel only works on macOS.", out)

@unittest.skipUnless(sys.platform == "darwin", "macOS only")
def test_mac_panel_starts_on_macos(self):
    with mock.patch("vitrina.app.Metrics", wraps=Metrics) as metrics:
        code, out, *_ = self.serve_until_long_sleep({"port": self.free_port(), "wifi": False, "mac": True})
    self.assertEqual(code, 0)
    metrics.assert_called_once()
    self.assertNotIn("Mac panel:", out)   # no reader failed
```

- [ ] **Step 2:** `/usr/bin/python3 -m unittest tests.test_app -v` → FAIL.
- [ ] **Step 3:** Implementar el cableado según la interfaz.
- [ ] **Step 4:** `tests.test_app` → PASS; suite completa → OK.
- [ ] **Step 5:** `git commit -am "feat(mac): start the readers with vitrina and note each request"`

---

### Task 6: El panel en el celu (`web/` + textos)

**Files:**
- Modify: `web/index.html`, `web/app.js`, `web/styles.css`, `vitrina/i18n.py`
- Test: `tests/test_i18n.py`, `tests/test_website_build.py`

**Interfaces:**
- Consumes: `state.mac.name`, los textos `mac_*`, `GET /api/metrics` (Tasks 4–5).
- Produces: la sección `<section class="panel mac" id="mac">` y en `app.js`: `renderers.mac`, `startMetrics()`, `stopMetrics()`, `fetchMetrics()`, `drawMac(m)`.

- [ ] **Step 1: Write the failing tests**

```python
# test_i18n.py
def test_mac_copy(self):
    self.assertEqual(STRINGS["es"]["mac_window"], "últimos 5 min")
    self.assertEqual(STRINGS["es"]["mac_on_battery"], "con batería")
    self.assertEqual(STRINGS["en"]["mac_disk_free"], "{free} free")
# test_website_build.py, en test_javascript_parses: sumar ROOT / "web" / "app.js" a los archivos que pasan por `node --check`.
```

- [ ] **Step 2:** `/usr/bin/python3 -m unittest tests.test_i18n -v` → FAIL.
- [ ] **Step 3:** Textos: las 12 claves del Apéndice A de la spec, en es y en, en `vitrina/i18n.py`.
- [ ] **Step 4:** `index.html`: la sección con la fila de título (`#mac-name` + `#mac-window`) y las seis cards de la spec §5, cada una con su clase de color (`mac-cpu`, `mac-gpu`, `mac-ram`, `mac-net`, `mac-disk`, `mac-battery`) que define `--c` en `styles.css`. Sin `style=""`.
- [ ] **Step 5:** `styles.css`: portar el CSS de `spike/panel-mac/maqueta-b2.html` (variante `.v-tint`) pasando `cqh`→`vh` y `cqw`→`vw`, con el fondo `#0D1126` en `.mac` (como `.claude` tiene el suyo). Esquina y barra de progreso sin cambios.
- [ ] **Step 6:** `app.js`:
  - `renderers.mac(s)`: nombre y textos con `textContent`.
  - En `show(id)`: `id === 'mac' ? startMetrics() : stopMetrics()`. **`startMetrics` no hace nada si ya hay un intervalo**; si no, `fetchMetrics()` y `setInterval(fetchMetrics, 5000)`. `stopMetrics` hace `clearInterval` y lo deja en `null`.
  - `fetchMetrics()`: como `poll()` (timeout con `AbortController`, `no-store`); si falla, no toca el dibujo.
  - `drawMac(m)`: valor grande = el último valor no `null` de cada serie, `–` si no hay; la card de GPU se esconde si ninguna muestra trae `gpu`; la de batería si `m.battery` es `null` (y la de disco si `m.disk` es `null`), y la otra card chica ocupa la fila; formatos, ejes, escala de red, línea cortada en `null` y colores tal como la spec §5 y §6.4 (el dibujo de la maqueta es el punto de partida; los colores se leen de `--c` con `getComputedStyle`).
- [ ] **Step 7:** `/usr/bin/python3 -m unittest` → OK (incluye `node --check web/app.js`).
- [ ] **Step 8: Vista previa.** En `$S/macprev/`: copia de `web/`; `api/state` = `json.dumps(build_state(store, Config(mac=True, seconds_per_panel=15), "es", "wifi", now, 0))` con `store.set("mac", {"name": '<b>x</b> & "y"'})`; `api/metrics` = 60 muestras de ejemplo cada 5 s, `ram_total` de 24 GiB, disco y batería. Servir con `python3 -m http.server 8793 --bind 127.0.0.1 --directory $S/macprev 2> $S/macprev.log` y capturar con Chrome sin ventana a 890×396, `?panel=mac`. Comprobar: se parece a la maqueta B2; el título muestra `<b>x</b> & "y"` tal cual.
- [ ] **Step 9: Variante vacía.** `api/metrics` con `samples: []`, `disk: null`, `battery: null`, y otra con todas las `gpu` en `null`: el panel muestra `–` o esconde las cards, y la consola (`--enable-logging=stderr --v=0`) no tiene errores.
- [ ] **Step 10: Conteo de pedidos.** Sin `?panel=`, con Chrome sin ventana y `--virtual-time-budget=120000`: en `$S/macprev.log`, los `GET /api/metrics` tienen que ser del orden de 4 visitas × 4 pedidos (entre 12 y 20). Con un intervalo filtrado serían 30 o más.
- [ ] **Step 11:** `git commit -am "feat(mac): the Mac panel on the phone"`

---

### Task 7: README y prueba en la Mac y el Nokia

**Files:**
- Modify: `README.md`, `README.es.md`

- [ ] **Step 1:** READMEs (en y es, mismo contenido): sumar el panel a la lista de arriba ("**Mac**: CPU, GPU, memory and network over the last 5 minutes, plus disk and battery"); la fila `mac` | `false` en la tabla de `config.json`; y una sección corta "The Mac panel" / "El panel Mac": qué lee, que lo hace sin `sudo` ni programas extra, que corre solo mientras vitrina corre, que se pausa si el celu no consulta en un minuto, y que el celu dibuja todo.
- [ ] **Step 2:** `git commit -am "docs(mac): document the Mac panel"`
- [ ] **Step 3:** En el `config.json` local (ignorado por git) poner `"mac": true`; `vitrina stop`, `vitrina start`.
- [ ] **Step 4 (con el usuario):** en el Nokia el panel aparece después de Claude y se ve como B2; los números coinciden con el Monitor de Actividad dentro de unos puntos (CPU, memoria usada, red).
- [ ] **Step 5: Carga.** `PID=$(cat ~/Library/Application\ Support/vitrina/server.pid)`; `ps -o cputime= -p $PID` al empezar y a los 10 min, con el panel en la rotación. Repetir con `"mac": false`. La diferencia tiene que ser **menor a 1 s**.
- [ ] **Step 6:** `vitrina stop` → `pgrep -f server.py` no devuelve nada. Con `"mac": true`, desconectar el celu más de 1 min y volver: el gráfico arranca de nuevo desde la derecha.

---

### Task 8: Auditoría final (fallas y vulnerabilidades)

- [ ] **Step 1:** `/usr/bin/python3 -m unittest` en verde y `git diff main --stat` sin archivos fuera del mapa.
- [ ] **Step 2: Revisión de correctitud** de toda la rama contra `main` con superpowers:requesting-code-review, pasándole la spec y este plan.
- [ ] **Step 3: Revisión de seguridad** con la skill `security-review` sobre la rama. Además, a mano:
  - `/api/metrics` exige clave por cabecera y `Host` local, y no tiene parámetros que lleguen a `ctypes` ni a `subprocess`.
  - Los únicos `subprocess` nuevos son `pmset` y `scutil`, con lista de argumentos, `timeout=10` y sin datos del pedido.
  - La historia tiene tope (300 s) y el log no se llena (una línea por lector que falla).
  - `ctypes`: tipos de retorno y argumentos declarados; todo lo que se pide se libera (`freeifaddrs`, `IOObjectRelease`, `CFRelease`).
  - La página usa `textContent` para todo lo que viene del servidor.
  - `vitrina stop` no deja hilos ni procesos.
- [ ] **Step 4:** Cada hallazgo importante se arregla con TDD (test que falla → arreglo → verde) y un commit `fix(mac): …`; se repiten los pasos 1–3 sobre lo cambiado.
- [ ] **Step 5:** Informe al usuario: hallazgos, qué se arregló, qué quedó como menor. **Frenar acá:** merge a `main` y push solo con su OK.
