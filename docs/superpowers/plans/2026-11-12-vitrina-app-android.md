# vitrina — Plan 2: app Android y server cerrado

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** una app Android propia muestra vitrina a pantalla completa, prende y apaga la pantalla siguiendo a la Mac, y solo ella puede ver el server, que pasa a ser HTTPS con clave y se empareja por cable.

**Architecture:** el server Python suma TLS (certificado propio generado con `/usr/bin/openssl`) y una clave que exige en cada pedido; `python3 server.py pair` crea clave y certificado y se los pasa a la app por `adb`. La app (Kotlin, solo APIs del framework) guarda el emparejamiento cifrado con el Keystore, muestra la página en un WebView que reconoce el certificado por su huella, y un servicio en primer plano consulta la Mac para manejar la pantalla con una máquina de estados testeada.

**Tech Stack:** Python 3.9 stdlib (`ssl`, `hmac`, `secrets`), LibreSSL `openssl` de macOS, Kotlin + Android SDK (framework APIs) + Gradle, JUnit 4.

**Spec:** `docs/superpowers/specs/2026-11-12-vitrina-design.md` (§8 la app, §8b seguridad y emparejamiento). El Plan 1 (`docs/superpowers/plans/2026-11-12-vitrina-server-y-pagina.md`) ya está en `main`.

## Global Constraints

- **Solo macOS** en la PC. Python **3.9 stdlib**: correr con `/usr/bin/python3`; tests con `/usr/bin/python3 -m unittest -v`; `from __future__ import annotations` en cada módulo. Los tests pueden usar `/usr/bin/openssl`.
- **Secretos** en `~/Library/Application Support/vitrina/` (carpeta `0700`, archivos `0600`): `cert.pem`, `key.pem`, `secret`. Nunca en el repo, en `config.json` ni en la consola. **Los tests usan siempre una carpeta temporal**, nunca la real.
- **Huella** = SHA-256 de los bytes DER del certificado, en hexadecimal minúscula (64 caracteres), igual en Mac y Android.
- **Clave en los pedidos**: cookie `vitrina_key` o header `Authorization: Bearer <clave>`; comparación con `hmac.compare_digest`. Sin clave → `401` con cuerpo vacío.
- **App**: paquete `io.github.nicob201.vitrina`, nombre "vitrina", Kotlin, `minSdk 26`, `compileSdk`/`targetSdk` = la última plataforma estable instalada (anotarla), JVM 17. **Solo APIs del framework de Android: ninguna librería de terceros ni AndroidX** (menos superficie de ataque). Tests: solo `testImplementation("junit:junit:4.13.2")`. `android:allowBackup="false"` y `usesCleartextTraffic="false"`.
- **Emparejamiento**: componente `io.github.nicob201.vitrina/.PairActivity`, extras `key` (String), `fingerprint` (String), `port` (Int), `wifi_ip` (String); `exported="true"` con `android:permission="android.permission.DUMP"` (solo el shell de `adb` la tiene). La clave viaja a `adb` por **stdin**, nunca en la línea de comandos de la Mac.
- **WebView**: sin `addJavascriptInterface`, `allowFileAccess=false`, `allowContentAccess=false`, `mixedContentMode=NEVER_ALLOW`, navegación limitada a los orígenes emparejados, certificado aceptado solo por huella.
- Textos de la app en castellano e inglés (`res/values/` inglés, `res/values-es/` castellano).
- Código, comentarios y commits en inglés, commits convencionales **sin ningún trailer**.
- Rama `feat/android-app`. **Se mergea recién cuando pasa la Task 14**: el cierre del server y la app llegan juntos (spec §8b).
- Instalar herramientas en la Mac o la app en el celu son efectos fuera del repo: **pedir OK al usuario** antes de la primera vez.

## Review Focus

1. **La IP de la Mac cambia** (el router le da otra): por WiFi la app queda en "sin conexión" sin colgarse, y se arregla desde ajustes o emparejando de nuevo → verificación en Task 14.
2. **El celu se reinicia o Android mata la app**: al prender, vitrina vuelve sola (pantalla de inicio) y el servicio arranca → verificación en Task 14.
3. **La clave de la Mac cambió** (se emparejó otro celu o se borró): la app muestra "Volvé a emparejar", no una pantalla rota → verificación en Task 14 y manejo del `401` en Task 11.
4. **Alguien le habla HTTP común (o basura) al puerto HTTPS**: la conexión se cierra sin trazas en la consola ni bloquear a otros clientes → test en Task 5.
5. **La Mac se duerme a mitad de una consulta y se despierta**: la pantalla sigue a la Mac (se apaga y vuelve a prender) → verificación en Task 14.

## Estructura de archivos

