# vitrina — sitio web Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el sitio estático de vitrina (portada con demo en vivo, "Cómo se ve", instalación, seguridad, es/en) listo para que el usuario lo publique en Cloudflare Pages.

**Architecture:** `website/` tiene la página (HTML/CSS/JS a mano, sin dependencias) y `website/build.py`, que arma `dist/`: copia el sitio, copia `web/` como `dist/demo/` con un shim que fabrica `/api/state` en el navegador, y genera los datos de ejemplo con el código real del server. Nada de `web/`, `vitrina/` ni `android/` se modifica.

**Tech Stack:** Python 3.9+ (solo biblioteca estándar, `unittest`), HTML, CSS y JavaScript sin build; Chrome sin ventana para verificar.

**Spec:** `docs/superpowers/specs/2026-11-16-vitrina-sitio-web.md` (léela entera antes de empezar; los textos finales están en su Apéndice A).

## Global Constraints

- **Frenar antes de publicar.** No hagas `git push`, no mergees a `main`, no uses `wrangler` ni nada de Cloudflare, no cambies la visibilidad ni la configuración del repo en GitHub. Eso lo hace el usuario.
- Todo el trabajo va en la rama **`feat/website`** (creada desde `main`).
- **Commits sin atribución:** nunca agregues `Co-Authored-By` ni ninguna línea de autoría o "generated with" a un commit. Mensajes en inglés, estilo `feat(website): …` (como el historial del repo).
- No se modifican `web/`, `vitrina/`, `android/`, `server.py`, los READMEs ni los tests existentes.
- Solo biblioteca estándar de Python 3.9 (`from __future__ import annotations` en archivos nuevos). Sin `npm`, sin librerías ni CDN en el sitio. La máquina del usuario tiene Python 3.9.6.
- Ni el sitio ni la demo pueden tener `<script>` o `<style>` en línea, ni atributos `style=""` escritos en el HTML (la CSP de `_headers` los bloquea). `element.style.setProperty` desde JS sí vale.
- Colores: `--night #1A2142`, `--dusk #262F59`, `--haze #3A4475`, `--mist #9AA1C7`, `--moon #F1F2FA`, `--lamp #FFCF6E`. Fuentes: `Big Shoulders Display` (títulos y wordmark) y `Atkinson Hyperlegible Next` (el resto); los archivos salen de `dist/demo/fonts/`. Sin flechas `→` en botones, sin etiquetas en mayúsculas, sin animaciones de entrada ni efectos de hover; el único movimiento es el de la demo.
- Textos exactos: los del Apéndice A de la spec, en voseo. `{versión}` es la de `android/app/build.gradle.kts`.
- Los enlaces externos llevan `rel="noopener noreferrer"`. Responsive con un solo corte a 860 px; sin scroll horizontal desde 320 px.
- Los scripts temporales y las capturas van al directorio scratchpad de la sesión (`/private/tmp/claude-501/-Users-nico-Developer--lab-vitrina/25c574d1-289e-497c-ad15-59f3111c049a/scratchpad`, abajo `$S`), no al repo. Las maquetas de referencia están en `spike/sitio/maqueta-portada.html` (opción A) y `spike/sitio/maqueta-resto.html`: **no están en git** (`spike/` está ignorado) pero sí en esta máquina; el CSS del sitio se porta de ahí.

## Review Focus

1. **Fecha del visitante en el shim** (zona horaria, cambio de mes, 29 de febrero, domingo vs. lunes): el gráfico de GitHub tiene que dar lo mismo que `github_view` para esa fecha. → Task 2 (paridad con 5 fechas).
2. **Build corrido desde otra carpeta** (Cloudflare corre el comando desde la raíz, pero un humano puede no): no puede depender del directorio actual. → Task 1 (`test_build_runs_from_any_cwd`).
3. **Cambia `web/`** (otra ruta de datos, otro `<script>`) y la demo se rompe en silencio: el build tiene que fallar. → Task 1 (`test_build_fails_if_app_js_stops_fetching_state`, `test_inject_requires_exactly_one_app_script`).
4. **Sin `localStorage` ni `navigator.clipboard`** (ventana privada, HTTP): la página tiene que andar igual, sin botón de copiar y sin guardar el idioma. → Task 3 (verificación manual con la API anulada).
5. **El aviso `ready` de un iframe nunca llega** (demo lenta o rota): a los 4 s el iframe se muestra igual. → Task 3.
6. **`?lang=` con un valor raro** (`?lang=fr`): cae al idioma del navegador, no rompe nada. → Task 3.

---

## Mapa de archivos

