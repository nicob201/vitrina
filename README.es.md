# vitrina

*[Read in English](README.md)*

Convertí un celular Android viejo en una mini pantalla de escritorio. La computadora junta los datos y
el celu los muestra a pantalla completa, rotando entre paneles:

- **Hora** con la fecha y el clima
- **Actividad en GitHub**: los cuadraditos de contribuciones, tu racha y lo de hoy
- **Uso de Claude**: sesión actual y límite semanal, con marca de ritmo (opcional)
- **Fotos** de una carpeta de tu computadora

Gratis y open source. Sin cuentas, sin nube, sin instalar nada más que Python.

## Qué necesitás

- Una computadora con **macOS o Windows** y **Python 3.9 o más nuevo**.
  - macOS: corré `python3 --version` en la Terminal; si no está, macOS te ofrece instalarlo.
  - Windows: instalalo desde [python.org](https://www.python.org/downloads/).
- Un **celular Android** con Chrome, en el mismo WiFi que la computadora o enchufado por USB.

## Arranque rápido

```sh
git clone https://github.com/nicob201/vitrina.git
cd vitrina
python3 server.py
```

La primera vez crea `config.json`. Completalo (ver abajo) y volvé a arrancar el server. Te muestra las
direcciones para abrir en el celu:

```
vitrina is running
  WiFi:  http://192.168.0.10:8765
  Cable: http://localhost:8765
Press Ctrl+C to stop.
```

## Configuración (`config.json`)

| Opción | Por defecto | Qué hace |
|---|---|---|
| `port` | `8765` | Puerto donde escucha el server |
| `wifi` | `true` | `false` = solo se puede usar por cable USB |
| `language` | `"auto"` | `"auto"` sigue el idioma del celu; `"es"` o `"en"` para forzarlo |
| `seconds_per_panel` | `15` | Cuánto queda cada panel en pantalla (5 o más) |
| `github_user` | `""` | Tu usuario de GitHub. Vacío = sin panel de GitHub |
| `claude` | `false` | `true` activa el panel de uso de Claude (ver abajo) |
| `city` | `""` | Ciudad para el clima. Vacío = sin clima |
| `country` | `""` | Código de país de dos letras, opcional, para elegir bien la ciudad. Ej.: `"AR"` |
| `units` | `"celsius"` | `"celsius"` o `"fahrenheit"` |
| `photos_dir` | `""` | Carpeta de fotos. Vacío = sin panel de fotos |

Un panel sin nada para mostrar queda afuera de la rotación. Al arrancar, el server muestra qué lugar
encontró para tu ciudad, así ves que eligió el correcto.

## Conectar el celu

**Por WiFi.** Abrí la dirección `WiFi:` en Chrome del celu y tocá la pantalla una vez para pasar a
pantalla completa. Consejo: fijá la IP de tu computadora en el router para que la dirección no cambie.

- **Que la pantalla no se apague:** por WiFi, Chrome no tiene permitido mantener la pantalla prendida. En
  el celu, activá Opciones de desarrollador → **Pantalla activa** (queda prendida mientras carga).
- **Windows:** la primera vez, el firewall pregunta por Python. Permitilo en **redes privadas**, o el
  celu no lo va a encontrar.
- **macOS con Python de python.org:** corré una vez *Install Certificates.command* (en la carpeta de
  Python dentro de Aplicaciones), o GitHub, Claude y el clima no van a poder conectarse.

**Por cable.** Instalá [adb](https://developer.android.com/tools/releases/platform-tools), activá la
depuración USB en el celu y enchufalo. El server se da cuenta (`USB: phone connected`) y arma la conexión
solo; abrí `http://localhost:8765` en el celu.

Tocá la pantalla para pasar al panel siguiente. Si se va la computadora, el reloj sigue andando, quedan
los últimos datos y aparece "sin conexión" hasta que vuelva.

> Por ahora el celu usa Chrome. Se viene una app de Android de vitrina que va a prender y apagar la
> pantalla del celu junto con tu computadora.

## El panel de Claude

Viene apagado. Con `"claude": true`, el server lee el login que **Claude Code** ya guarda en esta
computadora y le pregunta a Anthropic tu uso cada 5 minutos:

- En macOS el login está en el Llavero; macOS puede preguntarte una vez si lo permitís.
- En Windows se lee de `~/.claude/.credentials.json`.
- El token **nunca sale de tu computadora** y nunca se renueva (renovarlo podría cerrarte la sesión de
  Claude Code). Al celu solo van porcentajes y horarios de reinicio.
- Usa el mismo endpoint **no documentado** que el `/usage` de Claude Code. Puede dejar de andar en
  cualquier momento; si pasa, el panel simplemente desaparece.

## Privacidad

- Con `"wifi": true`, **cualquiera en tu red local puede abrir la página**, fotos incluidas. Usá
  `"wifi": false` en redes en las que no confíes; ahí solo anda por cable.
- El server solo responde pedidos; nunca cambia nada en tu computadora. No expongas su puerto a internet.
- Para el clima solo se manda el nombre de la ciudad a Open-Meteo.

## Fotos

JPEG, PNG y WebP. Las fotos de iPhone en HEIC hay que exportarlas a JPEG primero. Las horizontales ocupan
toda la pantalla; las verticales se ven enteras sobre una copia desenfocada. Si en un celu viejo las fotos
tardan en aparecer, achicalas a unos 1600 px de ancho.

## Desarrollo

```sh
python3 -m unittest
```

Sin dependencias ni build: el server es Python a secas y la página (`web/`) es HTML, CSS y JavaScript.

## Créditos

- Datos del clima de [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0).
- Fuentes: [Big Shoulders Display](https://fonts.google.com/specimen/Big+Shoulders+Display) y
  [Atkinson Hyperlegible Next](https://fonts.google.com/specimen/Atkinson+Hyperlegible+Next), SIL Open
  Font License 1.1 (en `web/fonts/`).

## Licencia

[MIT](LICENSE)
