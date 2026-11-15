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

## Quick start

```sh
git clone https://github.com/nicob201/vitrina.git
cd vitrina
mkdir -p ~/.local/bin && ln -s "$PWD/server.py" ~/.local/bin/vitrina   # the `vitrina` command, in any folder
```

If `~/.local/bin` isn't in your PATH yet, add it and open a new terminal:

```sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
```

Then run `vitrina` (in a terminal where the command isn't found yet, `python3 server.py` does the same). The
first run creates `config.json` and says it isn't paired yet:

```sh
vitrina
```

Fill in `config.json` (see below). Download `vitrina-1.0.0.apk` from the
[latest release](https://github.com/nicob201/vitrina/releases/latest), check it against the SHA-256 in the
release notes, and, with the phone plugged in by USB, install it and pair:

```sh
shasum -a 256 vitrina-1.0.0.apk          # must match the release notes
adb install vitrina-1.0.0.apk            # installs the vitrina app on the phone
vitrina pair                             # the phone says "Paired"
vitrina start                            # runs in the background
```

```
vitrina is running
  WiFi:  https://192.168.0.10:8765
  Cable: https://localhost:8765
To stop it: vitrina stop
Log: /Users/you/Library/Application Support/vitrina/server.log
```

vitrina opens on the phone by itself. The first time it walks you through the phone settings the screen
needs to follow the Mac: make vitrina the **home screen**, a **screen timeout** of one minute or less,
**Stay awake** (Developer options) turned off and, on newer Android versions, permission for its
notifications.

## Starting and stopping

Without the `vitrina` link (see Quick start), `python3 server.py <command>` from the project folder does the same.

| Command | What it does |
|---|---|
| `vitrina start` | Starts in the background. You can close the terminal. |
| `vitrina stop` | Stops it wherever it's running: frees the port and drops the cable link, and if vitrina was the one that opened `adb`, closes it too. The phone's screen turns off by itself. |
| `vitrina` | Runs it in the foreground, messages in view. Ctrl+C stops it. |
| `vitrina pair` | Pairs the phone (see above). |

In the background, messages go to `~/Library/Application Support/vitrina/server.log`.

**If the Mac slept for more than an hour, vitrina stops by itself** as soon as it wakes: the Mac may be on
another network (from home to a café) and vitrina won't come back listening there. Run `vitrina start` again.
After a shorter sleep it carries on and the phone turns on by itself. Nothing starts on its own: vitrina only
runs when you start it.

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
| `photos_dir` | `""` | Folder with photos. Empty = no photo panel. E.g.: `"~/Pictures/vitrina"` |

A panel with nothing to show simply stays out of the rotation. When the server starts it prints which
place it found for your city, so you can check it picked the right one.

## Using the phone

- **Cable or Wi‑Fi.** With the phone plugged in, the server connects it over the cable by itself
  (`USB: phone connected`) and the app prefers it; unplugged, the app uses the Mac's Wi‑Fi address from
  the pairing. The corner of the screen says which one is in use.
- **The screen follows the Mac.** It stays on while vitrina runs on the Mac, turns off about a minute
  after it stops, and turns back on when it starts again. The power button still works.
- **After the phone restarts** vitrina comes back by itself; if the phone has a PIN or pattern, once you
  unlock it.
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
  repo or in `config.json`. On the phone the key is stored only encrypted with the Android Keystore: the
  app makes every request for its page itself and sends the key as a header, so it never sits in a cookie.
  The app's data is left out of backups and phone-to-phone transfers.
- **Pairing only through adb** (USB, or Android's wireless debugging). Only adb can open the app's pairing
  screen, so no other app on the phone can point vitrina at another server. **Pairing again changes the
  key**: any phone paired before (a lost one, say) is locked out. Restart the server after pairing.
- The page no longer opens in Chrome or any other browser: only the app can show it.
- `"wifi": false` keeps the server off the network entirely; then only the cable works.
- The server never starts by itself, only answers requests and never changes anything on your Mac.
  Don't expose its port to the internet.
- The weather lookup sends only the city name to Open-Meteo.

## Photos

JPEG, PNG and WebP. iPhone photos in HEIC need to be exported as JPEG first. Landscape photos fill the
screen; portrait ones are shown whole over a blurred copy. An older phone can't show very large photos
(over about 4000 px, like 50 MP shots): they appear cut off. Resize them first; on a Mac,
`sips -Z 1600 photo.jpg` shrinks one in place so its longest side is 1600 px.

## Development

```sh
python3 -m unittest                         # server
(cd android && ./gradlew testDebugUnitTest) # app logic
```

To build the app from source instead of using the release you need **JDK 17** and the **Android SDK**
(Android Studio's, or the command-line tools), with `JAVA_HOME` and `ANDROID_HOME` set:

```sh
(cd android && ./gradlew installDebug)   # builds and installs a debug build on the plugged-in phone
```

A debug build and the release APK are signed with different keys, so neither can replace the other:
uninstall the app from the phone first (`adb uninstall io.github.nicob201.vitrina`).

The server has no dependencies and no build step: plain Python, and the page (`web/`) is plain HTML, CSS
and JavaScript. The app (`android/`) is Kotlin on Android's own APIs only: no third-party libraries.

## Credits

- Weather data by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0).
- Fonts: [Big Shoulders Display](https://fonts.google.com/specimen/Big+Shoulders+Display) and
  [Atkinson Hyperlegible Next](https://fonts.google.com/specimen/Atkinson+Hyperlegible+Next), SIL Open
  Font License 1.1 (in `web/fonts/`).

## License

[MIT](LICENSE)
