# vitrina v1.0.0 Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship vitrina as v1.0.0: `vitrina` commands in every user-facing text, a release-signed APK verified on the
Nokia, the repo public with secret scanning, and a GitHub release carrying the APK and its SHA-256.

**Architecture:** No new code paths. Message strings change (server + app), Gradle gains an optional release
signing config fed by environment variables, the key lives outside the repo, and the release is published with `gh`.

**Tech Stack:** Python 3.9+ stdlib (server), Kotlin + AGP 9.5.1 (app), `keytool`/`apksigner` from `.tools/`, `gh`.

**Spec:** `docs/superpowers/specs/2026-11-12-vitrina-design.md` §8d (and §8c for the `vitrina` command).

## Global Constraints

- Commits: conventional, in English, **no trailer of any kind** (no Co-Authored-By, no "Generated with").
- No new dependencies, server or app.
- Android toolchain only from the project: `source .tools/env.sh` before any Gradle, `keytool` or `apksigner` call.
- The signing key and its password never enter the repo, a commit, a log, or GitHub.
- User-facing commands are `vitrina start`, `vitrina stop`, `vitrina pair`; the README keeps the
  `python3 server.py ...` equivalent for anyone without `~/.local/bin` in their PATH.
- App version: `versionName "1.0.0"`, `versionCode 1`. Release asset: `vitrina-1.0.0.apk`. Tag: `v1.0.0` (annotated).
- Work on branch `chore/v1-release`, merged into `main` with `--no-ff` like the earlier plans.
- **Stop after Task 4.** Task 5 (merge, push, public, release) starts only after the user says the audit of
  Tasks 1–4 (done in another session) passed. Even then, ask the user before making the repo public and before
  pushing the tag / publishing the release.

## Review Focus

1. A contributor without the key builds and tests the app → nothing asks for a key (`testDebugUnitTest` and
   `assembleRelease` both succeed with no `VITRINA_*` variables; release comes out unsigned). Checked in Task 3.
2. Phone in Spanish → the Spanish strings say `vitrina start` / `vitrina pair` too. Checked in Task 2 by grep.
3. Someone without `~/.local/bin` in PATH → README says how to add it and gives the `python3 server.py` equivalent. Task 4.
4. Installing the release APK over the debug build → `INSTALL_FAILED_UPDATE_INCOMPATIBLE`; uninstall first. Task 3 step.
5. The release build (not debug) still pins the certificate and turns the screen on/off → checked on the Nokia in Task 3.

---

### Task 1: Server messages use the `vitrina` command

**Files:**
- Modify: `vitrina/app.py:37,60,69,111`
- Modify (doc comments only): `android/app/src/main/java/io/github/nicob201/vitrina/Pairing.kt:5`, `PairActivity.kt:16`
- Test: `tests/test_app.py:88,97,105,135,234`

- [ ] **Step 1: Update the assertions first**

In `tests/test_app.py`: the three `assertIn("python3 server.py pair", out)` become `assertIn("vitrina pair", out)`;
both `"Usage: python3 server.py [start | stop | pair]"` become `"Usage: vitrina [start | stop | pair]"`. Add to
`test_long_sleep_stops_and_releases_everything` (it runs the real server and captures its output):
`self.assertIn("To stop it: vitrina stop", out)`.

- [ ] **Step 2: Run and see them fail**

Run: `python3 -m unittest tests.test_app`
Expected: 6 failures, all on the changed strings.

- [ ] **Step 3: Change the four messages in `vitrina/app.py`**

`Usage: vitrina [start | stop | pair]`, `Not paired yet. Plug in the phone and run: vitrina pair`,
`Can't read the certificate. Plug in the phone and run: vitrina pair`, `To stop it: vitrina stop`.
Doc comments in `Pairing.kt` and `PairActivity.kt`: `` `python3 server.py pair` `` → `` `vitrina pair` ``.

- [ ] **Step 4: Run the whole server suite**

Run: `python3 -m unittest`
Expected: OK, no failures. `grep -rn "python3 server.py" vitrina tests android/app/src` prints nothing.

- [ ] **Step 5: Commit**

```bash
git add vitrina/app.py tests/test_app.py android/app/src/main/java
git commit -m "fix: point every hint at the vitrina command"
```

### Task 2: App texts, version 1.0.0, example IP in the test

