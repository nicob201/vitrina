# vitrina — diseño de la v1

> Estado: **aprobado** · 2026-11-12 · revisión "seguridad y solo macOS" (§8b) aprobada el mismo día
> La maqueta original (`spike/preview.html`) y las notas de arranque quedaron fuera del repo; lo que importa de ellas está acá.

## 1. Qué es y por qué

Convertir un celular Android viejo en una mini pantalla de escritorio que va rotando paneles: la hora con el
clima, la actividad de GitHub, el uso de Claude y fotos. Los datos los junta la PC; el celu los muestra.

Es un proyecto personal, open source y gratis para la comunidad (repo `vitrina` en GitHub, licencia MIT), y
también un proyecto para aprender. **La estética es prioridad**: todo lo que muestra el celular tiene que
verse bien, incluidos los estados raros (cargando, sin datos, sin conexión).

El celu de referencia es un **Nokia 2.4** (Android 12, LCD 720×1600, Helio P22, 3 GB RAM), usado ~8 h por día
enchufado, horizontal, y apagado el resto del día.

## 2. Objetivos, no-objetivos y anti-objetivos

**Objetivos de la v1**

- Paneles: **hora + fecha + clima**, **GitHub**, **Claude** (opcional) y **fotos** de una carpeta.
- Funciona **por WiFi y por cable**, y la mayor parte del tiempo se va a usar por WiFi.
- **La pantalla del celu sigue a la PC**: PC despierta con el server corriendo → pantalla prendida; PC
  dormida, apagada o server cortado → pantalla apagada; vuelve la PC → se prende sola.
- Se puede **apagar a mano** con el botón de encendido del celu, y la PC no lo vuelve a prender mientras siga ahí.
- Textos en **castellano e inglés**, según el idioma del celu, con opción para forzarlo.
- PC con **macOS** (Windows quedó afuera por ahora, 2026-11-12). Server en **Python sin dependencias**
  (`git clone` + `python3 server.py`).
- **Cerrado**: solo la app emparejada ve algo; todo viaja cifrado (HTTPS) y con clave (§8b).

**No-objetivos (después de la v1)**

- Panel de Spotify / "lo que está sonando". Pista: en macOS, AppleScript sobre Spotify/Música; en Windows, Python
  puede pedirle a PowerShell la API de medios de Windows (cualquier reproductor, sin login ni dependencias), sin verificar.
- Autoarranque del server en la PC (launchd / Programador de tareas).
- Que el celu se apague cuando la PC solo apaga su monitor pero sigue despierta.
- Web alojada en la nube, clientes iOS, varios celulares, pantalla de configuración (se edita `config.json`).

**Anti-objetivos (aunque ande, sería un fracaso)**

- Que el token de Claude salga de la PC. Al celu solo van porcentajes y horarios.
- Que el server renueve el token de Claude (puede cerrarle la sesión a Claude Code).
- Que instalar el server pida `pip install` o cualquier dependencia.
- Pantallas feas o "de error": un panel sin datos no aparece; nunca se ve un error técnico en el celu.
- Que el server sea accesible desde internet. Solo red local.
- Que algo (página, datos, fotos) se vea sin la clave, o que viaje sin cifrar.
- Que el server arranque sin que el usuario lo corra. Si algún día hay autoarranque, lo activa el usuario.

## 3. Restricciones

- **Viewport del Nokia** horizontal a pantalla completa: ~**890 × 396 px CSS**, dpr 1,75. CPU lenta.
- **Python 3.9+**: es el que trae macOS con las Command Line Tools. Solo biblioteca estándar. Su `ssl` usa
  LibreSSL 2.8.3: TLS 1.2 (sin 1.3), suficiente para Android 8+.
- **`/usr/bin/openssl`** (LibreSSL, viene con macOS) genera el certificado propio.
- **Las fuentes van dentro del repo** (Big Shoulders Display + Atkinson Hyperlegible Next, ambas OFL, con su
  licencia). El celu no necesita internet.
- **Endpoint de Claude no documentado** (`api/oauth/usage`): puede cambiar sin aviso. Si se rompe, desaparece
  el panel y nada más.