| Archivo | Responsabilidad |
|---|---|
| `website/build.py` | Arma `dist/` (§7 de la spec). Funciones puras y testeables. |
| `website/demo-shim.js` | Se inyecta en `dist/demo/index.html`; fabrica `/api/state` en el navegador. |
| `website/index.html`, `styles.css`, `site.js` | La página, sus estilos y su comportamiento (idioma, copiar, escala, `ready`). |
| `website/_headers`, `favicon.svg`, `og.png` | Cabeceras de Cloudflare, ícono, imagen para compartir. |
| `website/demo-photos/` | 3 fotos CC0 + `SOURCES.tsv`. |
| `tests/test_website_build.py` | Pruebas del build. |
| `.gitignore` | Agrega `dist/`. |

---

### Task 1: `build.py` con sus pruebas

**Files:**
- Create: `website/build.py`, `website/index.html` (mínimo, se reemplaza en el Task 3), `website/demo-photos/` (ver paso 1), `tests/test_website_build.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces (en `website/build.py`; los tests lo cargan con `importlib.util.spec_from_file_location("website_build", ROOT / "website" / "build.py")` porque `website/` no es un paquete):
  - `class BuildError(Exception)`
  - `DEFAULT_SITE_URL = "https://vitrina.pages.dev"`, `PHOTOS = ["bariloche.jpg", "estrellas.jpg", "lago-vertical.jpg"]`
  - `read_version(repo: Path) -> str` — `versionName` de `android/app/build.gradle.kts`; `BuildError` si no aparece.
  - `demo_pairs() -> list[list[int]]` — 365 pares `[nivel, cantidad]`, de más viejo a más nuevo, determinista.
  - `pairs_to_days(pairs: list[list[int]], today: date) -> list[Day]` — `Day` de `vitrina.github`; el par `i` tiene fecha `today - (364 - i)` días.
  - `demo_state(repo: Path, lang: str, now: datetime) -> dict` — estado completo (`json.dumps`-able) con los cuatro paneles.
  - `build(repo: Path, out: Path, site_url: str = DEFAULT_SITE_URL) -> None`
  - `main() -> int` — repo = `Path(__file__).resolve().parent.parent`, salida `repo / "dist"`, `site_url` de la variable de entorno `SITE_URL` si existe; imprime los errores en stderr y devuelve 1.
- Consumes: `vitrina.state.Store`, `vitrina.state.build_state`, `vitrina.config.Config`, `vitrina.github.Day`, `vitrina.i18n.STRINGS`.

- [ ] **Step 1: Crear la rama y mudar las fotos**

```sh
git switch -c feat/website
mkdir -p website/demo-photos
sips -Z 1600 -s format jpeg -s formatOptions 80 spike/sitio/fotos/3.jpg --out website/demo-photos/bariloche.jpg
sips -Z 1600 -s format jpeg -s formatOptions 80 spike/sitio/fotos/1.jpg --out website/demo-photos/estrellas.jpg
sips -Z 1600 -s format jpeg -s formatOptions 80 spike/sitio/fotos/0.jpg --out website/demo-photos/lago-vertical.jpg
```

Armar `website/demo-photos/SOURCES.tsv` copiando `spike/sitio/fotos/FUENTES.tsv` y cambiando solo la primera columna (`3.jpg`→`bariloche.jpg`, `1.jpg`→`estrellas.jpg`, `0.jpg`→`lago-vertical.jpg`) y el encabezado (`archivo` queda). Verificar: las tres fotos existen, cada una pesa menos de 600 KB y su lado más largo es 1600 px (`sips -g pixelWidth -g pixelHeight <foto>`).

- [ ] **Step 2: `.gitignore`, `website/index.html` mínimo y un shim vacío**

Agregar la línea `dist/` a `.gitignore`. Crear `website/demo-shim.js` con solo `// replaced in task 2` (el build lo copia y los tests lo necesitan). `website/index.html` por ahora: `<!doctype html><html lang="es" data-version="__VERSION__"><head><meta charset="utf-8"><title>vitrina</title><link rel="canonical" href="__SITE_URL__/"></head><body></body></html>`.

- [ ] **Step 3: Escribir `tests/test_website_build.py` (falla)**

Estructura: `ROOT = Path(__file__).resolve().parent.parent`; carga del módulo como arriba; helper `make_repo(tmp: Path) -> Path` que copia `web/`, `vitrina/`, `android/app/build.gradle.kts` (con `shutil.copy` creando el árbol), `website/` y `server.py` + `config.json` si existen (los deja en el repo de prueba a propósito, para comprobar que NO llegan a `dist`). Cada test usa `tempfile.TemporaryDirectory()`. Tests, con sus aserciones:

