# vitrina — Plan 3: arrancar y frenar desde cualquier terminal, e ícono de la app

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `vitrina start` / `vitrina stop` desde cualquier carpeta (el server corre en segundo plano y se frena del
todo, liberando puerto y `adb`), el server se frena solo si la Mac durmió más de 1 h, y la app tiene ícono.

**Architecture:** un módulo nuevo `vitrina/control.py` encuentra el server con un candado `flock` sobre
`server.pid`, lo lanza desconectado de la terminal (`start_new_session`) y lo frena con `SIGTERM` (que el
server trata como Ctrl+C). `app.py` toma el candado, mira el reloj para detectar el reposo largo y al salir
limpia `adb`. `~/.local/bin/vitrina` es un enlace a `server.py`. El ícono es un ícono adaptable en XML.

**Tech Stack:** Python 3.9 stdlib (`fcntl`, `signal`, `subprocess`), Android resources (adaptive icon, vector).

**Spec:** `docs/superpowers/specs/2026-11-12-vitrina-design.md`, §8c (y §8b para lo que no cambia).

## Global Constraints

- **Solo macOS.** Python **3.9 stdlib**, sin dependencias; `from __future__ import annotations` en cada módulo.
  Tests: `/usr/bin/python3 -m unittest -v`. **Los tests usan carpetas temporales**, nunca
  `~/Library/Application Support/vitrina/`.
- Carpeta de secretos `0700`; `server.pid` y `server.log` `0600`. Reusar `pairing._private_dir`.
- **Nada arranca solo**: `start` lo corre el usuario. Sin emparejar no arranca (como hoy).
- Reposo largo = **más de 3600 s** de reloj de pared entre dos miradas; mirar cada **5 s**.
- Mensajes del server en inglés y sin trazas (`Traceback`) ante errores esperables.
- App: **sin librerías de terceros ni AndroidX**; `minSdk 26`; colores de `res/values/colors.xml`.
- Código, comentarios y commits en inglés, commits convencionales **sin ningún trailer**.
- Rama `feat/start-stop-and-icon`; se mergea a `main` cuando pasa la verificación de la Task 3 y la Task 4.

## Review Focus

1. **El comando corre por el enlace desde otra carpeta**: `~/.local/bin/vitrina` desde `~` encuentra el repo →
   test en Task 2 (`test_runs_through_a_link_from_another_folder`).
2. **Cerrar la terminal después de `start`** no frena el server → test en Task 1 (sesión propia, `os.getsid`).
3. **Un `server.pid` viejo** de un server que murió de golpe: `start` no dice "ya corre" y `stop` no le manda
   señales a otro proceso → test en Task 1 (`test_stale_pid_file_is_not_running`).
4. **Un server en primer plano en otra terminal**: `vitrina stop` lo frena igual que Ctrl+C y libera el puerto →
   verificación manual en Task 3.
5. **`adb` que ya estaba abierto por otro programa** (Android Studio, depuración): `stop` no lo cierra → test en
   Task 2 (`release` con `kill_daemon=False`) y test de `main` en Task 2.

## Estructura de archivos

```
vitrina/control.py      (nuevo) candado/pid, start, stop, watch_sleep
vitrina/adb.py          (mod) daemon_running, release
vitrina/app.py          (mod) start/stop/ya-corre, candado, reposo, limpieza al salir
server.py               (mod) ejecutable + SIGTERM = Ctrl+C
tests/test_control.py   (nuevo)
tests/test_adb.py, tests/test_app.py   (mod)
README.md, README.es.md (mod)
android/app/src/main/res/drawable/ic_launcher_foreground.xml   (nuevo)
android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml     (nuevo)
android/app/src/main/AndroidManifest.xml                       (mod)
```

---

### Task 1: `control.py` — encontrar, arrancar y frenar el server

**Files:** Create `vitrina/control.py`, `tests/test_control.py`.

**Interfaces — Produces:**
- `PIDFILE = "server.pid"`, `LOGFILE = "server.log"`
- `hold_lock(folder: Path) -> IO[str] | None` — abre/crea `folder/server.pid` (`os.open`, `0o600`, crea la carpeta
  con `_private_dir`), `fcntl.flock(LOCK_EX | LOCK_NB)`; si lo consigue escribe `os.getpid()` (truncando) y
  devuelve el archivo abierto (quien lo llama lo guarda vivo; cerrarlo suelta el candado). Si está tomado, `None`.