- **Open-Meteo** es gratis para uso no comercial y pide atribución ("Weather data by Open-Meteo.com").

## 4. Enfoques considerados

| Decisión | Opciones | Elegida y por qué |
|---|---|---|
| Dónde corre | **(a) server local en la PC**; (b) web en Vercel/Cloudflare | **(a)**. El token de Claude y las fotos viven en la PC, y una web en la nube no puede saber si la PC está dormida. |
| Reparto PC / celu | **(a) la PC calcula todo, el celu pinta**; (b) la PC manda datos crudos y el celu calcula; (c) la PC arma el HTML y el celu recarga | **(a)**. Toda la lógica queda en Python y se testea con `unittest`, sin Node. El Nokia trabaja menos. (c) da parpadeos, pierde los fundidos y el reloj sin PC. |
| Apagar/prender la pantalla por WiFi | **(a) app Android propia**; (b) Fully Kiosk PLUS (US$11/celu); (c) `adb` inalámbrico | **(a)**. Gratis para la comunidad, sin marca de agua, y sirve para aprender Android. (b) obliga a cada usuario a pagar. (c) Android desactiva la depuración inalámbrica al reiniciar, y el celu se apaga todos los días. |
| Cómo llegan los datos al celu | **(a) el celu pregunta cada ~30 s**; (b) conexión abierta (SSE) | **(a)**. Más simple y aguanta mejor los cortes de WiFi; "sin conexión" = falló la pregunta. |
| Plataforma de la PC | (a) macOS y Windows; **(b) solo macOS** | **(b)** (decisión del usuario, 2026-11-12): desarrollo más fluido y macOS trae `openssl`. |
| Qué tan cerrado | (a) clave; **(b) clave + HTTPS** | **(b)**: nada se lee aunque alguien capture el tráfico de la red. Cuesta generar un certificado propio y que la app lo reconozca. |
| Cómo la app recibe la clave y reconoce el certificado | **(a) emparejar por cable una vez**; (b) código en pantalla; (c) QR | **(a)**: la confianza se arma por el cable, nadie se mete en el medio y no se tipea nada. (b) es vulnerable en ese primer momento si no se compara bien. (c) Python solo no genera QR. |
| Qué pasa al prender el celu | **(a) vitrina es la pantalla de inicio**; (b) se abre sola con el permiso "mostrar sobre otras apps"; (c) se abre a mano | **(a)**. Es lo que hacen las apps tipo kiosco y lo más confiable; el celu queda dedicado. (b) Android 10+ lo traba y es frágil. (c) habría que hacerlo todos los días. |

## 5. Arquitectura

Tres piezas:

```
PC (macOS)                                        Celu (Android)
┌──────────────────────────────────────┐          ┌──────────────────────────────┐
│ server.py  (Python, solo stdlib)     │  WiFi o  │ App "vitrina" (Kotlin)       │
│  ├─ fuentes: GitHub, Claude, clima,  │  cable   │  ├─ WebView a pantalla       │
│  │   fotos  (hilos con su intervalo) │◄────────►│  │   completa con la página  │
│  ├─ estado calculado en memoria      │  HTTPS   │  └─ control de pantalla:     │
│  ├─ GET /api/state  (JSON listo)     │          │      prende / deja apagar    │
│  ├─ GET /api/photo/<id>              │          │      según responda el server│
│  └─ sirve la página (web/)           │          └──────────────────────────────┘
│ adb reverse si hay cable             │
└──────────────────────────────────────┘
```

La página se ve **solo desde la app emparejada**: con certificado propio y clave, un navegador común no entra
(§8b). Los tests y las capturas de desarrollo usan la clave.

**Estructura del repo (propuesta):**

```
server.py               # punto de entrada: python server.py
vitrina/                # paquete Python: config, fuentes, estado, http
web/                    # index.html, styles.css, app.js, fonts/, icons
android/                # proyecto de la app (Gradle + Kotlin)
tests/                  # unittest + fixtures guardados
config.example.json
README.md / README.es.md / LICENSE
```

El código, los comentarios y los commits van en inglés (proyecto open source); los README en los dos idiomas.