- `test_read_version_matches_gradle`: `read_version(ROOT)` == la cadena entre comillas de `versionName` leída con una regex propia en el test (hoy `"1.0.0"`).
- `test_read_version_fails_without_version`: en un repo de prueba cuyo `build.gradle.kts` no tiene `versionName`, `assertRaises(BuildError)`.
- `test_demo_pairs_shape_and_determinism`: `len == 365`; cada par tiene `0 <= nivel <= 4`; `count == 0` si `nivel == 0` y `count > 0` si no; los últimos 12 pares tienen `nivel >= 2` y `count == 6`; dos llamadas devuelven lo mismo.
- `test_pairs_to_days_dates`: con `today = date(2026, 11, 16)`, el primer `Day.date` es `today - 364 días`, el último es `today`, y `Day.level/count` salen del par.
- `test_demo_state_has_four_panels_and_real_strings`: para `es` y `en`: `state["panels"] == ["clock", "github", "claude", "photos"]`, `state["strings"] == STRINGS[lang]`, `state["lang"] == lang`, `state["link"] == "wifi"`, `state["photos"] == ["photos/bariloche.jpg", "photos/estrellas.jpg", "photos/lago-vertical.jpg"]`, y `json.dumps(state)` no falla.
- `test_build_output_files`: tras `build(repo, out)`, existen `out/index.html`, `out/demo/index.html`, `out/demo/app.js`, `out/demo/styles.css`, `out/demo/weather-icons.svg`, `out/demo/fonts/big-shoulders-display.woff2`, `out/demo/demo-shim.js`, `out/demo/state.es.json`, `out/demo/state.en.json`, `out/demo/demo-days.json` y las tres fotos en `out/demo/photos/`; y **no** existen `out/build.py`, `out/demo-shim.js` ni `out/demo-photos`.
- `test_demo_days_json_matches_pairs`: `json.loads(out/demo/demo-days.json) == demo_pairs()`.
- `test_shim_injected_once_before_app_js`: en `out/demo/index.html`, `html.count('<script src="demo-shim.js"></script>') == 1` y su posición es menor que la de `<script src="app.js"></script>`.
- `test_inject_requires_exactly_one_app_script`: en un repo de prueba donde `web/index.html` no tiene `<script src="app.js"></script>` (o lo tiene dos veces), `build` lanza `BuildError`.
- `test_build_fails_if_app_js_stops_fetching_state`: en un repo de prueba cuyo `web/app.js` no contiene `fetch('/api/state'`, `build` lanza `BuildError`.
- `test_version_and_site_url_substituted`: `out/index.html` contiene `data-version="` + la versión, y con `site_url="https://example.test"` contiene `https://example.test/` y no `__SITE_URL__`; sin pasar `site_url`, contiene `DEFAULT_SITE_URL`.
- `test_unreplaced_placeholder_fails`: un repo de prueba cuyo `website/index.html` contiene `__OTRO__` hace fallar `build` con `BuildError`.
- `test_dist_has_no_private_files`: tras un build del repo de prueba, `os.walk(out)` no encuentra ningún archivo ni carpeta llamado `server.py`, `config.json`, `config.example.json`, `.tools`, `.superpowers`, `android`, `vitrina` ni `__pycache__`.
- `test_build_runs_from_any_cwd`: `subprocess.run([sys.executable, str(ROOT / "website" / "build.py")], cwd=<carpeta temporal>)` termina con código 0 y deja `ROOT / "dist" / "demo" / "state.es.json"` (limpiar `dist/` después con `shutil.rmtree`).

- [ ] **Step 4: Verificar que falla**

Run: `python3 -m unittest tests.test_website_build -v`
Expected: error al cargar `website/build.py` (no existe).

- [ ] **Step 5: Implementar `website/build.py`**

