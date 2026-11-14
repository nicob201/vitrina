# vitrina

*[Read in English](README.md)*

Convertí un celular Android viejo en una mini pantalla de escritorio. La computadora junta los datos y
el celu los muestra a pantalla completa, rotando entre paneles:

- **Hora** con la fecha y el clima
- **Actividad en GitHub**: los cuadraditos de contribuciones, tu racha y lo de hoy
- **Uso de Claude**: sesión actual y límite semanal, con marca de ritmo (opcional)
- **Fotos** de una carpeta de tu computadora

Gratis y open source. Sin cuentas, sin nube. El celu usa una pequeña app de vitrina que solo habla con tu
computadora, y su pantalla se prende y se apaga junto con ella.

## Qué necesitás

- Una **Mac** con **Python 3.9 o más nuevo**: corré `python3 --version` en la Terminal; si no está,
  macOS te ofrece instalarlo.
- **adb**, para hablar con el celu por USB: `brew install android-platform-tools`.
- Un **celular Android** (Android 8 o más nuevo) con la depuración USB activada, en el mismo WiFi que la
  Mac o enchufado por USB.
- Para instalar la app, por ahora desde el código: **JDK 17** y el **SDK de Android** (el de Android
  Studio o las herramientas de línea de comandos), con `JAVA_HOME` y `ANDROID_HOME` configurados. Los APK
  listos van a llegar en Releases.

## Arranque rápido

```sh
git clone https://github.com/nicob201/vitrina.git
cd vitrina
python3 server.py              # la primera vez crea config.json y avisa que falta emparejar
```

Completá `config.json` (ver abajo). Después, con el celu enchufado por USB:

```sh
(cd android && ./gradlew installDebug)   # instala la app de vitrina en el celu
python3 server.py pair                   # el celu dice "Emparejado"
python3 server.py
```

```
vitrina is running
  WiFi:  https://192.168.0.10:8765
  Cable: https://localhost:8765
Press Ctrl+C to stop.
```

vitrina se abre sola en el celu. La primera vez te guía por los ajustes del celu que hacen falta para
que la pantalla siga a la Mac: vitrina como **pantalla de inicio**, **tiempo de pantalla** de un minuto o
menos, **Permanecer activo** (Opciones para desarrolladores) apagado y, en versiones nuevas de Android,
permiso para sus notificaciones.

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

## Seguridad

- **Cerrado de entrada.** Solo la app emparejada ve algo. Todo viaja por HTTPS con un certificado hecho
  en tu Mac, que la app reconoce por su huella (no confía en ningún otro), y cada pedido lleva una clave
  secreta. Sin la clave el server no responde nada útil (`401`): ni la página, ni los datos, ni las fotos.
- **Los secretos** se guardan en `~/Library/Application Support/vitrina/` (carpeta y archivos privados),
  nunca en el repo ni en `config.json`. En el celu la clave se guarda cifrada con el Keystore de Android;
  además, la vista web de la app guarda una copia en su propio almacén privado de cookies. Los datos de la
  app quedan fuera de los backups y de las transferencias entre celus.
- **Emparejar es solo por adb** (USB, o la depuración inalámbrica de Android). Solo adb puede abrir la
  pantalla de emparejar de la app, así ninguna otra app del celu puede apuntar vitrina a otro server. **Emparejar de nuevo cambia la clave**: cualquier
  celu emparejado antes (uno perdido, por ejemplo) queda afuera. Después de emparejar, reiniciá el server.
- La página ya no se abre en Chrome ni en ningún otro navegador: solo la puede mostrar la app.
- `"wifi": false` deja el server fuera de la red; ahí solo anda por cable.
- El server nunca arranca solo, solo responde pedidos y nunca cambia nada en tu Mac. No expongas su
  puerto a internet.
- Para el clima solo se manda el nombre de la ciudad a Open-Meteo.

## Fotos

JPEG, PNG y WebP. Las fotos de iPhone en HEIC hay que exportarlas a JPEG primero. Las horizontales ocupan
toda la pantalla; las verticales se ven enteras sobre una copia desenfocada. Si en un celu viejo las fotos
tardan en aparecer, achicalas a unos 1600 px de ancho.

## Desarrollo

```sh
python3 -m unittest                         # server
(cd android && ./gradlew testDebugUnitTest) # lógica de la app
```

El server no tiene dependencias ni build: Python a secas, y la página (`web/`) es HTML, CSS y JavaScript.
La app (`android/`) es Kotlin con las APIs propias de Android: ninguna librería de terceros.

## Créditos

- Datos del clima de [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0).
- Fuentes: [Big Shoulders Display](https://fonts.google.com/specimen/Big+Shoulders+Display) y
  [Atkinson Hyperlegible Next](https://fonts.google.com/specimen/Atkinson+Hyperlegible+Next), SIL Open
  Font License 1.1 (en `web/fonts/`).

## Licencia

[MIT](LICENSE)