```
vitrina/pairing.py           secretos (carpeta, certificado, clave, huella) y `pair` por adb
vitrina/handler.py           (mod) TLS por conexión + exigir la clave
vitrina/app.py               (mod) subcomando `pair`, no arrancar sin emparejar, URLs https
server.py                    (mod) pasa los argumentos
web/app.js                   (mod) sin pantalla completa ni wakeLock de Chrome
README.md / README.es.md     (mod) solo macOS, app y emparejamiento
tests/tls.py                 helper: certificado temporal con openssl
tests/test_pairing.py        (nuevo); tests/test_handler.py, tests/test_app.py (mod)
android/                     proyecto Gradle (Kotlin DSL) con wrapper
android/app/src/main/AndroidManifest.xml
android/app/src/main/java/io/github/nicob201/vitrina/
  ScreenStateMachine.kt      lógica pura: consultas → mantener / prender / recargar
  Pairing.kt                 lógica pura: validar emparejamiento, huella, orígenes
  SecureStore.kt             emparejamiento cifrado con el Keystore
  PinnedClient.kt            HTTPS con certificado fijado por huella + Bearer
  PairActivity.kt            recibe el emparejamiento desde adb
  MainActivity.kt            WebView kiosco, pantalla de inicio, pantallas de estado
  SettingsActivity.kt        cambiar la dirección WiFi, salir al inicio original
  PollService.kt             servicio en primer plano que consulta la Mac
  ScreenBus.kt               avisos del servicio a la actividad
android/app/src/main/res/values/strings.xml, values-es/strings.xml
android/app/src/test/java/io/github/nicob201/vitrina/ScreenStateMachineTest.kt, PairingTest.kt
```

---

### Task 1: Herramientas de Android en la Mac

**Files:** ninguno del repo.

- [ ] **Step 1:** Pedir OK al usuario para instalar con Homebrew: `openjdk@17`, `android-commandlinetools` (cask) y `gradle`. Sin OK, parar.
- [ ] **Step 2:** Instalar; con `sdkmanager` instalar `platform-tools`, la última `platforms;android-<N>` estable y su `build-tools`; aceptar licencias (`yes | sdkmanager --licenses`). Exportar `JAVA_HOME` (openjdk@17) y `ANDROID_HOME` solo en los comandos del proyecto (no tocar el perfil del usuario sin preguntar).
- [ ] **Step 3: Verify** `java -version` → 17; `sdkmanager --list_installed` → la plataforma `<N>`; `gradle --version` → anda. Anotar `<N>` y las versiones en el ledger.

---

### Task 2: Prueba descartable en el Nokia (spike)

**Files:** `spike/android-wake/` (ignorado por git; **no se commitea nada**).

Responde las tres incertidumbres de la spec §10 antes de construir la app. App mínima de prueba + un server Python de prueba en el puerto `8443` con certificado propio (openssl) que loguea el header `Cookie` de cada pedido.

- [ ] **Step 1: P1, prender la pantalla desde segundo plano.** Servicio en primer plano (`foregroundServiceType="specialUse"`) que consulta `https://<ip-mac>:8443/` cada 20 s; cuando pasa de 3 fallas seguidas a OK, prende la pantalla y trae la actividad al frente (`setShowWhenLocked(true)` + `setTurnScreenOn(true)`, más un wake lock `SCREEN_BRIGHT_WAKE_LOCK | ACQUIRE_CAUSES_WAKEUP` si hace falta). **Pasa si:** con la pantalla apagada por tiempo, cortar el server de prueba ~1 min y volver a arrancarlo prende la pantalla en ≤ 25 s.
- [ ] **Step 2: P2, solo `adb` abre la pantalla de emparejar.** Actividad con `android:permission="android.permission.DUMP"`. **Pasa si:** `adb shell am start -n <pkg>/.PairActivity --es key x` la abre; `adb shell dumpsys package <pkg>` muestra el permiso en esa actividad; y `adb shell dumpsys package android` (o `pm list permissions -f`) muestra que `DUMP` es `signature|privileged|development` (una app común no puede tenerlo).
- [ ] **Step 3: P3, WebView con certificado propio y cookie.** WebView que acepta el certificado solo si la huella coincide (`onReceivedSslError`), con cookie `vitrina_key=x; Secure; HttpOnly; SameSite=Strict; Path=/`. Página de prueba con un `fetch('/api')` y un `<img>`. **Pasa si:** el log del server muestra la cookie en la página, en el `fetch` y en la imagen; y con otro certificado no carga nada. Anotar cómo se obtiene el DER del certificado en Android 12 (`SslError.getCertificate()` → `x509Certificate` en API 29+; `SslCertificate.saveState(...).getByteArray("x509-certificate")` en 26–28).
- [ ] **Step 4:** Anotar en el ledger qué combinación funcionó en cada punto. **Si alguno falla, parar y llevárselo al usuario**: cambia el diseño.