- `running_pid(folder: Path) -> int | None` — sin archivo → `None`; si puede tomar el candado (nadie lo tiene) lo
  suelta y devuelve `None`; si no puede, devuelve el pid escrito.
- `start(cmd: list[str], cwd: Path, folder: Path, timeout: float = 10.0) -> int`
- `stop(folder: Path, timeout: float = 10.0) -> int`
- `watch_sleep(on_long_sleep: Callable[[], None], stop: threading.Event, clock: Callable[[], float] = time.time, every: float = 5.0, limit: float = 3600.0) -> threading.Thread`

Comportamiento (textos exactos):
- `start`: si `running_pid(folder)` → imprime `vitrina is already running.` y devuelve `0` sin lanzar nada. Si no,
  abre `folder/server.log` truncado (`0o600`), lanza `subprocess.Popen(cmd, cwd=cwd, stdin=DEVNULL, stdout=log,
  stderr=STDOUT, start_new_session=True)` y cierra su copia del log. Cada 0,1 s: si el hijo terminó → imprime el
  log y devuelve `returncode or 1`; si `running_pid(folder) == hijo.pid` → imprime el log, después
  `Log: <ruta del log>`, y devuelve `0`. Pasado `timeout` → imprime el log y
  `vitrina is taking long to start. Log: <ruta>` y devuelve `1`.
- `stop`: sin server → `vitrina isn't running.` y `0`. Si hay: `os.kill(pid, SIGTERM)`, espera (cada 0,1 s) a que
  `running_pid` sea `None`; pasado `timeout` → `SIGKILL` y espera de nuevo. `ProcessLookupError` = ya terminó.
  Imprime `Stopped.` y devuelve `0`.
- `watch_sleep`: hilo daemon; `last = clock()`; mientras `not stop.wait(every)`: `now = clock()`; si
  `now - last > limit` → llama `on_long_sleep()` una vez y termina; si no, `last = now`.

- [ ] **Step 1: Tests que fallan** en `tests/test_control.py`. El hijo de prueba es
  `[sys.executable, "-c", CHILD]`, un script que agrega el repo a `sys.path`, imprime `vitrina is running`
  (flush), toma `hold_lock(<carpeta temporal>)` y duerme 60 s; variantes: ignora `SIGTERM`
  (`signal.signal(SIGTERM, SIG_IGN)` antes del candado) y falla (imprime `Not paired yet`, `sys.exit(1)`).
  Capturar stdout con `redirect_stdout`.
  - `test_lock_names_the_holder`: `f = hold_lock(d)` → `running_pid(d) == os.getpid()`; modo de `server.pid`
    `== 0o600`; `f.close()` → `running_pid(d) is None`.
  - `test_second_lock_is_refused`: con uno tomado, `hold_lock(d) is None`.
  - `test_stale_pid_file_is_not_running`: `server.pid` con `"12345"` y sin candado → `None`; carpeta sin archivo → `None`.
  - `test_start_then_stop`: `start(...) == 0`, salida contiene `vitrina is running` y `Log: `;
    `pid = running_pid(d)` no es `None`; `os.getsid(pid) != os.getsid(0)`; modo de `server.log` `0o600`;
    `stop(d) == 0`, salida contiene `Stopped.`; `running_pid(d) is None`.
  - `test_start_reports_a_failed_server`: hijo que falla → `start(...) == 1`, salida contiene `Not paired yet`.
  - `test_start_when_running_launches_nothing`: con `hold_lock(d)` tomado, `start` con un cmd que crearía un
    archivo marca → `0`, `vitrina is already running.`, la marca no existe.
  - `test_log_is_replaced_each_start`: `server.log` con `"old"` → después de `start`, el log no contiene `old`
    (frenar al final con `stop`).
  - `test_stop_when_nothing_runs`: `stop(d) == 0`, `vitrina isn't running.`
  - `test_stop_kills_a_server_that_ignores_sigterm`: hijo que ignora `SIGTERM`; `stop(d, timeout=1) == 0`;
    `running_pid(d) is None`.
  - `test_long_sleep_calls_back_once`: reloj falso que devuelve `0, 5, 10, 4000, 4005…`; `every=0.01` → el
    callback se llama una vez y el hilo termina (`join(1)`).
  - `test_short_gaps_never_call_back`: reloj que avanza de a 5; tras ~20 vueltas el callback no se llamó;
    `stop.set()` termina el hilo.