## 6. El server

**Arranque.** `python server.py`:

1. Lee `config.json`. Si no existe, lo crea copiando `config.example.json`, avisa qué completar y arranca
   igual con lo que haya (los paneles sin datos no aparecen).
2. Escucha en el puerto de la config (por defecto `8765`) en todas las interfaces, para el WiFi. Si
   `"wifi": false`, solo en `127.0.0.1` (modo solo cable).
3. Imprime las direcciones para el celu (la IP de la PC en la red local y `localhost`).
4. Si encuentra `adb` y hay un celu conectado, corre `adb reverse tcp:PUERTO tcp:PUERTO`. Lo revisa cada
   ~10 s, porque el cable se enchufa después o el túnel se cae cuando la PC se duerme.
5. Si hay ciudad configurada, la busca una vez en Open-Meteo e imprime qué lugar encontró
   ("Córdoba, Córdoba, Argentina"), para que se note si eligió otra.

**Fuentes.** Cada una corre en su hilo, con su intervalo, y guarda el último resultado bueno. Si una falla,
se registra en consola, se queda el dato anterior y el server sigue. Ninguna fuente tira el server.

| Fuente | De dónde | Cada | Qué calcula el server |
|---|---|---|---|
| GitHub | HTML público de `github.com/users/<user>/contributions` (sin token) | 5 min | Las 53 semanas con el nivel 0–4 de cada día (el que trae GitHub), total del año, racha de días seguidos, contribuciones de hoy, etiquetas de meses |
| Claude | `GET https://api.anthropic.com/api/oauth/usage`, headers `Authorization: Bearer <token>` y `anthropic-beta: oauth-2025-04-20` | 5 min | Sesión (`five_hour`) y semana (`seven_day`): % de uso y hora de reinicio. Semana: % de la semana transcurrida (marca de ritmo). Si ya pasó `resets_at`, 0 % sin consultar |
| Clima | Open-Meteo: geocoding una vez, después `forecast` con `current` (temperatura, `weather_code`, `is_day`) y `daily` (máx/mín) | 15 min | Temperatura actual, máx y mín del día, condición (código WMO → una de ~8 categorías con palabra en cada idioma e ícono), día/noche |
| Fotos | Carpeta de la config (jpg, jpeg, png, webp) | 1 min | Lista en orden mezclado; pasan todas antes de repetir |

**Token de Claude** (solo lectura, nunca se renueva):
- macOS: Keychain, servicio `Claude Code-credentials` vía `security find-generic-password -w`. macOS puede
  pedir permiso la primera vez; el README lo explica.
- Si no está en el Keychain: `~/.claude/.credentials.json`.
- El panel es **opt-in** (`"claude": true` en la config). Si el token venció o falta, se muestra el último dato
  y, si ya pasó la hora de reinicio, 0 %.

**Racha de GitHub:** cuenta días seguidos con contribuciones hacia atrás desde hoy; si hoy todavía va 0, arranca
desde ayer (el día no terminó).

**Idioma:** el server elige `es` o `en` con `"language"` de la config (`"auto"`, `"es"`, `"en"`). En `"auto"`
usa el header `Accept-Language` que manda el celu. Cualquier otro idioma → inglés.

**Endpoints** (solo lectura, no hay nada que escriba):

- `GET /` y archivos de `web/`.
- `GET /api/state` → todo listo para pintar (forma orientativa, los nombres los define el que construye):

```json
{
  "lang": "es",
  "link": "wifi",
  "seconds_per_panel": 15,
  "strings": { "github_title": "Actividad en GitHub", "...": "..." },
  "panels": ["clock", "github", "claude", "photos"],
  "clock":  { "weather": { "temp": 18, "max": 23, "min": 12, "condition": "cloudy", "label": "nublado", "is_day": true } },
  "github": { "total": 1234, "streak": 12, "today": 3, "weeks": [[0,1,4,2,0,0,1], "..."], "months": [{"week": 0, "label": "nov"}] },
  "claude": { "session": { "pct": 42, "resets_at": "..." }, "week": { "pct": 67, "resets_at": "...", "elapsed_pct": 55 } },
  "photos": ["/api/photo/3", "/api/photo/0", "..."]
}
```

  `link` es `"usb"` si el pedido viene de `127.0.0.1` (cable vía `adb reverse`) y `"wifi"` si no.
  Un panel sin datos no está en `panels`.