---

### Task 3: Secretos en la Mac

**Files:**
- Create: `vitrina/pairing.py`, `tests/tls.py`
- Test: `tests/test_pairing.py`

**Interfaces:**
- Produces:
  - `SECRETS_DIR = Path.home() / "Library" / "Application Support" / "vitrina"`
  - `class PairingError(Exception)` — su mensaje se muestra tal cual.
  - `ensure_cert(folder: Path) -> tuple[Path, Path]` — crea `folder` (`0700`) si falta; si faltan `cert.pem`/`key.pem` corre `/usr/bin/openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 3650 -subj /CN=vitrina -keyout key.pem -out cert.pem` y deja ambos en `0600`; devuelve `(cert, key)`. Falla de openssl → `PairingError`.
  - `fingerprint(cert: Path) -> str` — `hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest()`.
  - `save_secret(folder: Path, secret: str) -> None` — escribe `folder/"secret"` en `0600` sin ventana de permisos abiertos (crear con `os.open(..., 0o600)` en un temporal y `os.replace`).
  - `read_secret(folder: Path) -> str | None`
  - `tests/tls.py`: `make_cert(folder: Path) -> tuple[Path, Path]` (usa `ensure_cert`) para los tests de las tasks 5 y 6.

- [ ] **Step 1: Write the failing tests**

```python
def test_cert_is_created_once_with_private_permissions(self):
    cert, key = ensure_cert(self.dir / "v")
    first = cert.read_bytes()
    self.assertEqual(ensure_cert(self.dir / "v"), (cert, key))
    self.assertEqual(cert.read_bytes(), first)                         # no se regenera
    self.assertEqual(stat.S_IMODE((self.dir / "v").stat().st_mode), 0o700)
    self.assertEqual(stat.S_IMODE(key.stat().st_mode), 0o600)

def test_fingerprint_matches_openssl(self):
    out = subprocess.run(["/usr/bin/openssl", "x509", "-in", cert, "-noout", "-fingerprint", "-sha256"], ...).stdout
    self.assertEqual(fingerprint(cert), out.split("=")[1].strip().replace(":", "").lower())
    self.assertRegex(fingerprint(cert), r"^[0-9a-f]{64}$")

def test_secret_round_trip_is_private(self):
    save_secret(folder, "abc"); save_secret(folder, "def")
    self.assertEqual(read_secret(folder), "def")
    self.assertEqual(stat.S_IMODE((folder / "secret").stat().st_mode), 0o600)

def test_missing_secret_is_none(self): ...
def test_openssl_failure_raises_pairing_error(self):   # mock.patch("vitrina.pairing.subprocess.run") → returncode 1
```

- [ ] **Step 2:** Run `/usr/bin/python3 -m unittest tests.test_pairing -v` → Expected: FAIL (`ModuleNotFoundError`).
- [ ] **Step 3: Implement** lo de arriba en `vitrina/pairing.py` y `tests/tls.py`.
- [ ] **Step 4:** Run → Expected: PASS.
- [ ] **Step 5: Commit** `feat: keep the server certificate and key in a private folder`

---

### Task 4: Emparejar por cable

**Files:**
- Modify: `vitrina/pairing.py`
- Test: `tests/test_pairing.py`

**Interfaces:**
- Consumes: `ensure_cert`, `fingerprint`, `save_secret` (T3).
- Produces:
  - `APP_ID = "io.github.nicob201.vitrina"`
  - `pair(folder: Path, port: int, wifi_ip: str | None, adb=subprocess.run, which=shutil.which) -> str` — devuelve la huella.

Orden (la clave vieja solo se reemplaza si la app confirmó):
1. Sin `adb` → `PairingError("adb not found. Install it with: brew install android-platform-tools")`.
2. `adb devices`: ningún `device` → `PairingError("Plug in the phone and allow USB debugging.")` (un `unauthorized` también).
3. `adb shell pm path io.github.nicob201.vitrina` vacío → `PairingError("Install the vitrina app on the phone first.")`.
4. `ensure_cert(folder)`; `secret = secrets.token_urlsafe(32)`.
5. `adb(["adb", "shell", SCRIPT], input=secret + "\n", capture_output=True, text=True, timeout=30)` con `SCRIPT = 'read -r k; am start -W -n io.github.nicob201.vitrina/.PairActivity --es key "$k" --es fingerprint <fp> --ei port <port> --es wifi_ip <ip o "">'`. OK = `returncode == 0` y `"Status: ok"` en la salida; si no → `PairingError("The phone didn't accept the pairing.")`.
6. Recién ahí `save_secret(folder, secret)`.

