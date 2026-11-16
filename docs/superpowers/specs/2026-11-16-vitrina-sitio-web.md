# vitrina — el sitio web

> Estado: **aprobado** · 2026-11-16 (ajustado tras la revisión final de la rama: ver cambios en §6.4, §7 y el Apéndice A)
> Salió del brainstorming del 15 y 16 de noviembre. Las maquetas (`spike/sitio/`) quedaron fuera del repo (`spike/` está en `.gitignore`); lo que importa de ellas está acá.

## 1. Qué es y para quién

Una página estática que muestra vitrina y enseña a instalarla. Tiene que servirle a dos personas:

- **Quien llega a ver cómo se ve** y decide si le interesa: lo ve andando, no en una captura.
- **Quien ya quiere instalarla**: encuentra una guía corta y copiable. El detalle completo sigue en el README.

La estética es prioridad, igual que en el producto. Reusa el "escritorio de noche" de `web/`: la misma paleta y las mismas fuentes.

## 2. Decisiones ya tomadas

| Tema | Decisión |
|---|---|
| Demo | La **página real** (`web/`) corriendo adentro de un celu dibujado, con **datos de ejemplo**. Sin capturas ni fotos personales. |
| Portada | Opción **A "Centrada"**: nav, texto arriba, celu grande abajo apoyado en la línea del escritorio. |
| Idiomas | **es/en con botón**, en una sola página. La demo también cambia de idioma. |
| Estructura | **Una sola página**: portada con demo, "Cómo se ve", instalación, seguridad, cierre y pie. |
| "Cómo se ve" | Opción 2: **cuadrícula 2×2** con los cuatro paneles fijados. |
| Dominio | `vitrina.pages.dev`. Uno propio se puede sumar después sin tocar el sitio. |
| Hosting | Cloudflare Pages con la **integración de GitHub** (se publica en cada push a `main`). Sin `wrangler`. |
| Build | Un script de Python sin dependencias que corre Cloudflare. Sin `npm`. |
| Estilo | Limpio, sin librerías ni frameworks, sin trackers ni analítica, sin recursos de terceros. |

## 3. Objetivos y no-objetivos

**Objetivos**

- La portada muestra la demo andando sin que el visitante haga nada.
- Los datos de la demo **nunca se ven viejos**: la hora, la racha de GitHub y las cuentas regresivas de Claude se calculan en el navegador, relativas al momento de la visita.
- Los textos de la demo y del sitio salen del mismo código que el producto: el sitio **no copia a mano** nada de `web/` ni de `vitrina/i18n.py`.
- Anda bien en el celu y en la computadora, con teclado y con lector de pantalla.
- Se puede publicar y mantener sin tocar nada a mano: un push a `main` deja el sitio al día.

**No-objetivos**

- Blog, changelog, documentación completa (eso es el README), formulario de contacto.
- Analítica, cookies, anuncios, fuentes o scripts de otros dominios.
- Más idiomas que es/en, o una URL por idioma (`/en/`).
- Un dominio propio (queda para después; ver §12).

## 4. Estructura de la página

De arriba hacia abajo. El texto final de cada bloque está en el Apéndice A.

1. **Nav**: `vitrina` (wordmark) · Cómo se ve · Instalación · Seguridad · GitHub ↗ · botón es/en.
2. **Portada**: "Gratis y open source · v{versión}", el título, el texto, dos botones (Instalala, Ver en GitHub) y abajo el celu con la demo y el epígrafe.
3. **Cómo se ve** (`#como-se-ve`): título, subtítulo y cuadrícula 2×2: hora y clima, GitHub, Claude, fotos. Cada uno es una pantalla fijada en ese panel con un título y una línea.
4. **Instalación** (`#instalacion`): a la izquierda el título y las tres cosas que hacen falta; a la derecha los cuatro pasos, con comandos copiables y una nota al final.
5. **Seguridad** (`#seguridad`): título a la izquierda y cuatro afirmaciones a la derecha, separadas por líneas finas (sin tarjetas).
6. **Cierre**: "Sacá ese celu del cajón" y los mismos dos botones.
7. **Pie**: wordmark, créditos y enlaces (GitHub, Releases, README, licencia MIT).

