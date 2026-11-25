# vitrina

*[Read in English](README.md)*

Convertí un celular Android viejo en una mini pantalla de escritorio. La computadora junta los datos y
el celu los muestra a pantalla completa, rotando entre paneles:

- **Hora** con la fecha y el clima
- **Actividad en GitHub**: los cuadraditos de contribuciones, tu racha y lo de hoy
- **Uso de Claude**: sesión actual y límite semanal, con marca de ritmo (opcional)
- **Mac**: CPU, GPU, memoria y red de los últimos 5 minutos, más disco y batería (opcional)
- **Fotos** de una carpeta de tu computadora

Gratis y open source. Sin cuentas, sin nube. El celu usa una pequeña app de vitrina que solo habla con tu
computadora, y su pantalla se prende y se apaga junto con ella.

**Sitio web:** [vitrina.nicolasboscasso.workers.dev](https://vitrina.nicolasboscasso.workers.dev) — mirala andando y seguí una guía corta de instalación.

## Qué necesitás

- Una **Mac** con **Python 3.9 o más nuevo**: corré `python3 --version` en la Terminal; si no está,
  macOS te ofrece instalarlo.
- **adb**, para hablar con el celu por USB: `brew install android-platform-tools`.
- Un **celular Android** (Android 8 o más nuevo) con la depuración USB activada, en el mismo WiFi que la
  Mac o enchufado por USB.

## Arranque rápido

```sh
git clone https://github.com/nicob201/vitrina.git
cd vitrina
mkdir -p ~/.local/bin && ln -s "$PWD/server.py" ~/.local/bin/vitrina   # el comando `vitrina`, en cualquier carpeta
```

Si `~/.local/bin` todavía no está en tu PATH, agregalo y abrí una terminal nueva:

```sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
```

Después corré `vitrina`. La primera vez crea `config.json` y avisa que falta emparejar:

```sh
vitrina
```

Completá `config.json` (ver abajo). Bajá `vitrina-1.0.0.apk` del
[último release](https://github.com/nicob201/vitrina/releases/latest), comprobalo con el SHA-256 de las notas
del release y, con el celu enchufado por USB, instalalo y emparejá:

```sh
shasum -a 256 vitrina-1.0.0.apk          # tiene que coincidir con las notas del release
adb install vitrina-1.0.0.apk            # instala la app de vitrina en el celu
vitrina pair                             # el celu dice "Emparejado"
vitrina start                            # arranca en segundo plano
```

```
vitrina is running
  WiFi:  https://192.168.0.10:8765
  Cable: https://localhost:8765
To stop it: vitrina stop
Log: /Users/vos/Library/Application Support/vitrina/server.log
```

vitrina se abre sola en el celu. La primera vez te guía por los ajustes del celu que hacen falta para
que la pantalla siga a la Mac: vitrina como **pantalla de inicio**, **tiempo de pantalla** de un minuto o
menos, **Permanecer activo** (Opciones para desarrolladores) apagado y, en versiones nuevas de Android,
permiso para sus notificaciones.

## Arrancar y frenar

Sin el enlace de `vitrina` (ver Arranque rápido), `python3 server.py <comando>` desde la carpeta del proyecto
hace lo mismo.

| Comando | Qué hace |
|---|---|
| `vitrina start` | Arranca en segundo plano. Podés cerrar la terminal. |
| `vitrina stop` | Lo frena, esté donde esté corriendo: libera el puerto y saca la conexión por cable, y si el que abrió `adb` fue vitrina, también lo cierra. La pantalla del celu se apaga sola. |
| `vitrina` | Lo corre en primer plano, con los mensajes a la vista. Ctrl+C lo frena. |
| `vitrina pair` | Empareja el celu (ver arriba). |

En segundo plano los mensajes van a `~/Library/Application Support/vitrina/server.log`.

**Si la Mac durmió más de una hora, vitrina se frena sola** apenas despierta: la Mac pudo cambiar de red (de tu
casa a un café) y vitrina no vuelve a escuchar ahí. Corré `vitrina start` de nuevo. Si duerme menos, sigue como
estaba y el celu se prende solo. Nada arranca solo: vitrina corre solo cuando vos la arrancás.

## Configuración (`config.json`)

| Opción | Por defecto | Qué hace |
|---|---|---|
| `port` | `8765` | Puerto donde escucha el server |
| `wifi` | `true` | `false` = solo se puede usar por cable USB |
| `language` | `"auto"` | `"auto"` sigue el idioma del celu; `"es"` o `"en"` para forzarlo |
| `seconds_per_panel` | `15` | Cuánto queda cada panel en pantalla (5 o más) |
| `github_user` | `""` | Tu usuario de GitHub. Vacío = sin panel de GitHub |
| `claude` | `false` | `true` activa el panel de uso de Claude (ver abajo) |
| `mac` | `false` | `true` activa el panel de la Mac (ver abajo) |
| `city` | `""` | Ciudad para el clima. Vacío = sin clima |
| `country` | `""` | Código de país de dos letras, opcional, para elegir bien la ciudad. Ej.: `"AR"` |
| `units` | `"celsius"` | `"celsius"` o `"fahrenheit"` |
| `photos_dir` | `""` | Carpeta de fotos. Vacío = sin panel de fotos. Ej.: `"~/Pictures/vitrina"` |

Un panel sin nada para mostrar queda afuera de la rotación. Al arrancar, el server muestra qué lugar
encontró para tu ciudad, así ves que eligió el correcto.

## Usar el celu

- **Cable o WiFi.** Con el celu enchufado, el server lo conecta por cable solo (`USB: phone connected`) y
  la app lo prefiere; desenchufado, la app usa la dirección WiFi de la Mac que recibió al emparejar. La
  esquina de la pantalla dice cuál está usando.
- **La pantalla sigue a la Mac.** Queda prendida mientras vitrina corre en la Mac, se apaga más o menos
  un minuto después de que se corta y se vuelve a prender cuando arranca. El botón de encendido sigue
  andando.
- **Después de reiniciar el celu** vitrina vuelve sola; si el celu tiene PIN o patrón, cuando lo
  desbloqueás.
- **Tocá** para pasar al panel siguiente. Si se va la Mac, el reloj sigue andando, quedan los últimos
  datos y aparece "sin conexión" hasta que vuelva.
- **Dejá el dedo quieto 3 segundos** para los ajustes de la app: cambiar la dirección WiFi de la Mac (si
  el router le dio otra) o salir a la pantalla de inicio original del celu. Consejo: fijá la IP de tu Mac
  en el router para que la dirección no cambie.
- **macOS con Python de python.org:** corré una vez *Install Certificates.command* (en la carpeta de
  Python dentro de Aplicaciones), o GitHub, Claude y el clima no van a poder conectarse.

## El panel de Claude

Viene apagado. Con `"claude": true`, el server lee el login que **Claude Code** ya guarda en esta
computadora y le pregunta a Anthropic tu uso cada 5 minutos:

- El login está en el Llavero; macOS puede preguntarte una vez si lo permitís.
- El token **nunca sale de tu computadora** y nunca se renueva (renovarlo podría cerrarte la sesión de
  Claude Code). Al celu solo van porcentajes y horarios de reinicio.
- Usa el mismo endpoint **no documentado** que el `/usage` de Claude Code. Puede dejar de andar en
  cualquier momento; si pasa, el panel simplemente desaparece.

## El panel de la Mac

Apagado de entrada. Con `"mac": true`, el server lee qué tan ocupada está la Mac: CPU, GPU, memoria y red
cada 5 segundos, y espacio en disco y batería cada media hora.

- Le pregunta directo a macOS, sin `sudo` ni programas extra: cada lectura tarda mucho menos de un
  milisegundo.
- Corre solo mientras vitrina corre (`vitrina stop` la corta) y se pausa si el celu no consultó nada en un
  minuto.
- La Mac guarda los últimos 5 minutos; el celu los pide solo con el panel en pantalla y hace todo el
  dibujo. Al celu llegan porcentajes, velocidades, espacio en disco, batería y el nombre de la Mac: ningún
  nombre de proceso ni de archivo.

## Seguridad

- **Cerrado de entrada.** Solo la app emparejada ve algo. Todo viaja por HTTPS con un certificado hecho
  en tu Mac, que la app reconoce por su huella (no confía en ningún otro), y cada pedido lleva una clave
  secreta. Sin la clave el server no responde nada útil (`401`): ni la página, ni los datos, ni las fotos.
- **Los secretos** se guardan en `~/Library/Application Support/vitrina/` (carpeta y archivos privados),
  nunca en el repo ni en `config.json`. En el celu la clave se guarda solo cifrada con el Keystore de
  Android: la app hace ella misma cada pedido de la página y manda la clave en un header, así que nunca queda
  en una cookie. Los datos de la app quedan fuera de los backups y de las transferencias entre celus.
- **Emparejar es solo por adb** (USB, o la depuración inalámbrica de Android). Solo adb puede abrir la
  pantalla de emparejar de la app, así ninguna otra app del celu puede apuntar vitrina a otro server.
  **Emparejar de nuevo cambia la clave**: cualquier celu emparejado antes (uno perdido, por ejemplo) queda
  afuera. Después de emparejar, reiniciá el server.
- La página ya no se abre en Chrome ni en ningún otro navegador: solo la puede mostrar la app.
- `"wifi": false` deja el server fuera de la red; ahí solo anda por cable.
- El server nunca arranca solo, solo responde pedidos y nunca cambia nada en tu Mac. No expongas su
  puerto a internet.
- Para el clima solo se manda el nombre de la ciudad a Open-Meteo.

## Fotos

JPEG, PNG y WebP. Las fotos de iPhone en HEIC hay que exportarlas a JPEG primero. Las horizontales ocupan
toda la pantalla; las verticales se ven enteras sobre una copia desenfocada. Un celu viejo no puede mostrar
fotos muy grandes (de más de unos 4000 px, como las de 50 MP): se ven cortadas. Achicalas antes; en la Mac,
`sips -Z 1600 foto.jpg` la achica en el lugar para que su lado más largo mida 1600 px.

## Hacela tuya

vitrina es MIT: podés copiarla, modificarla y repartirla, así que cambiale el estilo a tu gusto. Lo que
muestra el celu es una página común (HTML, CSS y JavaScript) en `web/`, y el server la lee del disco en cada
pedido:

- **Colores:** las variables del principio de `web/styles.css` (`:root`): el fondo, los textos, los verdes de
  GitHub y la paleta del panel de Claude.
- **Fuentes:** cambiá los archivos de `web/fonts/` y las dos reglas `@font-face` y las variables `--display` y
  `--text` de `web/styles.css`. Las fuentes que trae vitrina tienen su propia licencia (SIL OFL, en
  `web/fonts/`); si usás otras, fijate la suya.
- **Verlo:** reabrí vitrina en el celu para cargar el cambio.

Esto no cambia las pantallas propias de la app Android (emparejar, ajustes). Para seguir recibiendo mejoras sin
conflictos, trabajá en un fork o en una rama.

## Desarrollo

```sh
python3 -m unittest                         # server
(cd android && ./gradlew testDebugUnitTest) # lógica de la app
```

Para compilar la app desde el código en vez de usar el release hacen falta **JDK 17** y el **SDK de Android**
(el de Android Studio o las herramientas de línea de comandos), con `JAVA_HOME` y `ANDROID_HOME` configurados:

```sh
(cd android && ./gradlew installDebug)   # compila e instala una versión debug en el celu enchufado
```

Una versión debug y el APK del release están firmados con claves distintas, así que ninguna reemplaza a la
otra: desinstalá antes la app del celu (`adb uninstall io.github.nicob201.vitrina`).

El server no tiene dependencias ni build: Python a secas, y la página (`web/`) es HTML, CSS y JavaScript.
La app (`android/`) es Kotlin con las APIs propias de Android: ninguna librería de terceros.

El sitio web vive en `website/`: `python3 website/build.py` lo arma en `dist/`, y la demo en vivo es la página
real de `web/` con datos de ejemplo.

## Créditos

- Datos del clima de [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0).
- Fuentes: [Big Shoulders Display](https://fonts.google.com/specimen/Big+Shoulders+Display) y
  [Atkinson Hyperlegible Next](https://fonts.google.com/specimen/Atkinson+Hyperlegible+Next), SIL Open
  Font License 1.1 (en `web/fonts/`).
- Fotos de la demo del sitio: dominio público (CC0) de Wikimedia Commons; autores en
  `website/demo-photos/SOURCES.tsv`.

## Licencia

[MIT](LICENSE)