- [ ] **Step 1: Write the failing tests** (un `FakeAdb` que responde por comando y registra `cmd` e `input`; openssl real en carpeta temporal)

```python
def test_missing_adb_device_or_app_raise_and_keep_the_old_secret(self):
    save_secret(folder, "old")
    for fake in (no_adb, no_device, unauthorized_only, app_missing):
        with self.assertRaises(PairingError): pair(folder, 8765, "192.168.0.10", **fake)
        self.assertEqual(read_secret(folder), "old")

def test_secret_goes_through_stdin_never_argv(self):
    fp = pair(folder, 8765, "192.168.0.10", adb=fake, which=has_adb)
    secret = read_secret(folder)
    self.assertTrue(all(secret not in " ".join(c) for c in fake.calls))
    self.assertEqual(fake.inputs[-1], secret + "\n")
    self.assertIn(f"--es fingerprint {fp}", fake.calls[-1][2])
    self.assertIn("--ei port 8765", fake.calls[-1][2])

def test_each_pairing_rotates_the_secret(self): ...   # dos pair() OK → claves distintas
def test_failed_send_keeps_the_old_secret(self): ...   # am start sin "Status: ok" → PairingError, read_secret == "old"
def test_no_wifi_ip_sends_empty(self): ...             # wifi_ip=None → '--es wifi_ip ""'
```

- [ ] **Step 2:** Run `/usr/bin/python3 -m unittest tests.test_pairing -v` → Expected: FAIL.
- [ ] **Step 3: Implement** `pair`.
- [ ] **Step 4:** Run → Expected: PASS.
- [ ] **Step 5: Commit** `feat: pair the phone over USB without exposing the key`

---

### Task 5: Server con HTTPS y clave

**Files:**
- Modify: `vitrina/handler.py`
- Test: `tests/test_handler.py`

**Interfaces:**
- Consumes: `tests/tls.make_cert` (T3).
- Produces:
  - `tls_context(cert: Path, key: Path) -> ssl.SSLContext` — `PROTOCOL_TLS_SERVER`, `minimum_version = TLSv1_2`.
  - `make_server(host, port, web_dir, get_state, photo_path, tls: ssl.SSLContext, secret: str) -> ThreadingHTTPServer` — **ambos obligatorios**, no hay modo sin cifrar.

Reglas:
- El handshake TLS se hace **en el hilo de cada conexión** (`Handler.setup`: timeout primero, después `self.request = tls.wrap_socket(self.request, server_side=True)`), así un cliente lento no traba al resto.
- Un handshake fallido (HTTP común, basura) cierra en silencio: el `Server` ignora `ssl.SSLError` y `OSError` en `handle_error` (cualquier otra excepción se sigue mostrando).
- Orden en `do_GET`: `Host` → clave → rutas. Clave = cookie `vitrina_key` (`http.cookies.SimpleCookie`) o `Authorization: Bearer`; `hmac.compare_digest`; si no, `401` con cuerpo vacío.

- [ ] **Step 1: Write the failing tests.** Pasar todos los tests existentes de `HandlerTest` a HTTPS: `setUp` crea el certificado con `make_cert`, el server con `tls_context(...)` y `secret="s3cret"`; el helper `get()` usa `http.client.HTTPSConnection(..., context=ctx)` con `ctx = ssl.create_default_context(cafile=cert)`, `ctx.check_hostname = False`, y manda `Cookie: vitrina_key=s3cret` salvo que el test diga otra cosa. Nuevos:

```python
def test_no_key_gets_401_everywhere(self):
    for path in ("/", "/a.css", "/api/state", "/api/photo/0"):
        resp, body = self.get(path, key=None)
        self.assertEqual((resp.status, body), (401, b""))

def test_wrong_key_gets_401(self): ...                  # Cookie: vitrina_key=nope
def test_bearer_header_works(self): ...                 # sin cookie, Authorization: Bearer s3cret → 200
def test_tls_1_2_is_the_minimum(self):
    self.assertEqual(tls_context(cert, key).minimum_version, ssl.TLSVersion.TLSv1_2)

def test_plain_http_is_dropped_quietly(self):            # Review Focus 4
    with redirect_stderr(io.StringIO()) as err:
        with socket.create_connection(addr) as s:
            s.sendall(b"GET / HTTP/1.1\r\nHost: x\r\n\r\n"); s.settimeout(3)
            self.assertNotIn(b"HTTP/", s.recv(100))          # cierre o alerta TLS; nunca una respuesta HTTP
        resp, _ = self.get("/")                              # el server sigue atendiendo
    self.assertEqual(resp.status, 200)
    self.assertNotIn("Traceback", err.getvalue())
```