- [ ] **Step 2:** `/usr/bin/python3 -m unittest tests.test_control -v` → FAIL (no existe `vitrina.control`).
- [ ] **Step 3:** Implementar `vitrina/control.py` según las interfaces.
- [ ] **Step 4:** `/usr/bin/python3 -m unittest tests.test_control -v` → PASS; `/usr/bin/python3 -m unittest` → todo OK.
- [ ] **Step 5:** Commit `feat: find, start and stop the server from any terminal`.

### Task 2: el server usa el candado, se frena por reposo, limpia `adb` y anda por el enlace

**Files:** Modify `vitrina/adb.py`, `vitrina/app.py`, `server.py`; tests `tests/test_adb.py`, `tests/test_app.py`.

**Interfaces — Consumes:** todo lo de Task 1. **Produces:**
- `adb.daemon_running() -> bool` — algo atiende en `127.0.0.1:5037` (conexión con timeout 0,5 s).
- `adb.release(port: int, kill_daemon: bool, run=subprocess.run, which=shutil.which, running=daemon_running) -> None`
  — sin `adb` o sin daemon corriendo: no hace nada (correr `adb` lo arrancaría). Si `kill_daemon`:
  `["adb", "kill-server"]`; si no: `["adb", "reverse", "--remove", f"tcp:{port}"]`. Timeout 5 s; errores se ignoran.

Cambios en `main` (`vitrina/app.py`):
- Acepta `[]`, `["pair"]`, `["start"]`, `["stop"]`; si no, `Usage: python3 server.py [start | stop | pair]` y `2`.
- `["start"]` → `control.start([sys.executable, str(root / "server.py")], root, secrets_dir)`; `["stop"]` →
  `control.stop(secrets_dir)`. Los dos **antes** de leer `config.json`.
- Después de cargar el TLS y antes de abrir el puerto: si `control.running_pid(secrets_dir)` → `vitrina is already running.` y `1`.
- `own_adb = not adb.daemon_running()` antes de `_start_sources` (vitrina abrió el daemon ⇒ lo cierra al salir).
- `control.watch_sleep(on_long_sleep, stop)` donde `on_long_sleep` loguea
  `The Mac slept for over an hour. Stopping.` y llama `server.shutdown()`.
- Las líneas de arranque terminan en `To stop it: python3 server.py stop` (reemplaza `Press Ctrl+C to stop.`);
  **después** de imprimirlas, `lock = control.hold_lock(secrets_dir)` (así `start` ve el log completo).
- `serve_forever()`; `KeyboardInterrupt` se traga; en `finally`: `stop.set()`, `server.server_close()`,
  `adb.release(cfg.port, own_adb)`, cerrar `lock` si hay, log `Stopped.`.
- `server.py`: primera línea `#!/usr/bin/env python3`, modo `755` en git, y
  `signal.signal(signal.SIGTERM, signal.default_int_handler)` antes de llamar a `main` (SIGTERM = Ctrl+C).

- [ ] **Step 1: Tests que fallan.**
  - `test_adb.py`: `test_release_without_adb_or_daemon_runs_nothing` (dos casos: `which → None`;
    `running → False`) → sin llamadas; `test_release_kills_the_daemon_vitrina_opened` → última llamada
    `["adb", "kill-server"]`; `test_release_leaves_someone_elses_daemon` → `["adb", "reverse", "--remove", "tcp:8765"]`
    y ningún `kill-server`; `test_release_ignores_errors` (`TimeoutExpired`, `FileNotFoundError`) → no lanza.
  - `test_app.py`:
    - `test_unknown_argument` pasa a esperar `Usage: python3 server.py [start | stop | pair]`.
    - `test_stop_needs_no_config`: `main(["stop"], root, secrets) == 0`, salida `vitrina isn't running.`,
      `config.json` no se creó.
    - `test_start_launches_server_py`: con `vitrina.app.control.start` simulado (devuelve `0`) → llamado con
      `([sys.executable, str(root / "server.py")], root, secrets)`; `config.json` no se creó.
    - `test_refuses_a_second_server`: emparejado y con `hold_lock(secrets)` tomado → `run_main(puerto libre)`
      da `1`, `already running`, el puerto queda libre.
    - `test_long_sleep_stops_and_releases_everything`: emparejado, simulando `vitrina.app.control.watch_sleep`
      (guarda el callback), `vitrina.app.adb.daemon_running → False`, `vitrina.app.adb.ensure_reverse → False` y
      `vitrina.app.adb.release`; correr `main([], root, secrets)` en un hilo; esperar a que
      `running_pid(secrets) == os.getpid()`; llamar el callback → `main` devuelve `0`; salida contiene
      `slept for over an hour` y `Stopped.`; `release` llamado con `(puerto, True)`; el puerto queda libre;
      `running_pid(secrets) is None`.
    - `test_runs_through_a_link_from_another_folder`: enlace `<tmp>/vitrina → REPO/server.py`;
      `subprocess.run([str(link), "nope"], cwd=tmp)` → código `2` y el `Usage:` en la salida.
