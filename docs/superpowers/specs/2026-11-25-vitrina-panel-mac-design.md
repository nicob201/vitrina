# vitrina — el panel "Mac" (recursos de la computadora)

> Estado: **aprobado** · 2026-11-25
> Salió del brainstorming del 25 de noviembre. La maqueta elegida (B2) y las pruebas de medición están en
> `spike/panel-mac/` (fuera del repo: `spike/` está en `.gitignore`). Lo que importa de ellas está acá.

## 1. Qué es y por qué

Un panel más en la rotación que muestra cómo está la Mac: CPU, GPU, memoria y red con un gráfico de los últimos
5 minutos, y disco y batería como dato fijo. Es para mirarlo de reojo en el escritorio, como el resto de vitrina.

La condición que manda: **la carga sobre la Mac tiene que ser la menor posible.** Todo lo visual (dibujar, escalar,
formatear, animar) lo hace el celu. La Mac solo lee los números, que el celu no puede ver.

## 2. Decisiones ya tomadas

| Tema | Decisión |
|---|---|
| Dónde va | **En la rotación**, como un panel más. No es una pantalla fija. |
| Diseño | Maqueta **B2**: fondo más oscuro, cada dato en su card, un color por dato, gráfico de los últimos 5 min y una card teñida apenas de su color (§5). |
| Qué muestra | CPU, GPU, memoria y red (bajada y subida) con gráfico; disco libre y batería en cards chicas sin gráfico. |
| Cada cuánto lee la Mac | CPU, GPU, memoria y red: **cada 5 s**. Disco y batería: **cada 30 min**. |
| Cuándo pide datos el celu | Cada 5 s, **solo mientras el panel está en pantalla**. |
| Cómo lee la Mac | **Preguntándole directo al sistema** (`ctypes`, solo biblioteca estándar), sin abrir programas para lo que se lee cada 5 s. Medido: ~0,09 ms por lectura (§4.2). |
| Pausa | Si nadie le consultó nada a la Mac en el último minuto (celu apagado, desenchufado o lejos), deja de leer. |
| Ciclo de vida | Corre dentro del proceso de vitrina: arranca con `vitrina start` (o `vitrina`) y `vitrina stop` lo corta junto con todo. También se corta cuando vitrina se frena sola tras más de 1 h de reposo. |
| Reparto de trabajo | **Enfoque 1** (§3): la Mac lee y hace las cuentas (porcentajes y velocidades); el celu dibuja. |

## 3. Enfoques considerados

1. **La Mac lee y hace las cuentas; el celu dibuja. (Elegido.)** La Mac lee cada 5 s, saca porcentajes y
   velocidades (una resta por dato) y guarda los últimos 5 min. El celu pide `/api/metrics` cada 5 s solo con el
   panel en pantalla, y dibuja, escala, formatea y anima.
2. **La Mac manda los valores crudos y el celu hace las restas.** Le ahorra a la Mac una resta por dato cada 5 s,
   que ni se mide, y pasa la lógica más fácil de romper (contadores que vuelven a cero, Mac reiniciada) al
   JavaScript del celu, que el proyecto hoy no prueba con tests. Descartado.
3. **Todo dentro de `/api/state`, pedido más seguido con el panel en pantalla.** Sin dirección nueva, pero cada
   pedido traería y armaría todo el estado (la grilla de GitHub, el clima, Claude) cada 5 s para nada. Descartado.

Por qué el 1: lo caro era leer los datos y eso ya bajó a microsegundos. Pasar las restas al celu no ahorra nada que
se note y deja sin tests lo más delicado. Todo lo visual ya queda del lado del celu.

## 4. Objetivos, no-objetivos y anti-objetivos

**Objetivos**

- Al entrar el panel, el gráfico ya está lleno (si la Mac venía leyendo) y se mueve cada 5 s mientras se ve.
- La carga extra sobre la Mac es despreciable (criterio medible en §9).
- Si una lectura falla (por ejemplo la GPU en una Mac que no la informa), ese dato no aparece y el resto sigue
  andando, igual que los otros paneles.