- [ ] **Step 2:** Run `/usr/bin/python3 -m unittest tests.test_handler -v` → Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** Run `/usr/bin/python3 -m unittest -v` → Expected: todo PASS (incluido `test_app`, que se ajusta en la Task 6; si falla acá solo por la firma de `make_server`, se arregla en la Task 6 y se anota).
- [ ] **Step 5: Commit** `feat: serve only over TLS and only to the paired key`

---

### Task 6: Arranque y subcomando `pair`

**Files:**
- Modify: `vitrina/app.py`, `server.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `SECRETS_DIR`, `pair`, `read_secret`, `PairingError` (T3–T4); `tls_context`, `make_server` (T5).
- Produces: `main(argv: list[str] | None = None, root: Path = ROOT, secrets_dir: Path = SECRETS_DIR) -> int`; `server.py` llama `main(sys.argv[1:])`.

Comportamiento:
- `argv == ["pair"]` → `pair(secrets_dir, cfg.port, net.lan_ip() if cfg.wifi else None)`; OK → `Paired. If the server is running, restart it.` + `WiFi:  https://<ip>:<port>`; `PairingError` → su mensaje, `return 1`.
- `argv == []` → si `read_secret(secrets_dir)` es `None` o falta `cert.pem`/`key.pem` → `Not paired yet. Plug in the phone and run: python3 server.py pair`, `return 1`, **antes de abrir el puerto**. Si no, arranca como hoy pero con `tls_context(...)` y la clave, e imprime las direcciones con `https://`.
- Cualquier otro argumento → `Usage: python3 server.py [pair]`, `return 2`.

- [ ] **Step 1: Write the failing tests** (`secrets_dir` temporal; helper que lo deja emparejado con `make_cert` + `save_secret`)

```python
def test_refuses_to_start_unpaired(self):
    code, out = self.run_main(port, paired=False)
    self.assertEqual(code, 1); self.assertIn("python3 server.py pair", out)
    # y el puerto quedó libre: se puede bindear
def test_pair_errors_are_messages(self):              # mock.patch("vitrina.app.pair", side_effect=PairingError("Plug in…"))
def test_pair_success_says_restart(self): ...         # mock pair → "fp"; out contiene "restart"
def test_unknown_argument(self): ...                  # main(["nope"]) == 2
```

  Ajustar los dos tests de puerto existentes para que corran emparejados.
- [ ] **Step 2:** Run `/usr/bin/python3 -m unittest tests.test_app -v` → Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** Run `/usr/bin/python3 -m unittest -v` → Expected: todo PASS.
- [ ] **Step 5: Commit** `feat: refuse to start unpaired and add the pair command`

---

### Task 7: Proyecto Android base

**Files:**
- Create: `android/settings.gradle.kts`, `android/build.gradle.kts`, `android/gradle.properties`, `android/app/build.gradle.kts`, `android/app/src/main/AndroidManifest.xml`, `android/app/src/main/java/io/github/nicob201/vitrina/MainActivity.kt` (vacía), `android/.gitignore` (`.gradle/`, `build/`, `local.properties`, `*.jks`, `*.keystore`), wrapper de Gradle (`gradle wrapper` con versión fija).

- [ ] **Step 1:** Proyecto Kotlin DSL con las Global Constraints (AGP y plugin de Kotlin: últimas estables compatibles con JDK 17; **versiones fijas**, anotarlas en el ledger). Sin dependencias salvo JUnit en tests. Manifest: `allowBackup="false"`, `usesCleartextTraffic="false"`, `MainActivity` con `screenOrientation="sensorLandscape"`.
- [ ] **Step 2: Verify** `cd android && ./gradlew --no-daemon testDebugUnitTest assembleDebug` → `BUILD SUCCESSFUL`.
- [ ] **Step 3: Verify en el Nokia** (con OK del usuario para instalar): `adb install -r app/build/outputs/apk/debug/app-debug.apk` → la app abre una pantalla vacía horizontal.
- [ ] **Step 4: Commit** `chore: add the Android project`

---

### Task 8: Máquina de estados de la pantalla

**Files:**
- Create: `android/app/src/main/java/io/github/nicob201/vitrina/ScreenStateMachine.kt`
- Test: `android/app/src/test/java/io/github/nicob201/vitrina/ScreenStateMachineTest.kt`

**Interfaces:**
- Produces:
  - `data class ScreenActions(val keepScreenOn: Boolean, val wake: Boolean, val reload: Boolean)`
  - `class ScreenStateMachine(private val failuresToRelease: Int = 3) { fun onPoll(ok: Boolean): ScreenActions }`

Arranca como "Mac ausente". Con consultas cada ~20 s, 3 fallas ≈ 1 min (spec §8). Prende solo en la transición "ausente → responde"; las acciones del usuario (botón de encendido) no entran: si apagó la pantalla con la Mac presente, no hay transición y no se prende.