- `GET /api/photo/<id>` → solo archivos de la lista de la carpeta configurada, por índice. Nada de rutas que
  vengan del celu (sin path traversal).

**Config (`config.example.json`):**

```json
{
  "port": 8765,
  "wifi": true,
  "language": "auto",
  "seconds_per_panel": 15,
  "github_user": "",
  "claude": false,
  "city": "",
  "country": "",
  "units": "celsius",
  "photos_dir": ""
}
```

`country` es opcional (código ISO, ej. `"AR"`) y sirve para desambiguar la ciudad.

## 7. La página (web/)

HTML + CSS + JS sin build, con la dirección visual de la maqueta (ver "Dirección visual" abajo):
paleta "escritorio de noche", fuentes locales, un panel a pantalla completa por vez con fundido, barra de
progreso abajo, `prefers-reduced-motion` respetado, zoom bloqueado.

- **Rotación:** solo los paneles de `panels`, en orden fijo (hora, GitHub, Claude, fotos), `seconds_per_panel`
  cada uno. Tocar la pantalla = siguiente.
- **Esquina fija:** reloj chico + estado de la conexión (`USB` / `WiFi` / "sin conexión"). Se oculta en el
  panel de la hora.
- **Hora:** como la maqueta (hora enorme abajo a la izquierda, día y fecha a la derecha), más el **clima arriba
  a la derecha**, donde la esquina está oculta:

```
┌──────────────────────────────────────────────┐
│                                   ☁  18°      │
│                         nublado · 23° / 12°   │
│                                               │
│  21:47                                jueves  │
│  (enorme)                    12 de noviembre  │
│  ━━━━━━  ──────  ──────  ──────               │
└──────────────────────────────────────────────┘
```

  Íconos de clima propios en SVG, en el estilo de la maqueta (trazo, colores `--moon` / `--sun`), con
  variante de noche para despejado y parcialmente nublado. Sin clima, el panel queda como la maqueta.
- **GitHub y Claude:** como la maqueta. El "se reinicia en 2 h 13 min" lo actualiza el celu a partir de
  `resets_at`, para que siga bien aunque se corte la PC.
- **Fotos:** una foto por vuelta. Horizontales a pantalla completa (`cover`); verticales enteras (`contain`)
  sobre una copia desenfocada de la misma foto. La siguiente se precarga antes de mostrarla.
- **Datos:** pide `/api/state` cada ~30 s. Si falla: "sin conexión" en la esquina, quedan los últimos datos y
  el reloj sigue. Antes del primer dato se muestra solo el panel de la hora.
- **Fechas y números** con `Intl` en el idioma de `lang`.

### Dirección visual

La maqueta con datos falsos se aprobó; **el panel de Claude es el favorito**: mantener ese estilo.

Concepto: **"escritorio de noche"**: fondo índigo profundo y texto claro. Dos paneles llevan los colores de su
marca (pedido del usuario, 2026-11-12): GitHub con sus verdes y Claude con su paleta cálida.

| Token | Valor | Uso |
|---|---|---|
| `--night` | `#1A2142` | Fondo. Índigo profundo: en LCD el negro se ve gris, un color profundo se ve intencional |
| `--dusk` | `#262F59` | Celdas vacías, fondo de las barras |
| `--haze` | `#3A4475` | Líneas, progreso inactivo, los dos puntos del reloj |
| `--mist` | `#9AA1C7` | Texto secundario |
| `--moon` | `#F1F2FA` | Texto principal, relleno de las barras |
| `--leaf-1..4` | `#0E4429` `#006D32` `#26A641` `#39D353` | Verdes de GitHub (modo oscuro), de apagado a brillante. Los días sin actividad quedan en `--dusk` |
| `--claude` | `#D97757` | Naranja de Claude: números y barras del panel de Claude |
| `--claude-bg` / `--claude-text` / `--claude-mist` / `--claude-track` | `#262624` `#FAF9F5` `#B7B5A9` `#3D3D3A` | Panel de Claude: fondo cálido, texto, texto secundario, parte vacía de las barras |
| `--sun` | `#D99A33` | Sol y rayo de los íconos del clima |