- Textos en es/en, como todo vitrina.

**No-objetivos (por ahora)**

- Temperaturas y ventiladores (necesitan `sudo` o funciones internas no oficiales).
- Lista de procesos (manda al celu nombres de lo que estás usando).
- Velocidad de lectura y escritura del disco, CPU por núcleo, alertas o colores según la carga.
- Tooltips o tabla de datos: es una pantalla de kiosco y tocar pasa de panel.
- Que el panel aparezca en la demo del sitio web.
- Windows y Linux (vitrina es solo para macOS por ahora).
- Elegir desde la configuración el intervalo o la ventana de 5 min.

**Anti-objetivos (sería un fracaso aunque ande)**

- Que la Mac se note más cargada con el panel prendido.
- Cualquier cosa que pida `sudo`, una dependencia nueva o un permiso nuevo.
- Que los datos salgan de la red local o se sirvan sin la clave y HTTPS de siempre.
- Que un problema de este panel rompa los demás.

## 5. Diseño visual (maqueta B2)

Referencia: `spike/panel-mac/maqueta-b2.html` (ver con el servidor de maquetas o abrir el archivo; usa las fuentes
de `web/fonts/`). Las medidas van en `vh`/`vw` como el resto de `web/styles.css` (la maqueta usa `cqh`/`cqw`, que
equivalen dentro del celu dibujado).

**Estructura** (de arriba abajo, con el mismo padding que los otros paneles):

- Fila de título: el **nombre de la Mac** (`scutil --get ComputerName`, p. ej. "MacBook Air de Nico") en 4,6vh
  bold, seguido de "· últimos 5 min" en `--mist`, peso normal. La esquina con la hora y el enlace queda como en los
  demás paneles.
- Grilla de 4 columnas, `gap: 10px`, que ocupa el resto del alto:
  - **Fila 1**, cuatro cards grandes: CPU · GPU · Memoria · Red.
  - **Fila 2**, dos cards chicas de 11,5vh de alto: Disco (ocupa 2 columnas) · Batería (ocupa 2 columnas).
- La barra de progreso de la rotación, igual que en los otros paneles.

**Card grande**: fila de etiqueta (puntito de 9px del color del dato + nombre, 3,7vh, `--mist`; a la derecha, un
dato de contexto en 3,3vh), número grande (Big Shoulders 700, 13vh, `--moon`, unidad en .42em `--mist`) y el
gráfico, que ocupa el resto de la card y llega hasta sus bordes izquierdo, derecho e inferior.

- CPU: `23 %`. GPU: `6 %`. Memoria: `59 %`, contexto `14,0 / 24 GB`.
- Red: número grande = **bajada** (`0,4 MB/s`); contexto = puntito de subida + `↑ 69 KB/s`.

**Card chica**: etiqueta con puntito · valor en `--moon` 600 · barra de 8px (fondo: el color del dato al 18 %
sobre la card; relleno: el color del dato) · contexto en `--mist`.

- Disco: `302 GB libres` · barra = espacio usado · `de 494 GB`.
- Batería: `80 %` · barra = carga · `enchufada` / `cargando` / `con batería`.

**Gráfico** (SVG dibujado en el celu, sin librerías):

- Línea de 2px, puntas y uniones redondeadas; relleno debajo con el color al 16 % de opacidad; un punto de radio
  4px al final, con un aro de 2px del color de la card.
- Eje X: el tiempo, los últimos 300 s contados desde la muestra más nueva (así no importa si los relojes del celu y
  la Mac difieren). Si la historia es más corta, la línea arranca más a la derecha.
- Eje Y: CPU, GPU y memoria de 0 a 100 % fijo. Red: escala compartida entre bajada y subida, tope = el máximo de las
  dos × 1,1, nunca menos de 1 MB/s (así el ruido de una red quieta no parece un pico).
- En la card de red, la subida va como segunda línea, sin relleno.
- Un `null` corta la línea (no se une por encima del hueco). La primera muestra después de vaciar la historia trae
  CPU y red en `null`, porque es solo el punto de partida.