Las firmas son las de Interfaces. Decisiones que los tests no fijan:
- `build` agrega `repo` a `sys.path` para importar `vitrina`, y mide todas las rutas desde `repo` (nada de `Path.cwd()`).
- Orden (§7 de la spec): borrar `out`; `shutil.copytree(repo/"website", out, ignore=shutil.ignore_patterns("build.py", "demo-shim.js", "demo-photos", "__pycache__"))`; copiar `web/` a `out/demo/`; copiar `website/demo-shim.js` a `out/demo/`; copiar `website/demo-photos/*.jpg` a `out/demo/photos/`; inyectar el shim; escribir los JSON; reemplazar `__VERSION__` y `__SITE_URL__` en `out/index.html`; recorrer `out` y levantar `BuildError` si algún archivo de texto (`.html`, `.js`, `.css`, `.json`, `_headers`, `.svg`) contiene un `__[A-Z_]+__`.
- `demo_pairs`: `rng = random.Random(7)`; 365 veces: con probabilidad 0,5 (`rng.random() < 0.5`) `nivel = rng.choice([1, 1, 2, 2, 3, 4])`, si no 0; `cantidad = nivel * 3`. Después, los últimos 12: `nivel = max(nivel, 2)`, `cantidad = 6`.
- `demo_state`: arma un `Store` con clima de ejemplo `{"temp": 18, "max": 22, "min": 11, "condition": "partly_cloudy", "is_day": True}`, `github_days = pairs_to_days(demo_pairs(), now.date())`, y `claude_usage = {"session": {"pct": 42.0, "resets_at": now + 2 h 14 min}, "week": {"pct": 51.0, "resets_at": now + 3 d 5 h}}`; llama `build_state(store, Config(github_user="demo", claude=True), lang, "wifi", now, 3)` y reemplaza `state["photos"]` por `["photos/" + p for p in PHOTOS]` (relativas a `/demo/`). Los bloques `github` y `claude` que salen de acá son solo para que existan los paneles: el shim los vuelve a calcular.
- La inyección busca la cadena exacta `<script src="app.js"></script>`; si `count != 1` → `BuildError("web/index.html must have exactly one <script src=\"app.js\"></script>")`. Chequear también `"fetch('/api/state'" in app.js`.
- `read_version`: regex `versionName\s*=\s*"([^"]+)"`.

- [ ] **Step 6: Verificar que pasa**

Run: `python3 -m unittest tests.test_website_build -v`
Expected: todos OK. Luego `python3 -m unittest` completo: sin fallas nuevas.

- [ ] **Step 7: Commit**

```sh
git add .gitignore website tests/test_website_build.py
git commit -m "feat(website): build script that assembles the site and the live demo"
```

---

### Task 2: `demo-shim.js` y la paridad con `github_view`

**Files:**
- Create: `website/demo-shim.js`

**Interfaces:**
- Consumes: de `build.py` — `dist/demo/state.{es,en}.json` (cargados con ruta relativa `state.<lang>.json`), `dist/demo/demo-days.json` (pares `[nivel, cantidad]`, 365).
- Produces: el script reemplaza `window.fetch` para `pathname === "/api/state"`; expone `window.__demoGithubView(pairs: number[][], todayISO: string) -> {total, streak, today, weeks, months}`; manda `parent.postMessage({ vitrinaDemo: "ready" }, location.origin)` una sola vez, ~400 ms después de entregar el primer estado y solo si `parent !== window`.

- [ ] **Step 1: Escribir el script de paridad (falla)**

Crear `$S/parity.py` (no va al repo). Argumentos: raíz del repo y carpeta `dist`. Para cada fecha de `["2026-11-16", "2026-11-15", "2026-03-01", "2028-02-29", "2027-01-01"]`:
1. Leer `dist/demo/demo-days.json` y construir en Python los `Day` con `today - (364 - i)` días; `want = github_view(days, today)` (de `vitrina.github`).
2. Escribir en `$S` una página `parity.html` con `<script src="file://<dist>/demo/demo-shim.js"></script>` y un segundo `<script>` que haga `document.body.textContent = JSON.stringify(window.__demoGithubView(<pares como JSON>, "<fecha>"))`.
3. Correr `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --dump-dom --virtual-time-budget=2000 file://<parity.html>` y extraer el JSON de `<body>…</body>`.
4. `assert got == json.loads(json.dumps(want))`, imprimiendo la fecha que difiere. Al final imprimir `paridad OK`.

Run: `python3 website/build.py && python3 -I $S/parity.py "$PWD" "$PWD/dist"`
Expected: FAIL (el shim no existe todavía).

- [ ] **Step 2: Implementar `website/demo-shim.js`**

Un solo IIFE, sin dependencias. Contrato:
- `lang` = `"en"` si `?lang=en`, si no `"es"`. `t0 = Date.now()` al cargar el script.
- `window.fetch` queda envuelto: si `new URL(input, location.href).pathname === "/api/state"` responde `demoState()`; si no, delega en el `fetch` original.
- `demoState()`: baja `state.<lang>.json` y `demo-days.json` con el `fetch` original (una vez, en caché), reemplaza `state.github` y `state.claude`, y devuelve `new Response(JSON.stringify(state), { headers: { "Content-Type": "application/json" } })`. Si ya mandó el aviso `ready`, no lo repite.
- **`github`**: `githubView(pairs, todayMs)`, donde `todayMs` es la fecha **local** del visitante a medianoche UTC (`Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())`) y el par `i` tiene fecha `todayMs - (364 - i) * 86400000`. Es el port de `vitrina/github.py::github_view` y tiene que dar **idéntico** resultado. Algoritmo (no lo determinan las firmas):