- Tipografías: **Big Shoulders Display** (números grandes; angosta y alta, entra bien en pantalla ancha y baja)
  + **Atkinson Hyperlegible Next** (textos; diseñada para leerse de un vistazo). Ambas OFL → van **dentro del repo** (sin depender de internet), no desde Google Fonts.
- Claude: barra semanal con una **marca de ritmo** (% de la semana transcurrida). Si la barra la pasa,
  vas por encima del ritmo. La marca va en marfil sobre el naranja.
- Sin mayúsculas sostenidas en labels, sin decoración innecesaria; el movimiento es solo el fundido entre
  paneles y la barra de progreso (respetando `prefers-reduced-motion`).
- Viewport real del Nokia en horizontal a pantalla completa: **~890 × 396 px CSS** (dpr 1,75).
- Bloquear el zoom (`user-scalable=no`): al rotar, Chrome quedó con zoom 1,7x y rompía el layout.

## 8. La app Android

App mínima en Kotlin que reemplaza al navegador. Se distribuye como APK en GitHub Releases; quien la usa no
instala herramientas de desarrollo.

- **Pantalla principal:** WebView a pantalla completa (modo inmersivo, horizontal fija) con la página del server.
- **Primera vez:** sin emparejar, muestra cómo hacerlo ("Enchufá el celu a la Mac y corré `python3 server.py pair`").
  Ya emparejada, prueba primero `https://localhost:<puerto>` (cable) y si no responde la dirección WiFi que
  recibió al emparejar.
- **Ajustes:** mantener apretado ~3 s → pantalla para cambiar la dirección WiFi o salir.
- **Control de pantalla** (la lógica, como máquina de estados testeable aparte):
  - Server responde → mantiene la pantalla prendida (`FLAG_KEEP_SCREEN_ON`).
  - Server sin responder ~1 min seguido → suelta la pantalla y Android la apaga con su tiempo de espera.
    El primer arranque guía para dejar ese tiempo en 1 min. Meta: pantalla apagada ≤ ~2 min después de que la
    PC se duerme.
  - Con la pantalla apagada, un servicio en primer plano sigue preguntando cada ~20 s (el celu está cargando,
    así que Android no lo frena). Android obliga a mostrar una notificación fija mientras corre.
  - **Prende la pantalla solo en la transición "server caído → server responde"**. Si el usuario la apagó con
    el botón y la PC sigue ahí, no la vuelve a prender.
  - En esa misma transición recarga la página, así toma cualquier cambio del server.
- **Pantalla de inicio:** la app se declara como pantalla de inicio de Android (categoría `HOME`) y el primer
  arranque guía para elegirla como predeterminada. Así se abre sola al prender el celu y el botón de inicio vuelve
  a vitrina. "Salir" (desde ajustes) abre el inicio original de Android.
- **minSdk 26** (Android 8): cubre la mayoría de los celus viejos que siguen andando.
- **WebView cerrado** (revisión de seguridad 2026-11-12): sin
  `addJavascriptInterface`, sin acceso a archivos (`allowFileAccess` y `allowContentAccess` en `false`), y la
  navegación queda limitada a la dirección del server configurada; cualquier otro enlace se ignora.

## 8b. Seguridad y emparejamiento (revisión 2026-11-12)

Pedido del usuario: "que sea cerrado, que no se exponga nada", y priorizar siempre la seguridad.

**Modelo.** Solo la app emparejada ve algo. Todo viaja por HTTPS con un certificado propio que la app reconoce por
su huella (no confía en nadie más), y cada pedido lleva una clave secreta. Sin clave no se sirve nada: ni la
página, ni los datos, ni las fotos.

**Secretos en la Mac.** En `~/Library/Application Support/vitrina/` (carpeta `0700`, archivos `0600`), nunca en el
repo ni en `config.json`:
- `cert.pem` + `key.pem`: certificado propio EC P-256, válido 10 años, generado con `/usr/bin/openssl` la primera
  vez que se empareja.