Los números de los pasos de instalación se justifican porque **es una secuencia**; no se usan numeraciones en ningún otro lado.

## 5. Diseño visual

**Colores** (los de `web/styles.css`, más un acento solo del sitio):

| Token | Valor | Uso |
|---|---|---|
| `--night` | `#1A2142` | fondo |
| `--dusk` | `#262F59` | líneas finas, superficies |
| `--haze` | `#3A4475` | bordes, la línea vertical de los pasos |
| `--mist` | `#9AA1C7` | texto secundario |
| `--moon` | `#F1F2FA` | texto principal, botón primario |
| `--lamp` | `#FFCF6E` | acento del sitio: punto de la portada, números de los pasos, foco del teclado |

Las secciones van a ancho completo sobre `--night` (en la maqueta parecen tarjetas solo porque se mostraban sueltas); la de seguridad baja en degradé hasta `#161c3a`, y el pie queda sobre ese mismo tono.

**Tipografía**: `Big Shoulders Display` para títulos y wordmark; `Atkinson Hyperlegible Next` para el resto. Los bloques de comandos usan la fuente monoespaciada del sistema (es código de verdad). Escala: h1 de la portada 76 px, h2 de sección 54 px, h3 de panel 30 px, texto 16–18 px, líneas de menos de 80 caracteres. En pantallas angostas los títulos bajan (h1 44 px, h2 40 px).

**La demo es lo memorable**: el celu grande de la portada. Todo lo demás es callado: sin gradientes decorativos (salvo el resplandor suave detrás del celu), sin tarjetas iguales, sin animaciones de entrada ni efectos al pasar el mouse. El único movimiento propio de la página es el de la demo.

**Botones**: primario `--moon` sobre `--night`; secundario con borde `--haze`. Texto en oración, sin flechas. Foco visible: anillo de 2 px `--lamp` con 3 px de separación.

**El celu dibujado**: marco de CSS (sin imágenes) alrededor de una pantalla de **890×396** (el viewport del Nokia) que contiene un `<iframe>` escalado con `transform: scale()`. Lleva la cámara frontal a la izquierda y un resplandor suave detrás, apoyado en una línea de escritorio (como en la maqueta A).

**Responsive**: un solo corte a 860 px de ancho.

- Debajo de 860 px: la cuadrícula de paneles pasa a 1 columna, instalación y seguridad se apilan (título arriba, contenido abajo), el nav muestra solo wordmark, GitHub y el botón de idioma.
- La escala de cada pantalla se calcula en JS (ver §6.4): `escala = min(escala máxima, ancho disponible / ancho sin escalar)`. En un celu la demo se ve chica pero entera.
- Sin scroll horizontal en ningún ancho a partir de 320 px.

## 6. La demo

### 6.1 Cómo funciona

La demo es una **copia de `web/`** servida en `/demo/` (la arma el build), más un script, `demo-shim.js`, que se inyecta en `demo/index.html` **antes** de `app.js`. El shim reemplaza `window.fetch` para la ruta `/api/state` y devuelve un estado armado en el navegador. Todo lo demás de `app.js` corre sin tocarse, y `web/` no se modifica.

Si `app.js` cambia la forma en que pide los datos (por ejemplo, otra ruta), el build tiene que fallar con un mensaje claro y no publicar una demo rota (ver §7, paso 4).

### 6.2 Qué datos usa

El estado se compone así:

- **Bloques que no dependen de la hora** (`lang`, `strings`, `seconds_per_panel`, `link`, `panels`, `clock.weather`, `photos`): los genera `build.py` **con el código real del server** (`vitrina.state.build_state` y `vitrina.i18n.STRINGS`) y los guarda como `demo/state.es.json` y `demo/state.en.json`. Así los textos de la demo son siempre los del producto.
- **Clima de ejemplo**: 18°, máxima 22°, mínima 11°, parcialmente nublado, de día.
- **`link`**: `wifi`.
- **`github`**: calculado en el navegador por el shim, con el mismo algoritmo que `vitrina/github.py::github_view` portado a JS (semanas, meses, total, racha, "hoy"). Los días salen de `demo/demo-days.json`, una lista de 365 pares `[nivel, cantidad]` de más viejo a más nuevo, que genera `build.py` con una semilla fija (`random.seed(7)`: cerca de la mitad de los días con actividad y una racha de 12 días hasta hoy; sin sesgo por día de la semana, porque el shim corre las fechas según el día de la visita). El shim les pone fechas contando hacia atrás desde **hoy** en el navegador.
- **`claude`**: calculado por el shim. Al cargar la página toma `t0 = Date.now()` y usa sesión 42 % que se reinicia en `t0 + 2 h 14 min`, y semana 51 % que se reinicia en `t0 + 3 d 5 h`. `elapsed_pct` de la semana = `round((ahora − (reinicio − 7 d)) / 7 d × 100)`, igual que `claude_view`. Como los reinicios quedan anclados a `t0`, las cuentas regresivas bajan de verdad mientras la persona mira.
- **`photos`**: tres rutas fijas dentro de `/demo/photos/` (ver §6.3).

Los cuatro paneles (`clock`, `github`, `claude`, `photos`) están siempre presentes.

### 6.3 Fotos

Tres fotos de dominio público (CC0) de Wikimedia Commons, ya descargadas en `spike/sitio/fotos/`. Pasan a `website/demo-photos/` con estos nombres, achicadas con `sips -Z 1600 -s formatOptions 80` (lado más largo 1600 px, que además cumple lo que pide el README para celus viejos):

| Archivo | Foto | Autor | Notas |
|---|---|---|---|
| `bariloche.jpg` (hoy `3.jpg`) | Mountains and Lake in Bariloche | Roger Burkhard | horizontal; es la primera de la demo |
| `estrellas.jpg` (hoy `1.jpg`) | Desert Stargazing | Jamison McAndie | horizontal |
| `lago-vertical.jpg` (hoy `0.jpg`) | Clear lake in the mountains | Tony Reid | **vertical**: muestra cómo vitrina trata las verticales |

`website/demo-photos/SOURCES.tsv` conserva título, autor, licencia, página, URL original y `sha1` de las fotos originales (el contenido de `spike/sitio/fotos/FUENTES.tsv`, con los nombres nuevos). Las fotos se acreditan en el pie aunque CC0 no lo exija.

### 6.4 Dónde se usa

- **Portada**: un iframe **interactivo** (`/demo/?lang={es|en}`) en el celu grande. Rota cada 15 s y, si se lo toca, pasa de panel, igual que el celu real.
- **Cómo se ve**: cuatro iframes **fijados** en un panel (`/demo/?lang=…&panel=clock|github|claude|photos`), con `loading="lazy"`, `inert`, `tabindex="-1"` y un `aria-label` en el contenedor (ver Apéndice A). No se pueden tocar.
- **Cambio de idioma**: al tocar es/en, el sitio cambia sus textos y **recarga** los iframes con el nuevo `?lang=`. La demo vuelve al primer panel; es aceptable.
- **Escalado**: `site.js` recorre los `.screen` con un `ResizeObserver` y fija `--s` (ver §5). Ancho sin escalar de la pantalla: 890 px; en la portada el marco suma 30 px de borde a cada lado (950 px); escala máxima 0.86 en la portada y 0.5 en la cuadrícula.
- **Sin parpadeo del reloj**: una pantalla fijada muestra el reloj un instante hasta que carga el estado. Cada iframe arranca con `opacity: 0` y el shim avisa con `parent.postMessage({ vitrinaDemo: "ready" }, location.origin)`: 400 ms después del primer estado si el panel es el reloj o la demo no está fijada, y si no, 1 s después de que `app.js` cambió al panel fijado (el fundido de `web/` dura 0,9 s). Si el primer pedido de estado falla, el shim lo reintenta en el siguiente sondeo. `site.js` valida `event.origin` y `event.source`, y muestra ese iframe con un fundido corto de 200 ms. Si el aviso no llega en 4 s, lo muestra igual.