```js
function githubView(pairs, todayMs) {
  const DAY = 86400000;
  const days = pairs.map(([level, count], i) => ({ ms: todayMs - (364 - i) * DAY, level, count }));
  const counts = new Map(days.map((d) => [d.ms, d.count]));
  let streak = 0;
  let day = counts.get(todayMs) ? todayMs : todayMs - DAY; // today isn't over yet
  while ((counts.get(day) || 0) > 0) { streak++; day -= DAY; }
  const weeks = [];
  const firstOfWeek = new Map();
  const start = days[0].ms - new Date(days[0].ms).getUTCDay() * DAY; // Sunday (getUTCDay: Sun=0)
  for (const d of days) {
    const diff = Math.round((d.ms - start) / DAY);
    const w = Math.floor(diff / 7), slot = diff % 7;
    while (weeks.length <= w) weeks.push([]);
    while (weeks[w].length < slot) weeks[w].push(null);
    weeks[w].push(d.level);
    if (!firstOfWeek.has(w)) firstOfWeek.set(w, d.ms);
  }
  const months = [];
  for (const w of [...firstOfWeek.keys()].sort((a, b) => a - b)) {
    const month = new Date(firstOfWeek.get(w)).getUTCMonth() + 1;
    if (!months.length || months[months.length - 1].month !== month) months.push({ week: w, month });
  }
  if (months.length > 1 && months[0].week === 0 && months[1].week <= 2) months.shift();
  return { total: days.reduce((n, d) => n + d.count, 0), streak, today: counts.get(todayMs) || 0, weeks, months };
}
```

  `window.__demoGithubView = (pairs, iso) => githubView(pairs, Date.parse(iso + "T00:00:00Z"))`.
- **`claude`**: `{ session: view(42, t0 + (2*60+14)*60000), week: view(51, t0 + (3*24+5)*3600000, true) }` con `now = Date.now()` calculado en cada pedido. `view(pct, resetsMs, isWeek)`: si `now >= resetsMs` devuelve `{ pct: 0, resets_at: null }` (y `elapsed_pct: null` para la semana); si no, `{ pct, resets_at: new Date(resetsMs).toISOString() }`, y para la semana además `elapsed_pct = round(clamp((now - (resetsMs - 7*86400000)) / (7*86400000) * 100, 0, 100))` con `round(x) = Math.floor(x + 0.5)`. La sesión no lleva `elapsed_pct` (igual que `claude_view`).

- [ ] **Step 3: Verificar paridad**

Run: `python3 website/build.py && python3 -I $S/parity.py "$PWD" "$PWD/dist"`
Expected: `paridad OK` con las 5 fechas. Si una difiere, el bug está en el port (revisar semanas y `months`), no en el test.

- [ ] **Step 4: Commit**

```sh
git add website/demo-shim.js
git commit -m "feat(website): demo shim that serves fresh sample state in the browser"
```

---

### Task 3: La página (`index.html`, `styles.css`, `site.js`)

**Files:**
- Modify: `website/index.html` (reemplaza el mínimo del Task 1)
- Create: `website/styles.css`, `website/site.js`

**Interfaces:**
- Consumes: `__VERSION__` y `__SITE_URL__` (los reemplaza `build.py`); `dist/demo/` (iframes `demo/?lang=…[&panel=…]`); el mensaje `{ vitrinaDemo: "ready" }` del shim.
- Produces: la página completa. Contrato de marcado que `site.js` usa:
  - `<html lang="es" data-version="__VERSION__">`; cada texto traducible lleva `data-i="clave"` (claves del Apéndice A); los atributos traducibles usan `data-i-attr="aria-label:clave"`.
  - `button#lang` con `aria-pressed`, dos `<span lang>` (`es`, `en`); el activo se marca con `aria-current="true"`.
  - Cada `.screen` lleva `data-max` (escala máxima) y `data-frame` (ancho sin escalar del marco), y vive dentro de un `[data-box]` cuyo ancho no depende de la pantalla. Portada: `data-max="0.86"`, `data-frame="950"`, `[data-box]` = `.stage`. Cuadrícula: `data-max="0.5"`, `data-frame="912"`, `[data-box]` = cada `.item`.
  - Cada `<iframe>` lleva `data-src` (sin `src`): `demo/` para la portada; `demo/?panel=clock|github|claude|photos` para la cuadrícula, con `loading="lazy"`, `inert`, `tabindex="-1"` y `title`. `site.js` les agrega `lang=` y recién ahí pone `src`.
  - Bloques de comandos: `.term` con un `<button class="copy-btn" data-i="copy">` y el texto del comando en un `<pre>` hijo (`data-copy` en el `.term`).