- [ ] **Step 1: Write the failing tests**

```kotlin
@Test fun firstSuccessWakesAndReloads() = assertEquals(ScreenActions(true, true, true), m.onPoll(true))
@Test fun laterSuccessesOnlyKeepOn() { m.onPoll(true); assertEquals(ScreenActions(true, false, false), m.onPoll(true)) }
@Test fun twoFailuresStillKeepOn() { m.onPoll(true); m.onPoll(false); assertTrue(m.onPoll(false).keepScreenOn) }
@Test fun thirdFailureReleases() { m.onPoll(true); repeat(2) { m.onPoll(false) }; assertEquals(ScreenActions(false, false, false), m.onPoll(false)) }
@Test fun comingBackAfterReleaseWakesOnce() { /* true, 3×false, true → wake+reload; true → sin wake */ }
@Test fun aBlipDoesNotWake() { m.onPoll(true); m.onPoll(false); assertEquals(ScreenActions(true, false, false), m.onPoll(true)) }
```

- [ ] **Step 2:** Run `cd android && ./gradlew testDebugUnitTest --tests '*ScreenStateMachineTest'` → Expected: FAIL (no compila / no existe).
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** Run → Expected: PASS.
- [ ] **Step 5: Commit** `feat(android): screen state machine`

---

### Task 9: Lógica de emparejamiento

**Files:**
- Create: `android/app/src/main/java/io/github/nicob201/vitrina/Pairing.kt`
- Test: `android/app/src/test/java/io/github/nicob201/vitrina/PairingTest.kt`

**Interfaces:**
- Produces:
  - `data class PairingInfo(val key: String, val fingerprint: String, val port: Int, val wifiIp: String)` — `toString()` **no** incluye la clave.
  - `object Pairing`:
    - `fun parse(key: String?, fingerprint: String?, port: Int, wifiIp: String?): PairingInfo?` — clave: ≥ 32 caracteres de `[A-Za-z0-9_-]`; huella: `^[0-9a-f]{64}$`; puerto 1–65535; `wifiIp`: vacío o IPv4 literal (cuatro números 0–255, sin resolver nombres). Inválido → `null`.
    - `fun isIpv4(s: String): Boolean`
    - `fun fingerprintOf(certDer: ByteArray): String` — SHA-256 en hex minúscula.
    - `fun matches(certDer: ByteArray, expected: String): Boolean` — comparación en tiempo constante (`MessageDigest.isEqual`).
    - `fun origins(info: PairingInfo): List<String>` — `["https://localhost:P", "https://<ip>:P"]` (sin la segunda si `wifiIp` está vacío).

- [ ] **Step 1: Write the failing tests**

```kotlin
@Test fun validPairing() = assertNotNull(Pairing.parse(KEY, FP, 8765, "192.168.0.10"))
@Test fun invalidFieldsAreRejected() {   // cada caso por separado → null
  // clave corta, clave con espacios, huella en mayúsculas o de 63, puerto 0 y 70000, ip "192.168.0.256", "mac.local"
}
@Test fun emptyWifiIpIsAllowed() = assertEquals(listOf("https://localhost:8765"), Pairing.origins(Pairing.parse(KEY, FP, 8765, "")!!))
@Test fun fingerprintOfKnownBytes() = assertEquals("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", Pairing.fingerprintOf("abc".toByteArray()))
@Test fun matchesOnlyTheSameCert() { assertTrue(Pairing.matches("abc".toByteArray(), ABC_FP)); assertFalse(Pairing.matches("abd".toByteArray(), ABC_FP)) }
@Test fun keyIsNotInToString() = assertFalse(Pairing.parse(KEY, FP, 8765, "")!!.toString().contains(KEY))
```

- [ ] **Step 2:** Run `./gradlew testDebugUnitTest --tests '*PairingTest'` → Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** Run `./gradlew testDebugUnitTest` → Expected: PASS (las dos clases).
- [ ] **Step 5: Commit** `feat(android): pairing validation and certificate fingerprints`

---

### Task 10: Guardado seguro y pantalla de emparejar

**Files:**
- Create: `SecureStore.kt`, `PairActivity.kt`, `res/values/strings.xml`, `res/values-es/strings.xml`
- Modify: `AndroidManifest.xml`

**Interfaces:**
- Consumes: `PairingInfo`, `Pairing.parse` (T9).
- Produces: `class SecureStore(context: Context) { fun save(info: PairingInfo); fun load(): PairingInfo?; fun clear() }`.