- `secret`: la clave, 32 bytes aleatorios (`secrets.token_urlsafe(32)`).

**Emparejar: `python3 server.py pair`**, con el celu enchufado (depuración USB autorizada) y la app instalada:
1. Si falta `adb`, el celu o la app, lo dice y termina.
2. Genera el certificado si no existe y **una clave nueva** (emparejar de nuevo deja afuera a cualquier celu
   emparejado antes, por ejemplo uno perdido).
3. Le pasa a la app, por `adb`, la clave, la huella SHA-256 del certificado, el puerto y la IP WiFi actual de la
   Mac. La pantalla de emparejar de la app solo la puede abrir `adb` (ninguna otra app del celu puede
   re-emparejarla hacia otro server).
4. La app muestra "Emparejado"; el server imprime lo mismo y la dirección WiFi.
5. Si el server estaba corriendo, hay que reiniciarlo para que tome la clave nueva (lo dice al terminar).

**El server.**
- Sin emparejar, `python3 server.py` no arranca: avisa que primero hay que correr `python3 server.py pair`.
- Siempre HTTPS (TLS 1.2 o más), también por cable.
- Cada pedido necesita la clave en el header `Authorization: Bearer <clave>` (la app lo pone en todos sus
  pedidos, también en los de la página; ninguna cookie). Comparación en tiempo constante
  (`hmac.compare_digest`). Sin clave → `401`, sin nada útil en la respuesta (ni cuerpo ni versión del server).
- Siguen: chequeo del `Host`, lista fija de archivos, solo `GET`, timeout de conexiones, `"wifi": false` para
  solo cable.
- Nunca arranca solo.

**La app.**
- El WebView no sale a la red por su cuenta: la app hace cada pedido de la página (la página, los datos, las
  fotos, las fuentes) con su propio cliente HTTPS, que acepta el certificado solo si su huella coincide con
  la emparejada y manda la clave en el header `Authorization`. Con cualquier otro certificado no se manda
  nada y la app muestra "No es tu Mac". El sondeo en segundo plano usa el mismo cliente.
- La clave se guarda solo cifrada con una clave del Android Keystore, en el almacenamiento privado de la app:
  el WebView nunca la recibe, así que no queda en ninguna cookie. Los datos de la app quedan fuera de backups
  y transferencias entre celus, y el WebView no confía en ninguna autoridad de certificados.
  (Revisión 2026-11-13, después de la revisión de código.)
- Si el server responde `401` (se emparejó otro celu o se borró la clave en la Mac), la app muestra "Volvé a
  emparejar" con la misma explicación del primer arranque.

**Lo que se pierde.** La página ya no se ve en Chrome ni en ningún navegador. Hasta que la app exista, el server
sigue como en el Plan 1; el cierre del server y la app llegan juntos.

## 8c. Arrancar y frenar desde cualquier terminal (revisión 2026-11-14)

Pedido del usuario: no tener que entrar a la carpeta y correr `python3 server.py` cada vez, poder frenarlo desde
cualquier lado ("no sé dónde está corriendo el server": quedó uno corriendo sin terminal) y que al frenarlo se
libere todo lo que vitrina usa de la Mac. Y el ícono de la app, que no tenía.

**Enfoques considerados.**

| Tema | Opciones | Elegida y por qué |
|---|---|---|
| Acceso | (a) dos apps de Mac (`osacompile`) en el Dock; (b) dos `.command` que abren la Terminal; **(c) comandos de terminal** | **(c)**, elección del usuario. |
| Desde cualquier carpeta | **(a) enlace en `~/.local/bin`** (ya en el PATH); (b) alias en `~/.zshrc`; (c) instalador | **(a)**. (b) toca el perfil del usuario; (c) suma dependencias. |
| Reposo largo | (a) seguir como hasta ahora; **(b) frenarse si la Mac durmió más de 1 h** | **(b)**. Mientras duerme el server no usa nada, pero la Mac pudo cambiar de red (de casa a un café) y el server despertaría escuchando ahí. Costo: después de un reposo largo hay que correr `vitrina start`. |