- [ ] **Step 1: `index.html`**

Escribir el HTML en español (funciona sin JS salvo la demo), con la estructura de §4 de la spec y los textos del Apéndice A: `<head>` con `charset`, `viewport`, `theme-color #1A2142`, `<title>` y `meta description` (`meta.title`, `meta.description`), `canonical` y `og:title/description/image/url/type`, `twitter:card=summary_large_image` (la imagen es `__SITE_URL__/og.png`), `<link rel="icon" href="favicon.svg" type="image/svg+xml">`, `<link rel="stylesheet" href="styles.css">`, `<script src="site.js" defer>`. Cuerpo: `header.nav`, `main` con `section.hero`, `section#como-se-ve`, `section#instalacion`, `section#seguridad`, `section.closing`, y `footer`. Un `<h1>` solo (el de la portada). En la portada el celu es `div.phone > div.screen > iframe`, dentro de `div.stage[data-box]`. Cada ítem de la cuadrícula es `figure.item[data-box]` con `div.screen`, `figcaption` con `h3` y `p`, y `role="img"` + `aria-label` (clave `panels.alt` con `{t}` = el título del panel) en el contenedor de la pantalla. Los pasos de instalación son una `<ol class="steps">`. Los cuatro hechos de seguridad son `div.facts > div` con `h3` y `p` (sin tarjetas). Enlaces: los de la última línea del Apéndice A; `GitHub ↗` del nav y `Ver en GitHub` van a `https://github.com/nicob201/vitrina`.

- [ ] **Step 2: `styles.css`**

Portar el CSS de las maquetas, cambiando las rutas de las fuentes a `demo/fonts/…`:
- Portada: de `spike/sitio/maqueta-portada.html`, bloque `.site`/`nav`/`.hero`/`.stage`/`.phone`/`.screen`/`.desk`/`.eyebrow`/`.headline`/`.lede`/`.caption`/`.btn`/`.ctas` de la opción **A** (`.a`). Sin el contenedor `.site` ni `.option`: las secciones van a ancho completo sobre `--night`.
- Resto: de `spike/sitio/maqueta-resto.html`: `.panels-2` (cuadrícula de la opción 2), `.install`/`.needs`/`.steps`/`.term`/`.note`, `.security`/`.sec`/`.facts`, `.closing`, `footer`.
- Tokens en `:root` (los de Global Constraints), fondo del `body` `--night`, texto `--moon`.
- Un solo corte `@media (max-width: 860px)`: grilla de paneles a 1 columna; `.install` y `.sec` a 1 columna; nav solo con wordmark, GitHub y `#lang`; h1 44 px, h2 40 px; `section` con padding 56 px 16 px.
- Foco: `:focus-visible { outline: 2px solid var(--lamp); outline-offset: 3px }`.
- `.screen` usa `--s` (la fija `site.js`); `iframe { opacity: 0; transition: opacity .2s }` y `iframe.ready { opacity: 1 }`. Con `@media (prefers-reduced-motion: reduce)` la transición desaparece.
- Los iframes fijados llevan `pointer-events: none`; el de la portada no.

- [ ] **Step 3: `site.js`**