- [ ] **Step 1: `SecureStore`:** clave AES-256-GCM en `AndroidKeyStore` (alias `vitrina-pairing`); `PairingInfo` serializado con `org.json.JSONObject`, cifrado, y guardado (IV + texto cifrado en Base64) en `SharedPreferences` privadas. `load()` devuelve `null` ante cualquier problema (datos corruptos, clave del Keystore perdida).
- [ ] **Step 2: `PairActivity`:** lee los extras → `Pairing.parse` → `SecureStore.save` → muestra "Emparejado" ~3 s y abre `MainActivity` limpiando la pila. Inválido → "Datos de emparejamiento inválidos" y no toca lo guardado. Manifest: `exported="true"`, `android:permission="android.permission.DUMP"`, `excludeFromRecents="true"`, sin `intent-filter`.
- [ ] **Step 3: Verify en el Nokia** (instalar con `adb install -r`):
  - `/usr/bin/python3 server.py pair` (desde esta rama) → el celu muestra "Emparejado" y la consola `Paired…`.
  - `adb shell dumpsys package io.github.nicob201.vitrina | grep -A3 PairActivity` → aparece `android.permission.DUMP`.
  - `adb shell am start -n io.github.nicob201.vitrina/.PairActivity --es key corta` → "inválidos"; un `pair` posterior sigue andando.
- [ ] **Step 4: Commit** `feat(android): store the pairing encrypted and accept it only from adb`

---

### Task 11: Pantalla principal (kiosco)

**Files:**
- Modify: `MainActivity.kt`, `AndroidManifest.xml`, strings
- Create: `SettingsActivity.kt`, `PinnedClient.kt`

**Interfaces:**
- Consumes: `SecureStore` (T10), `Pairing` (T9).
- Produces: `object PinnedClient { fun get(origin: String, path: String, info: PairingInfo, timeoutMs: Int = 5000): Int }` — código HTTP o `-1`; `HttpsURLConnection` con un `TrustManager` que acepta solo el certificado cuya huella coincide (`Pairing.matches`) y un `HostnameVerifier` que acepta cualquier nombre (la huella reemplaza el chequeo de nombre); manda `Authorization: Bearer`.

- [ ] **Step 1: Pantalla de inicio y kiosco.** `intent-filter` con `MAIN` + `HOME` + `DEFAULT` + `LAUNCHER`; `launchMode="singleTask"`; pantalla completa inmersiva (`WindowInsetsController` en API 30+, flags de `systemUiVisibility` en 26–29); horizontal.
- [ ] **Step 2: Estados.** Sin emparejar → texto "Enchufá el celu a la Mac y corré: python3 server.py pair". Emparejada → en un hilo de fondo, `PinnedClient.get(origin, "/api/state", info)` para cada origen de `Pairing.origins` y carga el primero que dé `200` (localhost primero). `401` → pantalla "Volvé a emparejar" (sin borrar lo guardado). Nadie responde → carga igual el origen WiFi (la página muestra "sin conexión" y se recupera sola).
- [ ] **Step 3: WebView cerrado** según las Global Constraints. `onReceivedSslError`: `Pairing.matches(der, info.fingerprint)` → `proceed()`, si no `cancel()` y pantalla "No es tu Mac" (el DER se obtiene como se anotó en la Task 2). `shouldOverrideUrlLoading` → bloquea todo origen que no esté en `Pairing.origins(info)`. Cookie `vitrina_key=<clave>; Secure; HttpOnly; SameSite=Strict; Path=/` para cada origen con `CookieManager` + `flush()` antes de cargar.
- [ ] **Step 4: Ajustes.** Mantener apretado ≥ 3 s sin mover el dedo → `SettingsActivity` (los toques cortos siguen llegando a la página: tocar = siguiente panel). Ajustes: dirección WiFi (validada con `Pairing.isIpv4`, se guarda en `SecureStore`), "Salir" (abre la primera actividad `HOME` que no sea vitrina) y "Volver".
- [ ] **Step 5: Verify en el Nokia:**
  - Emparejada y con el server corriendo → la página se ve por WiFi, tocar cambia de panel, mantener 3 s abre ajustes.
  - "No es tu Mac": parar vitrina y correr `openssl s_server -accept 8765 -cert otro.pem -key otra.pem -www` con un certificado nuevo → la app muestra "No es tu Mac" y no carga nada.
  - Volver a arrancar vitrina → anda.
- [ ] **Step 6: Commit** `feat(android): kiosk WebView pinned to the paired Mac`

---

### Task 12: Servicio que sigue a la Mac

**Files:**
- Create: `PollService.kt`, `ScreenBus.kt`
- Modify: `MainActivity.kt`, `AndroidManifest.xml`, strings