Techo conocido: cinco instancias de la página corren a la vez (cada una con su `setInterval` de 1 s). Los cuatro iframes de la cuadrícula son `lazy`, así que solo cargan al acercarse. Si un celu lento se traba, se pausan con `IntersectionObserver`; no hace falta para la v1.

## 7. Build

`website/build.py`: Python 3.9 o más nuevo, **solo biblioteca estándar**, importa el paquete `vitrina/` del repo. Se llama así, desde la raíz del repo:

```sh
python3 website/build.py
```

y deja todo en `dist/` (en `.gitignore`). Pasos, en orden; cualquier error corta con un mensaje claro y código de salida distinto de cero:

1. Borra `dist/` y la vuelve a crear.
2. Copia `website/` a `dist/`, **sin** `build.py`.
3. Copia `web/` a `dist/demo/` (incluye `fonts/` y `weather-icons.svg`) y `website/demo-photos/` a `dist/demo/photos/`.
4. Inyecta `<script src="demo-shim.js"></script>` en `dist/demo/index.html` justo antes de `<script src="app.js"></script>`. Verifica que `index.html` tiene **exactamente una** etiqueta `<script src="app.js"></script>` y que `app.js` contiene `fetch('/api/state'`; si no, falla.
5. Genera `dist/demo/state.es.json`, `state.en.json` y `demo-days.json` (§6.2).
6. Lee la versión de `android/app/build.gradle.kts` (`versionName = "…"`) y falla si no la encuentra. Reemplaza `__VERSION__` en `dist/index.html` por esa versión.
7. Reemplaza `__SITE_URL__` en `dist/index.html` por la variable de entorno `SITE_URL` o, si no existe, por `https://vitrina.pages.dev`.
8. Falla si queda algún `__…__` sin reemplazar en `dist/`.

Los enlaces a releases apuntan siempre a `…/releases/latest`; la versión solo se usa en la portada y en el nombre del APK de los comandos (`vitrina-{versión}.apk`).

### Cabeceras (`website/_headers`, se copia tal cual a `dist/`)

```
/*
  Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
```

Consecuencia: **ni el sitio ni la demo pueden tener scripts en línea**, y el HTML del sitio tampoco tiene `<style>` ni atributos `style=""`. `style-src` admite `'unsafe-inline'` porque `web/app.js` inyecta estilos en línea al pintar (los `style="grid-column:…"` de los meses de GitHub y el `<style>` del sprite `weather-icons.svg`) y la demo no puede modificar `web/`; es un riesgo bajo: un estilo en línea no ejecuta código, y `script-src` sigue en `'self'`.

## 8. Archivos nuevos

```
website/
  index.html            la página, en español (funciona sin JS; site.js traduce a inglés)
  styles.css
  site.js               textos es/en, botón de idioma, botones de copiar, escala de pantallas, aviso "ready"
  demo-shim.js          se inyecta solo en dist/demo/index.html
  build.py
  _headers
  favicon.svg           una "v" del wordmark sobre --night
  og.png                1200×630, vista previa al compartir el enlace
  demo-photos/          3 fotos + SOURCES.tsv
tests/test_website_build.py
```

Se modifica `.gitignore` (agrega `dist/`). **No se toca** `web/`, `vitrina/` ni `android/`.