**Colores**

| Rol | Valor |
|---|---|
| Fondo del panel | `#0D1126` (más oscuro que `--night`, pero índigo: el negro puro se ve gris en la pantalla del celu) |
| Card | `#1A2142` (`--night`), borde 1px del color del dato al 28 %, radio 14px |
| Tinte de la card (B2) | degradé vertical de `#1A2142` (hasta el 30 %) al color del dato al 16 % sobre la card; las cards chicas, color al 9 % plano |
| CPU | `#338ced` (azul) |
| GPU | `#e76624` (naranja) |
| Memoria | `#00a888` (aguamarina) |
| Red, bajada | `#d28e05` (ámbar) |
| Red, subida | `#e24d8b` (magenta) |
| Disco | `#0aac23` (verde) |
| Batería | `#9887ef` (violeta) |

Los siete colores pasaron el validador de paleta de la skill dataviz en modo oscuro sobre `#1A2142`: distancia
entre vecinos con daltonismo ≥ 10, contraste ≥ 3:1. Los números y textos van siempre en `--moon`/`--mist`, nunca
en el color del dato: el color va en el puntito, la línea y el relleno.

**Casos que cambian la grilla**

- Sin GPU (ninguna muestra trae valor): la card no aparece y las otras tres se reparten el ancho.
- Sin batería (Mac de escritorio): la card no aparece y Disco ocupa la fila entera.

## 6. Cómo funciona

### 6.1 En la Mac (`vitrina/metrics.py`, nuevo)

Lecturas cada 5 s, sin abrir programas (código ya probado en `spike/panel-mac/`):

| Dato | Cómo | Costo medido |
|---|---|---|
| CPU % | `host_statistics(HOST_CPU_LOAD_INFO)` → ticks user/system/idle/nice; % = Δ(user+system+nice) / Δ(total) | 0,002 ms junto con memoria |
| Memoria usada | `host_statistics64(HOST_VM_INFO64)`; usada = (internal − purgeable + wired + compressor) × tamaño de página, como "Memoria usada" del Monitor de Actividad. Total: `os.sysconf("SC_PHYS_PAGES") × os.sysconf("SC_PAGESIZE")` | (idem) |
| GPU % | IOKit: servicio `IOAccelerator` → propiedad `PerformanceStatistics` → `"Device Utilization %"` (sin `sudo`; probado en M4). Si hay varias, la mayor | 0,021 ms |
| Red | `getifaddrs`, entradas `AF_LINK` de las interfaces cuyo nombre empieza con `en` (WiFi y Ethernet; así una VPN no se cuenta dos veces); bytes de `if_data` (offsets 40 y 44). La velocidad suma la diferencia **de cada interfaz** presente en las dos lecturas: una que aparece o desaparece (un dock, un adaptador USB) no cuenta, en vez de parecer un salto de 4 GB | 0,063 ms |

Cada 30 min (y al arrancar):

- Disco: `shutil.disk_usage("/")` (en esta Mac da lo mismo que el volumen de datos: 302 GB libres de 494 GB, como
  Finder).
- Batería: `pmset -g batt` (5 ms, una vez cada 30 min). La primera línea dice si viene de `'AC Power'` o
  `'Battery Power'`; la línea `InternalBattery` trae `80%; AC attached; not charging` / `charging` /
  `discharging`. Sin línea `InternalBattery` → sin batería. Estados para el celu: `ac`, `charging`, `battery`.

Una vez al arrancar: el nombre (`scutil --get ComputerName`; si falla, "Mac").

**Reglas de las cuentas**

- Los contadores de ticks y de bytes son de 32 bits y vuelven a cero: la diferencia se calcula módulo 2³².
- Las marcas de tiempo son `time.time()` (segundos). Si entre dos muestras pasaron más de 15 s (la Mac durmió, o
  hubo una pausa), se **vacía la historia** y esa muestra queda solo como punto de partida: CPU y red necesitan dos
  lecturas seguidas.