**Comandos.** `server.py` es ejecutable (`#!/usr/bin/env python3`) y `~/.local/bin/vitrina` es un enlace a él.
`python3 server.py ...` sigue andando igual.

- `vitrina` (sin nada): como hoy, en primer plano; Ctrl+C lo frena.
- `vitrina start`: lo arranca en segundo plano, desconectado de la terminal (se puede cerrar). Espera a que
  esté sirviendo y muestra lo mismo que el arranque normal (direcciones); si no arranca (sin emparejar, puerto
  ocupado), muestra el error y termina con error. Si ya estaba corriendo, lo dice.
- `vitrina stop`: encuentra el server donde sea que esté corriendo (en segundo plano o en otra terminal) y lo
  frena. Si no estaba corriendo, lo dice.
- `vitrina pair`: igual que hoy.

**Encontrar el server.** Todo server que arranca toma un candado (`fcntl.flock`) sobre
`~/Library/Application Support/vitrina/server.pid` (`0600`), con su número de proceso adentro, y lo tiene hasta
que termina. El sistema suelta el candado aunque el proceso muera de golpe, así un archivo viejo nunca hace
frenar a otro proceso. Candado tomado = hay un server; un segundo server dice "ya está corriendo" en vez de
"puerto ocupado".

**Frenar libera todo.** `stop` le manda `SIGTERM`; el server lo trata igual que Ctrl+C: deja de escuchar
(libera el puerto), corta los hilos y saca el `adb reverse`. Si el daemon de `adb` no estaba corriendo cuando
vitrina lo usó por primera vez, lo cierra (`adb kill-server`); si ya estaba, lo deja (otro programa lo usa).
Si no termina en unos segundos, `stop` lo mata. La pantalla del celu se apaga sola, como cuando la Mac se duerme.

**Reposo.** Un hilo mira cada pocos segundos cuánto durmió la Mac (el reloj de pared contra
`CLOCK_UPTIME_RAW`, que no avanza mientras duerme) y lo va sumando. Mientras duerme, macOS se despierta unos
segundos cada 15–20 min (Power Nap): eso no cuenta como despertar; la cuenta vuelve a cero recién con 5 min
despierta seguidos. Con más de 1 h sumada, el server lo anota en el log y se frena igual que con `stop`.
(Revisión 2026-11-14: la primera versión miraba el salto entre dos miradas, y Power Nap no la dejaba disparar.)

**Log.** En segundo plano, la salida del server va a `~/Library/Application Support/vitrina/server.log` (`0600`,
se pisa en cada `start`).

**Ícono de la app.** Ícono adaptable (Android 8+, ya es el mínimo de la app): la pantallita sobre un soporte del
ícono de notificación, color `moon` sobre fondo `night`.

**No cambia.** Nada arranca solo: `start` lo corre el usuario. Sin emparejar no arranca.

## 8d. Release v1.0.0 y repo público (revisión 2026-11-15)

Pedido del usuario: cerrar el proyecto como v1, pasar el repo a público y publicar el release v1.0.0 con la app
lista para instalar, así nadie necesita JDK ni el SDK de Android. (La web para mostrarlo viene después, aparte.)

**Enfoques considerados (firma del APK).**

| Opción | Costo | Elegida y por qué |
|---|---|---|
| **(a) Firmar en la Mac, a mano** | Hay que guardar la clave de firma con backup | **(a)**, elección del usuario. La clave nunca sale de la Mac. |
| (b) GitHub Actions firma en cada tag | La clave vive en GitHub y el repo suma una acción automática | Más superficie de ataque a cambio de poco. |
| (c) Sin APK, solo código | Instalar sigue pidiendo JDK + SDK | Rompe lo prometido (§8: "se distribuye como APK"). |

**Firma.** Clave nueva (`keytool`, RSA 4096, ~27 años) en `~/Library/Application Support/vitrina-release/`
(carpeta `0700`, archivo `0600`), fuera del repo; su contraseña en el Llavero de macOS. Gradle firma el release
solo si recibe la clave por variables de entorno: sin ellas, el build de release sale sin firmar y nadie más
necesita nada. `*.jks` y `*.keystore` van al `.gitignore` por las dudas. **El usuario hace backup de la clave y
su contraseña**: sin ellas no se puede publicar una actualización que se instale encima de la v1.