Los textos que se ven en pantalla viven en `site.js` (objeto `STRINGS = { es: {…}, en: {…} }`) y el HTML marca cada uno con `data-i="clave"`. Los textos del Apéndice A pueden llevar `<code>` y `<a>`, que se insertan con `innerHTML`: es seguro porque son constantes del propio sitio y nunca texto de un visitante ni de la URL.

Idioma inicial: `?lang=es|en` si está; si no, el último elegido guardado en `localStorage` (con `try/catch`: puede no estar disponible); si no, `navigator.language` (`es…` → es; el resto → en). Se actualizan `<html lang>`, `<title>` y la meta descripción.

Los botones "Copiar" usan `navigator.clipboard.writeText`; si la API no existe, el botón no se muestra y el texto sigue seleccionable. Al copiar, el botón dice "Copiado" 1,5 s.

## 9. Seguridad y privacidad del sitio

- Sitio 100 % estático: sin formularios, sin cookies, sin pedidos a otros dominios (las fuentes van locales). La CSP de §7 lo hace cumplir.
- Los enlaces externos llevan `rel="noopener noreferrer"`.
- Nada de datos reales en la demo: el estado es de ejemplo y las fotos son de dominio público. El build **no lee** `config.json`, el Llavero ni la carpeta de secretos.
- `dist/` no puede contener `server.py`, `config*.json`, `.tools/`, `.superpowers/` ni `android/`: el test de §10 lo verifica.
- Los deploys de vista previa de Cloudflare (ramas que no son `main`) son públicos: es aceptable porque el sitio no tiene nada privado. Aun así, el trabajo del sitio se hace en una rama y no se mezcla hasta que se revisa.

## 10. Pruebas y criterios de aceptación

**Automáticas** (`python3 -m unittest`, en `tests/test_website_build.py`; el build corre en un directorio temporal):

- `dist/` tiene `index.html`, `styles.css`, `site.js`, `_headers`, `favicon.svg`, `og.png`, `demo/index.html`, `demo/app.js`, `demo/demo-shim.js`, `demo/state.es.json`, `demo/state.en.json`, `demo/demo-days.json` y las tres fotos.
- `demo/index.html` incluye `demo-shim.js` **exactamente una vez**, antes de `app.js`.
- Ambos `state.*.json` tienen los cuatro paneles en orden (`clock`, `github`, `claude`, `photos`) y `strings` iguales a `vitrina.i18n.STRINGS[lang]`.
- `demo-days.json` tiene 365 pares y el último día tiene nivel > 0 (racha hasta hoy).
- La versión de `index.html` coincide con la de `build.gradle.kts`; no queda ningún `__…__`.
- `dist/` no contiene `server.py`, `config.json`, `config.example.json`, `.tools`, `.superpowers`, `android`.
- El build falla (código ≠ 0) si falta la etiqueta `app.js` o el `fetch('/api/state'` (se prueba con una copia de `web/` alterada).

**Manuales** (en un navegador, sirviendo `dist/` con `python3 -m http.server --directory dist`):

1. La portada muestra el celu con la demo andando, y tocarla cambia de panel.
2. Los cuatro paneles de la cuadrícula muestran su panel (no el reloj) y no parpadean al cargar.
3. El botón es/en cambia el sitio **y** la demo.
4. El gráfico de GitHub termina en el día de hoy y el panel de Claude cuenta hacia atrás.
5. **Paridad del port de `github_view`**: con una fecha fija, el shim y el server dan el mismo resultado. Un comando de una sola vez (sin pasar a CI): `demo-shim.js` expone el cálculo como `window.__demoGithubView(pares, "AAAA-MM-DD")`; se compara su salida en Chrome sin ventana contra `vitrina.github.github_view` para la misma fecha. El plan trae el comando exacto.
6. Anda con teclado (se llega a todo, el foco se ve) y no hay scroll horizontal a 320, 390, 860 y 1280 px de ancho.
7. La pestaña de red no muestra pedidos a otros dominios y la consola no tiene errores de CSP.
8. Lighthouse en el sitio desplegado: accesibilidad ≥ 95, buenas prácticas ≥ 95. (No se fija un número de rendimiento: la demo corre cinco instancias de la página.)