- [ ] **Step 2:** `/usr/bin/python3 -m unittest tests.test_adb tests.test_app -v` → FAIL.
- [ ] **Step 3:** Implementar en `adb.py`, `app.py` y `server.py` (`git update-index --chmod=+x server.py`).
- [ ] **Step 4:** `/usr/bin/python3 -m unittest -v` → todo PASS.
- [ ] **Step 5:** Commit `feat: stop cleanly on stop or a long sleep and run from any folder`.

### Task 3: README, enlace en la Mac y verificación real

**Files:** Modify `README.md`, `README.es.md`.

- [ ] **Step 1: README** (los dos idiomas): en la instalación, después de emparejar, una vez:
  `ln -s "$PWD/server.py" ~/.local/bin/vitrina` (si `~/.local/bin` no está en el PATH, `python3 server.py start`
  desde la carpeta hace lo mismo). Sección nueva "Arrancar y frenar": `vitrina start` (segundo plano, se puede
  cerrar la terminal), `vitrina stop` (lo encuentra donde esté; libera el puerto y cierra `adb` si lo abrió
  vitrina), `vitrina` en primer plano con Ctrl+C, el log en `~/Library/Application Support/vitrina/server.log`, y
  que si la Mac durmió más de 1 h el server se frena solo (por seguridad: la Mac pudo cambiar de red) y hay que
  correr `vitrina start`. Actualizar el bloque de salida de ejemplo (`To stop it: python3 server.py stop`).
- [ ] **Step 2: Enlace** (aprobado en el diseño): `ln -s <repo>/server.py ~/.local/bin/vitrina`.
- [ ] **Step 3: Verificar** con el Nokia por WiFi. Antes, frenar el server viejo que corre sin candado (el que
  arrancó esta sesión con el código anterior). Desde `~`:
  - `vitrina start` → muestra las direcciones y `Log: …`; `lsof -iTCP:8765 -sTCP:LISTEN` lo muestra; el celu se
    prende. Otro `vitrina start` → `vitrina is already running.`
  - `adb kill-server`, `vitrina stop`, `vitrina start` (ahora el daemon lo abre vitrina), `vitrina stop` →
    `Stopped.`; el puerto quedó libre; `pgrep -x adb` vacío; el celu se apaga solo (~1 min).
  - `vitrina` en primer plano en una terminal + `vitrina stop` desde otra → la primera imprime `Stopped.` y vuelve.
- [ ] **Step 4:** Commit `docs: start and stop vitrina from any terminal`.

### Task 4: ícono de la app

**Files:** Create `android/app/src/main/res/drawable/ic_launcher_foreground.xml`,
`android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml`; modify `AndroidManifest.xml`.

- [ ] **Step 1:** `ic_launcher_foreground.xml`: vector `108dp` × `108dp`, viewport `108`; un `<group>` con
  `scaleX/scaleY="2.25"`, `translateX/translateY="27"` y el mismo `pathData` y `fillType="evenOdd"` de
  `drawable/ic_notify.xml`, con `fillColor="@color/moon"` (así entra en la zona segura de 66 dp).
- [ ] **Step 2:** `ic_launcher.xml`: `<adaptive-icon>` con `<background android:drawable="@color/night"/>`,
  `<foreground>` y `<monochrome>` = `@drawable/ic_launcher_foreground`. En el manifest, `<application>` suma
  `android:icon="@mipmap/ic_launcher"` y `android:roundIcon="@mipmap/ic_launcher"`.
- [ ] **Step 3:** `source .tools/env.sh && cd android && ./gradlew --no-daemon testDebugUnitTest assembleDebug` →
  `BUILD SUCCESSFUL`.
- [ ] **Step 4: Verificar en el Nokia:** `adb install -r app/build/outputs/apk/debug/app-debug.apk` (conserva el
  emparejamiento); abrir la info de la app
  (`adb shell am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d package:io.github.nicob201.vitrina`) y
  sacar captura: se ve la pantallita clara sobre azul noche. Volver a vitrina (botón de inicio).
- [ ] **Step 5:** Commit `feat(android): launcher icon`.