**Interfaces:**
- Consumes: `ScreenStateMachine` (T8), `PinnedClient` (T11), `SecureStore` (T10).
- Produces: `object ScreenBus { @Volatile var listener: ((ScreenActions) -> Unit)?; var needsRepair: Boolean }` (mismo proceso; `MainActivity` se suscribe en `onResume` y se borra en `onPause`).

- [ ] **Step 1: `PollService`:** servicio en primer plano `specialUse` (con la `property` `android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE`), permisos `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_SPECIAL_USE`, `WAKE_LOCK`, `POST_NOTIFICATIONS`. Notificación de baja importancia "Esperando a la Mac" / "Waiting for the Mac". Cada 20 s: `PinnedClient.get` sobre los orígenes; `200` → `onPoll(true)`; `401` → `ScreenBus.needsRepair = true` y `onPoll(false)`; otro → `onPoll(false)`. Lo arranca `MainActivity` al estar emparejada.
- [ ] **Step 2: Aplicar las acciones:** `keepScreenOn` → `FLAG_KEEP_SCREEN_ON` en la ventana; `wake` → traer `MainActivity` al frente y prender la pantalla **con la combinación que funcionó en la Task 2**; `reload` → `WebView.reload()`.
- [ ] **Step 3: Guía del primer arranque** (después de emparejar, hasta que esté todo o el usuario toque "Listo"): elegir vitrina como inicio (`Settings.ACTION_HOME_SETTINGS`), tiempo de pantalla ≤ 1 min (lee `Settings.System.SCREEN_OFF_TIMEOUT`; botón a `Settings.ACTION_DISPLAY_SETTINGS`), permiso de notificaciones en Android 13+.
- [ ] **Step 4: Verify en el Nokia:**
  - Server corriendo → la pantalla no se apaga.
  - Ctrl+C en el server → en ≤ ~2 min la pantalla se apaga.
  - Volver a correrlo → en ≤ ~25 s se prende y la página se recarga.
  - Con el server corriendo, apagar con el botón → queda apagada; cortar el server ≥ 1 min y volver a correrlo → se prende.
- [ ] **Step 5: Commit** `feat(android): follow the Mac with a foreground poll`

---

### Task 13: Página y README

**Files:**
- Modify: `web/app.js`, `README.md`, `README.es.md`

- [ ] **Step 1:** En `web/app.js`, el toque solo pasa al panel siguiente: borrar `requestFullscreen` y `wakeLock` (la app ya está a pantalla completa y maneja la pantalla).
- [ ] **Step 2: README** (los dos): requisitos **solo macOS**; instalar la app (por ahora desde el código: `cd android && ./gradlew installDebug` con el celu enchufado; los APK en Releases llegan cuando el repo sea público); emparejar con `python3 server.py pair`; seguridad (HTTPS con certificado propio, clave, carpeta de secretos, emparejar de nuevo cambia la clave, `"wifi": false`); la página ya no se abre en Chrome. Sacar lo de Windows y lo de "Pantalla activa" de Chrome.
- [ ] **Step 3: Verify** `grep -n -i "windows\|chrome" README.md README.es.md` → solo la línea que dice que la página no se abre en navegadores; `/usr/bin/python3 -m unittest` → OK.
- [ ] **Step 4: Commit** `docs: macOS-only setup with the app and pairing`

---

### Task 14: De punta a punta en el Nokia

**Files:** ninguno (salvo correcciones que aparezcan, cada una con su test si es lógica).

- [ ] **Step 1: Emparejar desde cero:** borrar la carpeta de secretos de prueba no hace falta; correr `python3 server.py` sin emparejar → mensaje y sale 1. `python3 server.py pair` → "Emparejado". `python3 server.py` → anda.
- [ ] **Step 2: WiFi y cable:** desenchufado → la esquina dice `WiFi`; enchufado → `USB` (origen `localhost` vía `adb reverse`).
- [ ] **Step 3: La Mac se duerme y se despierta** (cerrar la tapa ≥ 2 min y abrirla) → la pantalla del celu se apaga y vuelve a prender sola (Review Focus 5).
- [ ] **Step 4: Clave cambiada** (Review Focus 3): con el server parado, `python3 -c` que reemplaza `secret` con `save_secret(SECRETS_DIR, secrets.token_urlsafe(32))`; arrancar → la app muestra "Volvé a emparejar". `pair` + reiniciar → vuelve.
- [ ] **Step 5: IP distinta** (Review Focus 1): en ajustes poner una IP equivocada → "sin conexión" sin colgarse; corregirla → vuelve.
- [ ] **Step 6: Reinicio del celu** (Review Focus 2): apagar y prender → vitrina aparece sola como inicio y el servicio corre (notificación visible).
- [ ] **Step 7:** Si todo pasa, la rama está lista para el merge (spec §8b: server cerrado y app llegan juntos).