**Peso**: la carga inicial (sin las fotos de la demo) tiene que quedar por debajo de 300 KB.

## 11. Publicación (la hace el usuario)

El plan que sale de esta spec **frena antes de pushear y publicar**. Eso lo hace el usuario en su cuenta:

1. Crear la cuenta de Cloudflare (gratis), con verificación en dos pasos. *(En curso.)*
2. Mergear la rama del sitio en `main` y pushear (a pedido explícito).
3. Workers y Pages → Create → **Pages** → Connect to Git → autorizar la app de GitHub **solo para `nicob201/vitrina`**.
4. Proyecto `vitrina`, rama de producción `main`, **build command** `python3 website/build.py`, **output directory** `dist`, directorio raíz vacío.
5. Si el primer build falla por la versión de Python, agregar la variable de entorno `PYTHON_VERSION=3.12` en Settings → Variables.
6. Abrir `https://vitrina.pages.dev` y repasar los criterios manuales de §10. Si el nombre `vitrina` ya está tomado, elegir otro y avisar: cambia `SITE_URL` (variable de entorno del proyecto) y los enlaces del README.

**Después de publicar** (cada cosa se hace con el OK del usuario): enlazar el sitio desde `README.md` y `README.es.md`, y poner la URL en el campo "Website" del repo (`gh repo edit --homepage`).

## 12. Fuera de alcance, para después

- Dominio propio (el sitio no depende de la URL: `SITE_URL` y la configuración de Cloudflare alcanzan).
- Una URL por idioma (`/en/`) si más adelante importa el posicionamiento en buscadores.
- Pausar con `IntersectionObserver` las demos fuera de pantalla, si se nota lentitud.
- Una sección o página de novedades cuando haya más versiones.

## Apéndice A — Textos

Las claves de la tabla son las de `STRINGS` y los `data-i` del HTML. `{versión}` y `{t}` se reemplazan al pintar. Voseo en castellano, oraciones sin mayúsculas de más.

