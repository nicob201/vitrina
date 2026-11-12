# vitrina

*[Leer en castellano](README.es.md)*

Turn an old Android phone into a small desk display. Your computer gathers the data; the phone shows it
full screen, rotating through panels:

- **Clock** with the date and the weather
- **GitHub activity**: the contribution squares, your streak and today's count
- **Claude usage**: current session and weekly limits, with a pace mark (optional)
- **Photos** from a folder on your computer

Free and open source. No accounts, no cloud, nothing to install beyond Python.

## What you need

- A computer with **macOS or Windows** and **Python 3.9 or newer**.
  - macOS: run `python3 --version` in Terminal; if it's missing, macOS offers to install it.
  - Windows: install it from [python.org](https://www.python.org/downloads/).
- An **Android phone** with Chrome, on the same Wi‑Fi as the computer or plugged in by USB.

## Quick start

```sh
git clone https://github.com/nicob201/vitrina.git
cd vitrina
python3 server.py
```

The first run creates `config.json`. Fill it in (see below) and start the server again. It prints the
addresses to open on the phone:

```
vitrina is running
  WiFi:  http://192.168.0.10:8765
  Cable: http://localhost:8765
Press Ctrl+C to stop.
```

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

## Connecting the phone

**Over Wi‑Fi.** Open the `WiFi:` address in Chrome on the phone and tap the screen once to go full
screen. Tip: give your computer a fixed IP in your router so the address doesn't change.

- **Keep the screen on:** over Wi‑Fi, Chrome isn't allowed to keep the screen awake. On the phone, turn on
  Developer options → **Stay awake** (the screen stays on while charging).
- **Windows:** the first time, the firewall asks about Python. Allow it on **private networks**, or the
  phone won't reach it.
- **macOS with Python from python.org:** run *Install Certificates.command* once (in the Python folder
  under Applications), or GitHub, Claude and the weather can't connect.

**Over the cable.** Install [adb](https://developer.android.com/tools/releases/platform-tools), turn on
USB debugging on the phone and plug it in. The server notices (`USB: phone connected`) and sets up the
connection by itself; open `http://localhost:8765` on the phone.

Tap the screen to jump to the next panel. If the computer goes away, the clock keeps running, the last
data stays on screen and an "offline" mark appears until it's back.

> For now the phone uses Chrome. A small vitrina Android app is on the way: it will turn the phone's
> screen on and off together with your computer.

## The Claude panel

Off by default. With `"claude": true`, the server reads the login that **Claude Code** already keeps on
this computer and asks Anthropic for your usage every 5 minutes:

- On macOS the login lives in the Keychain; macOS may ask once whether to allow it.
- On Windows it's read from `~/.claude/.credentials.json`.
- The token **never leaves your computer** and is never refreshed (refreshing could log Claude Code
  out). Only percentages and reset times go to the phone.
- It uses the same **undocumented** endpoint as Claude Code's `/usage`. It may stop working at any
  time; if it does, the panel just disappears.

## Privacy

- With `"wifi": true`, **anyone on your local network can open the page**, photos included. Use
  `"wifi": false` on networks you don't trust; then only the cable works.
- The server only answers requests; it never changes anything on your computer. Don't expose its port
  to the internet.
- The weather lookup sends only the city name to Open-Meteo.

## Photos

JPEG, PNG and WebP. iPhone photos in HEIC need to be exported as JPEG first. Landscape photos fill the
screen; portrait ones are shown whole over a blurred copy. If photos are slow to appear on an older
phone, resize them to about 1600 px wide.

## Development

```sh
python3 -m unittest
```

No dependencies, no build step: the server is plain Python and the page (`web/`) is plain HTML, CSS and
JavaScript.

## Credits

- Weather data by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0).
- Fonts: [Big Shoulders Display](https://fonts.google.com/specimen/Big+Shoulders+Display) and
  [Atkinson Hyperlegible Next](https://fonts.google.com/specimen/Atkinson+Hyperlegible+Next), SIL Open
  Font License 1.1 (in `web/fonts/`).

## License

[MIT](LICENSE)