- La historia guarda las muestras de los últimos 300 s (60 a 5 s).
- Una lectura que falla devuelve `None` para ese dato y se registra en el log **solo la primera vez**, para no
  llenarlo cada 5 s.

**Pausa sin celu**: la app del celu le consulta `/api/state` a la Mac cada 20 s aunque tenga la pantalla apagada, y
la página cada 30 s. Cada pedido con la clave correcta a `/api/state` o `/api/metrics` anota la hora. Si la última
fue hace más de 60 s, la lectura de 5 s no lee nada (y la historia se vacía por la regla de arriba). Al arrancar
vitrina cuenta como un pedido. Con la Mac dormida no corre nada, como hoy. Disco y batería no se pausan: son 5 ms
cada 30 min.

### 6.2 La dirección nueva: `GET /api/metrics`

Misma protección que todo lo demás (HTTPS, clave por cabecera, `Host` local), `Cache-Control: no-store`. Responde:

```json
{
  "interval": 5,
  "samples": [{"t": 1795637400, "cpu": 23.1, "gpu": 6, "ram": 15032385536, "down": 412000, "up": 69000}],
  "ram_total": 25769803776,
  "disk": {"free": 302059892736, "total": 494384795648},
  "battery": {"pct": 80, "state": "ac"}
}
```

- `cpu` y `gpu` en %, `ram` en bytes usados, `down`/`up` en bytes por segundo. Un dato que no se pudo leer va como
  `null`. `disk` y `battery` pueden ser `null`.
- Unos 5 KB con la historia llena. La Mac no arma nada en el pedido: devuelve lo que ya tiene.

### 6.3 En el estado (`/api/state`)

- Opción nueva en `config.json`: `"mac": false` por defecto, como `"claude"`. Si está en `true` en una Mac, la
  fuente arranca; fuera de macOS se avisa en el log y no arranca.
- El panel `"mac"` entra en `panels` cuando la opción está prendida y hubo una primera lectura con algún dato.
  Desde ahí **no sale** aunque la historia se vacíe (pausa o reposo), para que la rotación no cambie sola. Va entre
  `claude` y `photos`: reloj, GitHub, Claude, **Mac**, fotos.
- Con `"mac": false`, `/api/metrics` responde 404.
- `state["mac"] = {"name": "MacBook Air de Nico"}`. Los números no van en el estado: van en `/api/metrics`.

### 6.4 En el celu (`web/`)

- `index.html`: la sección `#mac` con las seis cards.
- `app.js`: `renderers.mac` pone el nombre y los textos. Al mostrar el panel (`show('mac')`) pide `/api/metrics`
  enseguida y después cada 5 s; al pasar a otro panel deja de pedir. Con `?panel=mac` (fijado) pide siempre.
  Si un pedido falla, queda el último dibujo, como el resto de la página.