Un archivo, sin dependencias. Contenido: `const STRINGS = { es: {...}, en: {...} }` con **todas** las claves del Apéndice A (copiadas literales; `{versión}` y `{t}` quedan como están y se reemplazan al pintar) y estas funciones (todas en el ámbito del archivo, ninguna global):
- `pickLang(): "es" | "en"` — `?lang=es|en` si es uno de los dos; si no, `localStorage.getItem("lang")` (dentro de `try/catch`); si no, `navigator.language` que empiece con `es` → `"es"`, el resto `"en"`. Cualquier otro valor de `?lang=` se ignora.
- `applyLang(lang: string): void` — recorre `[data-i]` (`innerHTML`, son constantes propias) y `[data-i-attr]`; reemplaza `{versión}` por `document.documentElement.dataset.version` y `{t}` por el título del panel; actualiza `<html lang>`, `document.title`, `meta[name=description]` y los `og:`/`twitter:` que lo necesiten; marca el botón `#lang`; guarda el idioma en `localStorage` (con `try/catch`); y (re)carga los iframes: `iframe.src = iframe.dataset.src + (contiene "?" ? "&" : "?") + "lang=" + lang`.
- `setupCopy(): void` — si `!navigator.clipboard`, oculta todos los `.copy-btn`; si existe, al tocar uno copia el texto de su `.term pre` con `navigator.clipboard.writeText` y cambia su texto a `copied` durante 1,5 s.
- `fitScreens(): void` — para cada `.screen`: `box = el.closest("[data-box]")`; ancho disponible = `box.clientWidth` menos el padding horizontal de `box` (`getComputedStyle`); `s = Math.min(Number(el.dataset.max), disponible / Number(el.dataset.frame))`; `el.style.setProperty("--s", s)`. Se llama al cargar, con un `ResizeObserver` sobre cada `[data-box]` y en `resize`.
- `setupReady(): void` — escucha `message`: ignora todo lo que no cumpla `event.origin === location.origin && event.data && event.data.vitrinaDemo === "ready"`; busca el iframe cuyo `contentWindow === event.source` y le agrega la clase `ready`. Además, `setTimeout` de 4 s por iframe: si todavía no tiene `ready`, se la agrega. Al recargar los iframes por cambio de idioma, se les saca `ready` y se repite el temporizador.
- Arranque: `setupReady(); setupCopy(); fitScreens(); applyLang(pickLang());` y el click de `#lang` alterna el idioma y llama `applyLang`.

- [ ] **Step 4: Verificar en el navegador**

```sh
python3 website/build.py
python3 -m http.server 8793 --bind 127.0.0.1 --directory dist &
C="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$C" --headless=new --disable-gpu --hide-scrollbars --window-size=1280,3400 --virtual-time-budget=25000 --screenshot=$S/p-es.png "http://127.0.0.1:8793/?lang=es"
"$C" --headless=new --disable-gpu --dump-dom --virtual-time-budget=8000 "http://127.0.0.1:8793/?lang=en" | grep -c "Your old phone, now a desk display"
"$C" --headless=new --disable-gpu --dump-dom --virtual-time-budget=8000 "http://127.0.0.1:8793/?lang=fr" | grep -o '<html lang="[a-z]*"'
```

Expected: la captura `p-es.png` muestra portada con la demo andando, la cuadrícula con **cuatro paneles distintos** (no cuatro relojes), instalación, seguridad, cierre y pie (mirar la imagen y compararla con `spike/sitio/maqueta-portada.html` y `maqueta-resto.html`); el segundo comando imprime `1`; el tercero imprime `<html lang="…"` con el idioma del navegador de Chrome (no rompe). Revisar a mano: con `navigator.clipboard` y `localStorage` anulados desde la consola, la página sigue sin errores; los botones de copiar desaparecen.

- [ ] **Step 5: Commit**

```sh
git add website
git commit -m "feat(website): the page, its styles and its es/en behavior"
```

---

### Task 4: Cabeceras, ícono, imagen para compartir y la prueba del `dist` completo

**Files:**
- Create: `website/_headers`, `website/favicon.svg`, `website/og.png`
- Modify: `tests/test_website_build.py`

**Interfaces:**
- Consumes: el build de los tasks anteriores. Produces: `dist/` completo, listo para subir.

- [ ] **Step 1: Prueba que falla**

Agregar a `tests/test_website_build.py`:
- `test_dist_complete`: tras `build(repo, out)`, existen `out/index.html`, `out/styles.css`, `out/site.js`, `out/_headers`, `out/favicon.svg`, `out/og.png`.
- `test_headers_csp`: `out/_headers` empieza con `/*`, contiene `Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin` y `Permissions-Policy: camera=(), microphone=(), geolocation=()`.
- `test_no_inline_scripts_or_styles`: `re.search(r"<script(?![^>]*\bsrc=)", html)` y `re.search(r"<style|\sstyle=", html)` no encuentran nada en `out/index.html` ni en `out/demo/index.html`.
- `test_page_has_no_third_party_urls_loaded`: en `out/index.html`, `out/styles.css` y `out/site.js`, ningún `<script src>`, `<link rel="stylesheet">`, `<link rel="icon">`, `<img src>`, `<iframe src>` ni `url(` apunta a `http://` o `https://` (los `<a href>`, el `canonical` y las metas `og:` sí pueden tener URLs absolutas).