| Clave | es | en |
|---|---|---|
| `meta.title` | vitrina — tu celu viejo, ahora una pantalla de escritorio | vitrina — your old phone, now a desk display |
| `meta.description` | Convertí un Android viejo en una mini pantalla de escritorio con la hora, el clima, tu actividad en GitHub, el uso de Claude y tus fotos. Gratis y open source. | Turn an old Android phone into a small desk display with the time, weather, your GitHub activity, your Claude usage and your photos. Free and open source. |
| `nav.demo` | Cómo se ve | How it looks |
| `nav.install` | Instalación | Install |
| `nav.security` | Seguridad | Security |
| `nav.github` | GitHub ↗ | GitHub ↗ |
| `hero.eyebrow` | Gratis y open source · v{versión} | Free and open source · v{versión} |
| `hero.title` | Tu celu viejo, ahora una pantalla de escritorio | Your old phone, now a desk display |
| `hero.lede` | La hora y el clima, tu actividad en GitHub, el uso de Claude y tus fotos, rotando en un Android que tenías en un cajón. Tu Mac junta los datos; sin cuentas ni nube. | The time and weather, your GitHub activity, your Claude usage and your photos, rotating on an Android that was sitting in a drawer. Your Mac gathers the data; no accounts, no cloud. |
| `hero.cta1` | Instalala | Install it |
| `hero.cta2` | Ver en GitHub | View on GitHub |
| `hero.caption` | La página real de vitrina, con datos de ejemplo. Tocala para pasar de panel. | The real vitrina page, with sample data. Tap it to switch panels. |
| `panels.title` | Cuatro paneles, uno por vez | Four panels, one at a time |
| `panels.sub` | Rotan solos, cada 15 segundos por defecto. Un panel sin nada para mostrar queda afuera. | They rotate on their own, every 15 seconds by default. A panel with nothing to show is left out. |
| `panels.alt` | {t}: vista en vivo con datos de ejemplo | {t}: live view with sample data |
| `panels.clock.t` | La hora y el clima | Time and weather |
| `panels.clock.d` | El reloj grande, la fecha y el tiempo de tu ciudad. Si se va la Mac, el reloj sigue. | A big clock, the date and your city's weather. If the Mac goes away, the clock keeps going. |
| `panels.github.t` | Tu actividad en GitHub | Your GitHub activity |
| `panels.github.d` | Los cuadraditos del último año, tu racha y lo de hoy. | Last year's squares, your streak and today's count. |
| `panels.claude.t` | El uso de Claude | Your Claude usage |
| `panels.claude.d` | Sesión actual y límite semanal, con marca de ritmo. Opcional, viene apagado. | Current session and weekly limit, with a pace marker. Optional, off by default. |
| `panels.photos.t` | Tus fotos | Your photos |
| `panels.photos.d` | Las de una carpeta de tu Mac. Las verticales se ven enteras. | From a folder on your Mac. Portrait photos are shown whole. |
| `install.title` | Instalala en cuatro pasos | Install it in four steps |
| `install.sub` | Primero, tres cosas que tenés que tener. | First, three things you need. |
| `needs.mac` | Una Mac | A Mac |
| `needs.mac.d` | con Python 3.9 o más nuevo | with Python 3.9 or newer |
| `needs.adb` | adb | adb |
| `needs.adb.d` | `brew install android-platform-tools` (sin traducir) | `brew install android-platform-tools` (not translated) |
| `needs.phone` | Un celu Android | An Android phone |
| `needs.phone.d` | 8 o más nuevo, con depuración USB | 8 or newer, with USB debugging |
| `step1.t` | Bajá vitrina y creá el comando | Get vitrina and create the command |
| `step1.d` | Así podés correr `<code>vitrina</code>` desde cualquier carpeta. El último comando agrega esa carpeta a tu PATH: abrí una terminal nueva después. | That lets you run `<code>vitrina</code>` from any folder. The last command adds that folder to your PATH: open a new terminal afterwards. |
| `step2.t` | Completá la configuración | Fill in the config |
| `step2.d` | Corré `<code>vitrina</code>` una vez: crea `<code>config.json</code>` y avisa que falta emparejar. Poné tu usuario de GitHub, tu ciudad y la carpeta de fotos. | Run `<code>vitrina</code>` once: it creates `<code>config.json</code>` and tells you pairing is still missing. Add your GitHub username, your city and your photos folder. |
| `step3.t` | Instalá la app en el celu | Install the app on the phone |
| `step3.d` | Bajá el APK del `<a>último release</a>` a tu carpeta Descargas, comprobá su huella SHA-256 con la de las notas y, con el celu enchufado por USB, instalalo. | Download the APK from the `<a>latest release</a>` into your Downloads folder, check its SHA-256 against the release notes and, with the phone plugged in over USB, install it. |
| `step3.c` (comentario del comando) | # tiene que coincidir con las notas del release | # must match the release notes |
| `step4.t` | Emparejá y arrancá | Pair and start |
| `step4.d` | El celu confirma el emparejado y vitrina se abre sola. La primera vez te guía por los ajustes del celu que hacen falta. | The phone confirms the pairing and vitrina opens by itself. The first time, it walks you through the phone settings it needs. |
| `install.note` | Para frenarla: `<code>vitrina stop</code>`. Nada arranca solo, y si la Mac duerme más de una hora, vitrina se frena. El detalle completo está en el `<a>README</a>`. | To stop it: `<code>vitrina stop</code>`. Nothing starts by itself, and if the Mac sleeps for more than an hour, vitrina stops. The full details are in the `<a>README</a>`. |
| `copy` / `copied` | Copiar / Copiado | Copy / Copied |
| `security.title` | Cerrada de entrada | Closed by default |
| `security.sub` | vitrina muestra tus datos en tu escritorio, así que está hecha para que nadie más pueda verlos. | vitrina shows your data on your desk, so it is built so nobody else can see it. |
| `sec1.t` | Solo el celu emparejado ve algo | Only the paired phone sees anything |
| `sec1.d` | Todo viaja por HTTPS con un certificado hecho en tu Mac, y cada pedido lleva una clave secreta. Sin ella, el server no responde nada útil. | Everything travels over HTTPS with a certificate made on your Mac, and every request carries a secret key. Without it, the server answers nothing useful. |
| `sec2.t` | Emparejar solo se puede con adb | Pairing only works through adb |
| `sec2.d` | Solo adb puede abrir la pantalla de emparejar de la app, así que ninguna otra app del celu puede apuntar vitrina a otro server. | Only adb can open the app's pairing screen, so no other app on the phone can point vitrina at a different server. |
| `sec3.t` | No hay cuentas ni nube | No accounts, no cloud |
| `sec3.d` | Tus datos no pasan por ningún servidor de vitrina. Al clima se le manda solo el nombre de la ciudad, y el token de Claude solo viaja a Anthropic, nunca al celu. | Your data never goes through a vitrina server. The weather service only gets your city's name, and the Claude token only goes to Anthropic, never to the phone. |
| `sec4.t` | No arranca sola ni toca tus archivos | It never starts itself or touches your files |
| `sec4.d` | Corre solo cuando vos la arrancás. No toca tus archivos ni la configuración de tu Mac: solo guarda lo suyo en su propia carpeta. El código es abierto y el APK está firmado, con su huella en cada release. | It runs only when you start it. It doesn't touch your files or your Mac's settings: it only keeps its own data in its own folder. The code is open and the APK is signed, with its fingerprint in every release. |
| `closing.title` | Sacá ese celu del cajón | Get that phone out of the drawer |
| `closing.small` | Gratis, open source, licencia MIT. | Free, open source, MIT license. |
| `footer.credits` | Datos del clima de `<a>Open-Meteo.com</a>` (CC BY 4.0). Fuentes Big Shoulders Display y Atkinson Hyperlegible Next (SIL OFL 1.1). Fotos de la demo: dominio público (CC0) de `<a>Wikimedia Commons</a>`; autores en `<a>SOURCES.tsv</a>`. | Weather data from `<a>Open-Meteo.com</a>` (CC BY 4.0). Fonts Big Shoulders Display and Atkinson Hyperlegible Next (SIL OFL 1.1). Demo photos: public domain (CC0) from `<a>Wikimedia Commons</a>`; authors in `<a>SOURCES.tsv</a>`. |
| `footer.releases` | Releases | Releases |
| `footer.readme` | README | README |
| `footer.license` | Licencia MIT | MIT license |

Comandos (iguales en los dos idiomas; el `{versión}` se reemplaza):

```sh
# paso 1
git clone https://github.com/nicob201/vitrina.git
cd vitrina
mkdir -p ~/.local/bin && ln -s "$PWD/server.py" ~/.local/bin/vitrina
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc

# paso 3
cd ~/Downloads
shasum -a 256 vitrina-{versión}.apk   # (comentario traducido: step3.c)
adb install vitrina-{versión}.apk

# paso 4
vitrina pair
vitrina start
```

Los enlaces: GitHub → `https://github.com/nicob201/vitrina`; último release → `…/releases/latest`; Releases → `…/releases`; README → `…#readme`; Open-Meteo → `https://open-meteo.com/`; Wikimedia → `https://commons.wikimedia.org/`; SOURCES.tsv → `…/blob/main/website/demo-photos/SOURCES.tsv`.
