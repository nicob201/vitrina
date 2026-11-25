# vitrina — el panel "Mac" en el sitio web (diseño corto)

> Estado: **aprobado** · 2026-11-25
> Cambia lo que decía el spec del panel Mac (§4 y §8): el sitio ahora sí lo muestra.

## Intención

El sitio muestra la página real de vitrina. Tiene que incluir el panel Mac, que se agregó hoy.

**Objetivos:** el panel se ve en la demo grande y en la grilla, con gráficos que se mueven; los textos es/en lo
cuentan.

**No-objetivos:** rediseñar la página, cambiar `og.png`, la versión (sigue v1.0.0, Android no cambió) o `web/`.

**Anti-objetivos:** datos reales de la Mac del autor en el sitio; pedidos a terceros o cambios en la CSP.

## Enfoques (dónde va el quinto panel)

- **A, destacado:** Mac grande arriba y la grilla 2×2 como está. Se lee mejor, pero no sigue la rotación.
- **B, grilla corrida (elegido):** reloj, GitHub / Claude, Mac / fotos. Es más simple y sigue la rotación; las
  fotos quedan solas en la última fila.

## Cambios

- **Demo (`website/build.py`):** `mac: true` y un nombre de ejemplo, "Mi Mac" / "My Mac".
- **`website/demo-shim.js`:** responde `/api/metrics` en el navegador con el formato real: 5 min de muestras
  inventadas cada 5 s, relativas a la hora del visitante, así el gráfico entra lleno y avanza. Disco y batería fijos.
- **`website/index.html` y `site.js` (es/en):** la card "Tu Mac" / "Your Mac" entre Claude y fotos ("CPU, GPU,
  memoria y red de los últimos 5 minutos, más disco y batería. Opcional, viene apagado."), "Cinco paneles", y el
  panel nombrado en la bajada principal y en las descripciones para buscadores y al compartir. El paso 2 de
  instalación dice que se activa con `"mac": true`.
- **`website/styles.css`:** las fotos, centradas en la última fila con el mismo ancho que las otras (decisión mía).
  En el celular sigue todo en una columna.

## Pruebas

- Tests primero: la demo trae cinco paneles en orden; hay seis iframes, ninguno en el orden de tabulación.
- Con `node` (se salta si no está): `/api/metrics` del shim da las claves del formato real, 300 s de historia y
  valores en rango.
- En el navegador, con `dist/` servido: se ve en la demo grande y en `?panel=mac`, en es y en, en escritorio y a
  ancho de celular, sin errores en consola.

## Límites

Sin push hasta tener tu OK.

## A criterio de quien lo construya

La forma de las curvas inventadas y la redacción final de los textos.
