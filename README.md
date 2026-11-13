# vitrina

*[Leer en castellano](README.es.md)*

Turn an old Android phone into a small desk display. Your computer gathers the data; the phone shows it
full screen, rotating through panels:

- **Clock** with the date and the weather
- **GitHub activity**: the contribution squares, your streak and today's count
- **Claude usage**: current session and weekly limits, with a pace mark (optional)
- **Photos** from a folder on your computer

Free and open source. No accounts, no cloud. The phone runs a small vitrina app that only talks to your
computer, and its screen turns on and off together with it.

## What you need

- A **Mac** with **Python 3.9 or newer**: run `python3 --version` in Terminal; if it's missing, macOS
  offers to install it.
- **adb**, to talk to the phone over USB: `brew install android-platform-tools`.
- An **Android phone** (Android 8 or newer) with USB debugging turned on, on the same Wi‑Fi as the Mac or
  plugged in by USB.
- To install the app, for now from the source: **JDK 17** and the **Android SDK** (Android Studio's, or
  the command-line tools), with `JAVA_HOME` and `ANDROID_HOME` set. Ready-made APKs will come in Releases.

## Quick start

```sh
git clone https://github.com/nicob201/vitrina.git
cd vitrina
python3 server.py              # first run: creates config.json, then says it isn't paired yet
```

Fill in `config.json` (see below). Then, with the phone plugged in by USB:

```sh
(cd android && ./gradlew installDebug)   # installs the vitrina app on the phone
python3 server.py pair                   # the phone says "Paired"
python3 server.py
```

```
vitrina is running
  WiFi:  https://192.168.0.10:8765
  Cable: https://localhost:8765
Press Ctrl+C to stop.
```

vitrina opens on the phone by itself. The first time it walks you through three phone settings so the
screen can follow the Mac: make vitrina the **home screen**, a **screen timeout** of one minute or less,
and **Stay awake** (Developer options) turned off.

## Settings (`config.json`)

| Option | Default | What it does |
|---|---|---|
| `port` | `8765` | Port the server listens on |
| `wifi` | `true` | `false` = only reachable over the USB cable |
| `language` | `"auto"` | `"auto"` follows the phone's language; `"es"` or `"en"` to force one |
| `seconds_per_panel` | `15` | How long each panel stays on screen (5 or more) |
| `github_user` | `""` | Your GitHub username. Empty = no GitHub panel |
| `claude` | `false` | `true` turns on the Claude usage panel (see below) |
| `city` | `""` | City for the weather. Empty = no weather |
| `country` | `""` | Optional two-letter country code to pick the right city, e.g. `"AR"` |
| `units` | `"celsius"` | `"celsius"` or `"fahrenheit"` |
| `photos_dir` | `""` | Folder with photos. Empty = no photo panel |

A panel with nothing to show simply stays out of the rotation. When the server starts it prints which
place it found for your city, so you can check it picked the right one.

## Using the phone

- **Cable or Wi‑Fi.** With the phone plugged in, the server connects it over the cable by itself
  (`USB: phone connected`) and the app prefers it; unplugged, the app uses the Mac's Wi‑Fi address from
  the pairing. The corner of the screen says which one is in use.
- **The screen follows the Mac.** It stays on while vitrina runs on the Mac, turns off about a minute
  after it stops, and turns back on when it starts again. The power button still works.
- **Tap** to jump to the next panel. If the Mac goes away, the clock keeps running, the last data stays
  on screen and an "offline" mark appears until it's back.
- **Hold a finger still for 3 seconds** for the app's settings: change the Mac's Wi‑Fi address (if your
  router gave it another one) or exit to the phone's original home screen. Tip: give your Mac a fixed IP
  in your router so the address doesn't change.
- **macOS with Python from python.org:** run *Install Certificates.command* once (in the Python folder
  under Applications), or GitHub, Claude and the weather can't connect.

## The Claude panel

Off by default. With `"claude": true`, the server reads the login that **Claude Code** already keeps on
this computer and asks Anthropic for your usage every 5 minutes:

- The login lives in the Keychain; macOS may ask once whether to allow it.
- The token **never leaves your computer** and is never refreshed (refreshing could log Claude Code
  out). Only percentages and reset times go to the phone.
- It uses the same **undocumented** endpoint as Claude Code's `/usage`. It may stop working at any
  time; if it does, the panel just disappears.

## Security

- **Closed by default.** Only the paired app sees anything. Everything travels over HTTPS with a
  certificate made on your Mac, which the app recognizes by its fingerprint (it trusts nothing else), and
  every request carries a secret key. Without the key the server answers nothing useful (`401`): not the
  page, not the data, not the photos.
- **Secrets** live in `~/Library/Application Support/vitrina/` (private folder and files), never in the
  repo or in `config.json`. On the phone the key is stored encrypted with the Android Keystore.
- **Pairing only over USB.** Only adb can open the app's pairing screen, so no other app on the phone can
  point vitrina at another server. **Pairing again changes the key**: any phone paired before (a lost
  one, say) is locked out. Restart the server after pairing.
- The page no longer opens in Chrome or any other browser: only the app can show it.
- `"wifi": false` keeps the server off the network entirely; then only the cable works.
- The server never starts by itself, only answers requests and never changes anything on your Mac.
  Don't expose its port to the internet.
- The weather lookup sends only the city name to Open-Meteo.

## Photos

JPEG, PNG and WebP. iPhone photos in HEIC need to be exported as JPEG first. Landscape photos fill the
screen; portrait ones are shown whole over a blurred copy. If photos are slow to appear on an older
phone, resize them to about 1600 px wide.

## Development

```sh
python3 -m unittest                         # server
(cd android && ./gradlew testDebugUnitTest) # app logic
```

The server has no dependencies and no build step: plain Python, and the page (`web/`) is plain HTML, CSS
and JavaScript. The app (`android/`) is Kotlin on Android's own APIs only: no third-party libraries.

## Credits

- Weather data by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0).
- Fonts: [Big Shoulders Display](https://fonts.google.com/specimen/Big+Shoulders+Display) and
  [Atkinson Hyperlegible Next](https://fonts.google.com/specimen/Atkinson+Hyperlegible+Next), SIL Open
  Font License 1.1 (in `web/fonts/`).

## License

[MIT](LICENSE)