**Versión.** La app pasa a `versionName "1.0.0"`. El APK se publica como `vitrina-1.0.0.apk` en el release
`v1.0.0` (tag anotado sobre `main`), con su SHA-256 en las notas (en inglés y castellano) para poder verificarlo.

**Textos.** Todo lo que el server y la app le dicen al usuario usa el comando `vitrina` (`vitrina start`,
`vitrina stop`, `vitrina pair`) en vez de `python3 server.py`. El README pone el enlace de `vitrina` como paso de
la instalación y mantiene el equivalente con `python3 server.py` para quien no lo configure. La instalación de la
app pasa a ser: bajar el APK del release, verificar el SHA-256 y `adb install`; compilarla queda en "Development".

**Repo público.** Antes: la IP real de la Mac en un test (`PairingTest.kt`) pasa a una de ejemplo; el historial
se revisó y no tiene secretos (el email de los commits queda, decisión del usuario). Al publicar: protección contra
secretos de GitHub (secret scanning + push protection) activada. Los detalles menores pendientes quedan como issues.

**Verificación.** Tests del server y de la app; `apksigner verify` del APK; en el Nokia: desinstalar la versión de
desarrollo (firma distinta), instalar el APK del release, emparejar y ver los paneles.

## 9. Pruebas

- **Server (TDD):** `python -m unittest`, sin dependencias. Las llamadas a internet y la hora actual entran
  como parámetros, así los tests no tocan la red. Fixtures guardados: HTML real de contribuciones de GitHub,
  JSON de Claude (con los campos confirmados en el binario de Claude Code) y JSON de Open-Meteo.
  Cubre: parseo de cada fuente, racha, marca de ritmo, 0 % después del reinicio, mapeo de códigos de clima,
  elección de idioma, armado de `/api/state`, que `/api/photo` no sirva nada fuera de la carpeta, config faltante.
- **App (TDD de la lógica):** tests JUnit de la máquina de estados de pantalla (cuándo mantener, soltar y
  prender, incluido "apagada a mano").
- **Página y app en el celu:** verificación manual en el Nokia, con capturas (`adb exec-out screencap`) de cada
  panel y de los estados sin datos y sin conexión.

## 10. Riesgos y cosas a verificar al implementar

- **Prender la pantalla desde segundo plano en Android 12**: es lo más incierto. Hacer primero una prueba
  descartable en el Nokia.
- **Claude:** forma del JSON del Keychain (confirmada en uso real el 2026-11-12).
- **GitHub:** formato actual del HTML y zona horaria de los días (afecta "hoy" y la racha).
- **Fotos grandes** (12 MP) en un CPU lento: el server no puede achicarlas sin dependencias. Medir; si traba,
  el README recomienda fotos de ~1600 px. *Medido 2026-11-14 en el Nokia:* hasta 12 MP (4032 px) se ven bien;
  una de 50 MP se ve cortada. El usuario eligió achicarlas a mano (`sips -Z 1600`); el README lo explica.
- **Emparejamiento:** que la pantalla de emparejar de la app solo la pueda abrir `adb` (protegida con un permiso
  que solo tiene el shell, p. ej. `android.permission.DUMP`). Probarlo en el Nokia: otra app no debe poder abrirla.
- **WebView con certificado propio:** que todos los pedidos de la página (página, `fetch`, fotos) pasen por el
  cliente fijado por huella de la app. Probado en el Nokia (la prueba descartable usó una cookie; la versión
  final no usa ninguna).
- **Open-Meteo:** confirmar si la atribución alcanza con el README o hay que mostrarla.

## 11. Lo que queda a criterio de quien construye

Nombres de campos del JSON y de módulos, intervalos exactos (dentro de lo indicado), diseño de los íconos de
clima y del ícono de la app (dentro del estilo), cómo se arma el proyecto Gradle, la firma del APK (la clave
no va al repo), y los textos exactos en cada idioma.