**Files:**
- Modify: `android/app/src/main/res/values/strings.xml:9,10,12`, `android/app/src/main/res/values-es/strings.xml:8,9,11`
- Modify: `android/app/build.gradle.kts` (`versionName`)
- Modify: `android/app/src/test/java/io/github/nicob201/vitrina/PairingTest.kt:43`

- [ ] **Step 1: Strings** — in both languages, `python3 server.py pair` → `vitrina pair` and the waiting text's
`python3 server.py` → `vitrina start` (en: "Start vitrina on the Mac: vitrina start"; es: "Arrancá vitrina en la
Mac: vitrina start"). Nothing else in those strings changes.
- [ ] **Step 2: Version** — `versionName = "1.0.0"`; `versionCode` stays `1`.
- [ ] **Step 3: Test IP** — `"192.168.100.233"` → `"192.168.1.20"` (a private example, same shape).
- [ ] **Step 4: Verify**

Run: `source .tools/env.sh && (cd android && ./gradlew testDebugUnitTest)` → BUILD SUCCESSFUL.
Run: `grep -rn "python3\|192.168.100" android/app/src` → nothing.

- [ ] **Step 5: Commit**

```bash
git add android/app
git commit -m "feat(android): version 1.0.0 and the vitrina command in its hints"
```

### Task 3: Release signing, the APK, and the check on the Nokia

**Files:**
- Modify: `android/app/build.gradle.kts`
- Outside the repo: `~/Library/Application Support/vitrina-release/vitrina-release.jks`, Keychain item `vitrina-release`

**Interfaces:**
- Produces: env vars `VITRINA_KEYSTORE` (path) and `VITRINA_KEYSTORE_PASSWORD`; key alias `vitrina`;
  `android/app/build/outputs/apk/release/app-release.apk`, copied to `android/app/build/vitrina-1.0.0.apk` for Task 5.

- [ ] **Step 1: Optional signing config in `android/app/build.gradle.kts`**

Read both variables with `providers.environmentVariable(...).orNull`. Only when `VITRINA_KEYSTORE` is set,
`signingConfigs.create("release")` with that `storeFile`, the password for both `storePassword` and `keyPassword`
(PKCS12 uses one), `keyAlias = "vitrina"`; then `buildTypes.release.signingConfig` points at it. Unset → no
signing config, release builds unsigned. (`*.jks`/`*.keystore` are already in `android/.gitignore`.)

- [ ] **Step 2: Builds without the key still work**

Run: `source .tools/env.sh && (cd android && ./gradlew testDebugUnitTest assembleRelease)`
Expected: BUILD SUCCESSFUL; `android/app/build/outputs/apk/release/app-release-unsigned.apk` exists.

- [ ] **Step 3: Commit**

```bash
git add android/app/build.gradle.kts
git commit -m "build(android): sign release builds when a key is provided"
```

- [ ] **Step 4: Make the key (once, outside the repo)**

```bash
D="$HOME/Library/Application Support/vitrina-release"; mkdir -p "$D" && chmod 700 "$D"
security add-generic-password -a vitrina -s vitrina-release -w "$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"
export VITRINA_KEYSTORE_PASSWORD="$(security find-generic-password -a vitrina -s vitrina-release -w)"
keytool -genkeypair -keystore "$D/vitrina-release.jks" -storetype PKCS12 -alias vitrina -keyalg RSA -keysize 4096 \
  -validity 10000 -dname "CN=vitrina" -storepass:env VITRINA_KEYSTORE_PASSWORD
chmod 600 "$D/vitrina-release.jks"
```
Expected: the `.jks` exists with `-rw-------`; nothing printed the password.

- [ ] **Step 5: Build and verify the signed APK**

```bash
source .tools/env.sh
export VITRINA_KEYSTORE="$HOME/Library/Application Support/vitrina-release/vitrina-release.jks"
export VITRINA_KEYSTORE_PASSWORD="$(security find-generic-password -a vitrina -s vitrina-release -w)"
(cd android && ./gradlew clean assembleRelease)
"$ANDROID_HOME/build-tools/37.0.0/apksigner" verify --print-certs android/app/build/outputs/apk/release/app-release.apk
cp android/app/build/outputs/apk/release/app-release.apk android/app/build/vitrina-1.0.0.apk
shasum -a 256 android/app/build/vitrina-1.0.0.apk
```
Expected: `Signer #1 certificate DN: CN=vitrina`, verified with v2 (v3 on newer Android); SHA-256 printed.

- [ ] **Step 6: On the Nokia (adb over wireless debugging)**

`adb uninstall io.github.nicob201.vitrina` (the debug build has another signature), then
`adb install android/app/build/vitrina-1.0.0.apk`, `python3 server.py pair` (phone says "Emparejado"),
`vitrina start`. Check, with `adb exec-out screencap -p` captures: panels rotate; `vitrina stop` → screen goes off
within about a minute; `vitrina start` → screen comes back. Stop the server afterwards.

### Task 4: README (en + es)

**Files:**
- Modify: `README.md`, `README.es.md`

- [ ] **Step 1: "What you need" / "Qué necesitás"** — drop the JDK/SDK bullet and "Ready-made APKs will come in
Releases"; keep Mac + Python, adb, Android phone.
- [ ] **Step 2: Quick start / Arranque rápido** — order: clone; link the `vitrina` command
(`mkdir -p ~/.local/bin && ln -s "$PWD/server.py" ~/.local/bin/vitrina`, and if `~/.local/bin` isn't in PATH:
`echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc`, then open a new terminal); `vitrina` (creates
config.json); download `vitrina-1.0.0.apk` from the latest release, check `shasum -a 256 vitrina-1.0.0.apk`
against the release notes, `adb install vitrina-1.0.0.apk`; `vitrina pair`; `vitrina start`. The sample output
says `To stop it: vitrina stop`.
- [ ] **Step 3: "Starting and stopping"** — the link step moves to Quick start; this section keeps the table and
one line: without the link, `python3 server.py <command>` from the project folder does the same.
- [ ] **Step 4: Development / Desarrollo** — building the app from source: JDK 17 + Android SDK with
`JAVA_HOME`/`ANDROID_HOME`, `(cd android && ./gradlew installDebug)`; a debug build and a release APK can't
replace each other (uninstall first).
- [ ] **Step 5: Verify** — `grep -n "python3 server.py" README*.md` only hits the "equivalent" line and the
first-run fallback; both READMEs have the same sections in the same order.
- [ ] **Step 6: Commit**

```bash
git add README.md README.es.md
git commit -m "docs: install the app from the release and use the vitrina command"
```

### Task 5: Merge, go public, release

- [ ] **Step 1: Audit** — done by the user's other session on the whole branch (`git diff main...chore/v1-release`);
fix what it finds; `python3 -m unittest` and `./gradlew testDebugUnitTest` green. Don't start Step 2 before it passes.
- [ ] **Step 2: Merge and push** — `git checkout main && git merge --no-ff chore/v1-release && git push`,
delete the branch.
- [ ] **Step 3: Issues** — one issue per deferred minor (English, no labels): stop's timeout shorter than the
worst-case cleanup; a second signal during cleanup; a lock that's None after binding; a stale pid in
server.pid; Ctrl+C during start/stop; SIGHUP; the WebView renderer dying (`onRenderProcessGone`); a Keystore
failure while pairing. Each says what happens, where (file:line), and the expected behavior.
- [ ] **Step 4: Public** (ask the user first) —
`gh repo edit nicob201/vitrina --visibility public --accept-visibility-change-consequences`, then
`gh api -X PATCH repos/nicob201/vitrina -f 'security_and_analysis[secret_scanning][status]=enabled' -f 'security_and_analysis[secret_scanning_push_protection][status]=enabled'`
and topics (`android`, `kiosk`, `desk-display`, `python`, `macos`, `kotlin`). Check: `gh repo view --json visibility`
→ `PUBLIC`; `gh api repos/nicob201/vitrina --jq .security_and_analysis` shows both `enabled`.
- [ ] **Step 5: Tag and release** (ask the user first) — `git tag -a v1.0.0 -m "vitrina 1.0.0"`,
`git push origin v1.0.0`, `gh release create v1.0.0 android/app/build/vitrina-1.0.0.apk --title "vitrina 1.0.0"
--notes-file <notes>`. Notes, English then Spanish: what vitrina is (one line), what's in it (the four panels,
closed server, the app), install in four lines, the SHA-256 from Task 3 Step 5. Check: `gh release view v1.0.0`
lists the asset; download it and compare `shasum -a 256`.
- [ ] **Step 6: Hand-off** — tell the user to back up `vitrina-release.jks` and the Keychain item
`vitrina-release` (e.g. in their password manager). Update the project memory.