Run: `python3 -m unittest tests.test_website_build -v` → Expected: FAIL en `test_dist_complete` y `test_headers_csp`.

- [ ] **Step 2: Crear los tres archivos**

- `website/_headers`: exactamente el bloque del §7 de la spec (una línea de ruta `/*` y las cuatro cabeceras con dos espacios de sangría).
- `website/favicon.svg`: un cuadrado redondeado `#1A2142` con una "v" en `#F1F2FA` (trazo, no texto, para que no dependa de fuentes); 32×32 de `viewBox`.
- `website/og.png` (1200×630): armar en `$S` una página de prueba con fondo `#1A2142`, el wordmark `vitrina` (Big Shoulders Display, 120 px) y el título de la portada en dos líneas a la izquierda, y a la derecha la pantalla del panel de GitHub de la demo (captura de `http://127.0.0.1:8793/demo/?panel=github` a 890×396, con `--virtual-time-budget=8000`, sin marco de celu). Sacarle captura con `--window-size=1200,630 --screenshot`. Debe pesar menos de 300 KB.

- [ ] **Step 3: Verificar**

Run: `python3 -m unittest tests.test_website_build -v` → Expected: todos OK. Mirar `og.png` (se ve nítida, el texto no se corta).

- [ ] **Step 4: Commit**

```sh
git add website tests/test_website_build.py
git commit -m "feat(website): security headers, favicon and share image"
```

---

### Task 5: Verificación de punta a punta (sin código nuevo, salvo arreglos)

**Files:** ninguno nuevo; los arreglos que salgan se commitean aparte (`fix(website): …`).

- [ ] **Step 1: Servidor local que aplica `_headers`**

Escribir `$S/serve_dist.py` (no va al repo): un `http.server` sobre `dist/` en `127.0.0.1:8794` que, en cada respuesta, agrega las cabeceras de `dist/_headers`. Es necesario porque `python3 -m http.server` ignora `_headers` y sin eso la CSP no se prueba.

- [ ] **Step 2: Chequeos de la spec §10 (manuales)**

Con `python3 website/build.py` recién corrido y el servidor del paso 1:
1. Errores de CSP: `"$C" --headless=new --disable-gpu --enable-logging=stderr --v=0 --virtual-time-budget=15000 --dump-dom http://127.0.0.1:8794/ 2>&1 | grep -i "content security policy"` → Expected: sin salida. Repetir con `http://127.0.0.1:8794/demo/?panel=claude`.
2. Capturas a 320, 390, 860 y 1280 px de ancho (`--window-size=<ancho>,3600 --virtual-time-budget=25000 --screenshot`): sin scroll horizontal (nada se corta a la derecha), la demo entera visible, la cuadrícula en una columna debajo de 860 px.
3. Peso inicial: sumar el tamaño de `index.html`, `styles.css`, `site.js`, `_headers` y los woff2 de `dist/demo/fonts/` → Expected: menos de 300 KB (la demo y las fotos no cuentan).
4. Sin pedidos a otros dominios: `grep -rEho 'https?://[^"'"'"' )]+' dist/index.html dist/styles.css dist/site.js dist/demo/*.js dist/demo/*.html` → solo enlaces `<a>` (GitHub, Open-Meteo, Wikimedia, `__SITE_URL__` ya reemplazado) y las URLs de `og:`/`canonical`.
5. Gráfico de GitHub y cuentas regresivas: en dos capturas del panel de Claude con 60 s de diferencia (`--virtual-time-budget` no sirve para esto: usar dos corridas con `sleep 60` entre medio), el texto "Se reinicia en 2 h N min" baja.

Cualquier fallo se arregla en el task que lo originó y se vuelven a correr sus pruebas; no se sigue hasta que los cinco pasan.

---

### Task 6: Cierre (sin publicar)

- [ ] **Step 1: Todo el repo en verde**

Run: `python3 -m unittest` → Expected: OK (los tests de siempre más `test_website_build`). `git status` limpio; `dist/` no aparece (ignorado).

- [ ] **Step 2: Informe al usuario y parar**

Detenerse en `feat/website` sin pushear. Informar: lista de commits (`git log --oneline main..feat/website`), el resultado de la paridad y de los chequeos del Task 5, y recordar los pasos que le tocan a él (§11 de la spec): mergear a `main` y pushear, conectar Cloudflare Pages con `python3 website/build.py` y `dist`, `PYTHON_VERSION=3.12` si el build no encuentra Python, abrir el sitio y repasar los criterios manuales, correr Lighthouse. Después de publicar, con su OK, enlazar el sitio desde los READMEs y poner la URL en el campo Website del repo.