- Formatos con `Intl.NumberFormat(lang)`: red en KB/s debajo de 1 MB/s y en MB/s con un decimal arriba (base 1000,
  como el Monitor de Actividad); disco en GB base 1000 (como Finder); memoria en GB base 1024 (24 GB, como "Acerca
  de esta Mac").
- `styles.css`: el fondo y las cards del §5. La esquina y la barra de progreso quedan como en los otros paneles.
- La app Android no cambia: ya deja pasar cualquier GET de la página a la Mac emparejada, con la clave.

## 7. Seguridad y privacidad

- Nada nuevo sale de la red local: la Mac no consulta ningún servicio para este panel.
- Sin `sudo`, sin dependencias, sin permisos nuevos de macOS (lo probado no pidió ninguno).
- Lo que ve el celu: porcentajes, bytes por segundo, espacio en disco, batería y el nombre de la Mac. No hay nombres
  de procesos ni de archivos.

## 8. Archivos

| Archivo | Cambio |
|---|---|
| `vitrina/metrics.py` | Nuevo: lecturas con `ctypes`, las cuentas, la historia y el cuerpo de `/api/metrics`. |
| `vitrina/app.py` | Arranca la fuente (5 s y 30 min) si `cfg.mac`; anota la hora de cada pedido para la pausa. |
| `vitrina/handler.py` | Ruta `/api/metrics` (un `get_metrics` más en `make_server`). |
| `vitrina/state.py` | El panel `mac` en `panels` y `state["mac"]`. |
| `vitrina/config.py`, `config.example.json` | Opción `"mac": false`. |
| `vitrina/i18n.py` | Textos del Apéndice A. |
| `web/index.html`, `web/app.js`, `web/styles.css` | El panel. |
| `README.md`, `README.es.md` | El panel en la lista de arriba y la opción `"mac"`. |
| `tests/test_metrics.py` + los tests de handler, state y config | Ver §9. |

El sitio web no cambia: la demo responde solo `/api/state` y su configuración no prende `"mac"`, así que el panel
no aparece ni se pide `/api/metrics`. El test del build sigue valiendo.

## 9. Pruebas y criterios de aceptación

**Tests (TDD, `unittest`, sin dependencias)**

- Porcentaje de CPU a partir de dos lecturas de ticks, incluido un contador que vuelve a cero.
- Velocidad de red a partir de dos lecturas, incluido el salto de 2³².
- Fórmula de memoria usada con números de ejemplo.
- `pmset -g batt`: enchufada sin cargar (la salida real de esta Mac), cargando, con batería, y Mac sin batería.
- Historia: guarda 300 s; un salto de más de 15 s la vacía y la muestra siguiente es solo punto de partida.
- Pausa: sin pedidos en 60 s no lee; un pedido la reactiva.
- Una lectura que falla deja `null` en ese dato, no corta las demás y se registra una sola vez.
- `/api/metrics`: 401 sin clave, 200 con JSON y `no-store` con clave.
- Estado: el panel aparece con `"mac": true` y una muestra, en su lugar de la rotación; no aparece con `false` ni
  sin muestras.
- Config: `"mac"` tiene que ser `true` o `false`.
- Mismos textos en es y en.
- En macOS (saltado en otro sistema): las lecturas reales dan valores en rango (CPU y GPU entre 0 y 100, memoria
  usada menor que el total, bytes de red ≥ 0).

**En la Mac y el celu**

- El panel se ve como la maqueta B2 en el Nokia (890 × 396) y entra en la rotación después de Claude.
- Los números coinciden con el Monitor de Actividad dentro de unos puntos (CPU, memoria usada, red).
- Al entrar el panel, el gráfico ya está lleno; mientras se ve se mueve cada 5 s; al salir, el celu deja de pedir
  (se ve en el log si se agrega uno temporal, o contando pedidos).
- **Carga:** el tiempo de CPU del proceso de vitrina (`ps -o cputime`) durante 10 min con el panel en la rotación
  sube **menos de 1 s** respecto de 10 min con `"mac": false`. (Esperado: ~11 ms de lecturas más los pedidos.)
- `vitrina stop` deja sin proceso ni hilo de vitrina; con el celu desenchufado más de 1 min, la lectura se pausa.

## 10. Lo que queda a criterio de quien lo construya

- La forma exacta del código en `metrics.py` (funciones o una clase), mientras las cuentas sean funciones puras
  testeables sin `ctypes`.
- Cómo se dibuja el SVG en `app.js`, siguiendo §5 (la maqueta trae una versión que sirve de punto de partida).
- La redacción final de los textos del Apéndice A.

## Apéndice A — Textos

| Clave | es | en |
|---|---|---|
| `mac_window` | últimos 5 min | last 5 min |
| `mac_cpu` | CPU | CPU |
| `mac_gpu` | GPU | GPU |
| `mac_ram` | Memoria | Memory |
| `mac_net` | Red | Network |
| `mac_disk` | Disco | Disk |
| `mac_battery` | Batería | Battery |
| `mac_disk_free` | {free} libres | {free} free |
| `mac_disk_of` | de {total} | of {total} |
| `mac_ac` | enchufada | plugged in |
| `mac_charging` | cargando | charging |
| `mac_on_battery` | con batería | on battery |
