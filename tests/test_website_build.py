import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from vitrina.i18n import STRINGS

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("website_build", ROOT / "website" / "build.py")
wb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wb)

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)


def make_repo(tmp: Path) -> Path:
    """A throwaway copy of what the build reads, plus private files that must never reach dist."""
    repo = tmp / "repo"
    for name in ("web", "vitrina", "website"):
        shutil.copytree(ROOT / name, repo / name, ignore=shutil.ignore_patterns("__pycache__"))
    gradle = repo / "android" / "app" / "build.gradle.kts"
    gradle.parent.mkdir(parents=True)
    shutil.copy(ROOT / "android" / "app" / "build.gradle.kts", gradle)
    (repo / "server.py").write_text("# private\n")
    (repo / "config.json").write_text("{}\n")
    return repo


class WebsiteBuildTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def build(self, repo=None, **kw):
        repo = repo or make_repo(self.tmp)
        out = self.tmp / "dist"
        wb.build(repo, out, **kw)
        return repo, out

    # ---- version ----
    def test_read_version_matches_gradle(self):
        text = (ROOT / "android" / "app" / "build.gradle.kts").read_text()
        want = re.search(r'versionName\s*=\s*"([^"]+)"', text).group(1)
        self.assertEqual(wb.read_version(ROOT), want)

    def test_read_version_fails_without_version(self):
        repo = make_repo(self.tmp)
        (repo / "android" / "app" / "build.gradle.kts").write_text("android {}\n")
        with self.assertRaises(wb.BuildError):
            wb.read_version(repo)

    # ---- demo data ----
    def test_demo_pairs_shape_and_determinism(self):
        pairs = wb.demo_pairs()
        self.assertEqual(len(pairs), 365)
        for level, count in pairs:
            self.assertTrue(0 <= level <= 4)
            self.assertEqual(count == 0, level == 0)
        for level, count in pairs[-12:]:
            self.assertGreaterEqual(level, 2)
            self.assertEqual(count, 6)
        self.assertEqual(pairs, wb.demo_pairs())

    def test_pairs_to_days_dates(self):
        today = date(2026, 11, 16)
        pairs = wb.demo_pairs()
        days = wb.pairs_to_days(pairs, today)
        self.assertEqual(days[0].date, date(2025, 11, 17))
        self.assertEqual(days[-1].date, today)
        self.assertEqual((days[10].level, days[10].count), tuple(pairs[10]))

    def test_demo_state_has_four_panels_and_real_strings(self):
        for lang in ("es", "en"):
            state = wb.demo_state(ROOT, lang, NOW)
            self.assertEqual(state["panels"], ["clock", "github", "claude", "photos"])
            self.assertEqual(state["strings"], STRINGS[lang])
            self.assertEqual(state["lang"], lang)
            self.assertEqual(state["link"], "wifi")
            self.assertEqual(
                state["photos"],
                ["photos/bariloche.jpg", "photos/estrellas.jpg", "photos/lago-vertical.jpg"],
            )
            json.dumps(state)

    # ---- build output ----
    def test_build_output_files(self):
        _, out = self.build()
        for rel in (
            "index.html", "demo/index.html", "demo/app.js", "demo/styles.css", "demo/weather-icons.svg",
            "demo/fonts/big-shoulders-display.woff2", "demo/demo-shim.js", "demo/state.es.json",
            "demo/state.en.json", "demo/demo-days.json", "demo/photos/bariloche.jpg",
            "demo/photos/estrellas.jpg", "demo/photos/lago-vertical.jpg",
        ):
            self.assertTrue((out / rel).is_file(), rel)
        for rel in ("build.py", "demo-shim.js", "demo-photos"):
            self.assertFalse((out / rel).exists(), rel)

    def test_demo_days_json_matches_pairs(self):
        _, out = self.build()
        self.assertEqual(json.loads((out / "demo" / "demo-days.json").read_text()), wb.demo_pairs())

    def test_shim_injected_once_before_app_js(self):
        _, out = self.build()
        html = (out / "demo" / "index.html").read_text()
        shim, app = '<script src="demo-shim.js"></script>', '<script src="app.js"></script>'
        self.assertEqual(html.count(shim), 1)
        self.assertLess(html.index(shim), html.index(app))

    def test_inject_requires_exactly_one_app_script(self):
        app = '<script src="app.js"></script>'
        for new in ("", app + app):
            with self.subTest(copies=new.count("app.js")):
                repo = make_repo(self.tmp / f"r{len(new)}")
                index = repo / "web" / "index.html"
                index.write_text(index.read_text().replace(app, new))
                with self.assertRaises(wb.BuildError):
                    wb.build(repo, self.tmp / f"d{len(new)}")

    def test_build_fails_if_app_js_stops_fetching_state(self):
        repo = make_repo(self.tmp)
        js = repo / "web" / "app.js"
        js.write_text(js.read_text().replace("fetch('/api/state'", "fetch('/api/other'"))
        with self.assertRaises(wb.BuildError):
            wb.build(repo, self.tmp / "dist")

    def test_version_and_site_url_substituted(self):
        repo, out = self.build()
        html = (out / "index.html").read_text()
        self.assertIn('data-version="%s"' % wb.read_version(repo), html)
        self.assertIn(wb.DEFAULT_SITE_URL + "/", html)
        self.assertNotIn("__SITE_URL__", html)
        out2 = self.tmp / "dist2"
        wb.build(repo, out2, site_url="https://example.test")
        self.assertIn("https://example.test/", (out2 / "index.html").read_text())

    def test_unreplaced_placeholder_fails(self):
        repo = make_repo(self.tmp)
        index = repo / "website" / "index.html"
        index.write_text(index.read_text() + "<!-- __OTRO__ -->")
        with self.assertRaises(wb.BuildError):
            wb.build(repo, self.tmp / "dist")

    def test_dist_has_no_private_files(self):
        _, out = self.build()
        banned = {"server.py", "config.json", "config.example.json", ".tools", ".superpowers",
                  "android", "vitrina", "__pycache__"}
        for _dir, dirs, files in os.walk(out):
            self.assertFalse(banned & set(dirs + files), _dir)

    def test_build_runs_from_any_cwd(self):
        dist = ROOT / "dist"
        self.addCleanup(shutil.rmtree, dist, ignore_errors=True)
        r = subprocess.run([sys.executable, str(ROOT / "website" / "build.py")], cwd=self.tmp,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((dist / "demo" / "state.es.json").is_file())


    # ---- the finished site ----
    def test_dist_complete(self):
        _, out = self.build()
        for rel in ("index.html", "styles.css", "site.js", "_headers", "favicon.svg", "og.png"):
            self.assertTrue((out / rel).is_file(), rel)

    def test_headers_csp(self):
        _, out = self.build()
        headers = (out / "_headers").read_text()
        self.assertTrue(headers.startswith("/*\n"))
        for line in (
            "Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "font-src 'self'; connect-src 'self'; frame-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'",
            "X-Content-Type-Options: nosniff",
            "Referrer-Policy: strict-origin-when-cross-origin",
            "Permissions-Policy: camera=(), microphone=(), geolocation=()",
        ):
            self.assertIn(line, headers)

    def test_no_inline_scripts_or_styles(self):
        _, out = self.build()
        for rel in ("index.html", "demo/index.html"):
            html = (out / rel).read_text()
            self.assertIsNone(re.search(r"<script(?![^>]*\bsrc=)", html), rel)
            self.assertIsNone(re.search(r"<style|\sstyle=", html), rel)

    def test_page_loads_nothing_from_third_parties(self):
        _, out = self.build()
        html = (out / "index.html").read_text()
        loaders = re.findall(r"<(?:script|img|iframe)\b[^>]*\ssrc=\"([^\"]+)\"", html)
        loaders += re.findall(r"<link\b[^>]*rel=\"(?:stylesheet|icon)\"[^>]*href=\"([^\"]+)\"", html)
        loaders += re.findall(r"url\(([^)]+)\)", (out / "styles.css").read_text())
        self.assertTrue(loaders)
        for url in loaders:
            self.assertNotRegex(url, r"^\W*https?:", url)


    # ---- review fixes ----
    def page(self):
        _, out = self.build()
        return (out / "index.html").read_text(), (out / "site.js").read_text()

    def test_install_puts_local_bin_on_the_path(self):
        html, _ = self.page()
        self.assertIn("export PATH=\"$HOME/.local/bin:$PATH\"", html)

    def test_apk_commands_run_where_the_apk_was_saved(self):
        html, _ = self.page()
        self.assertLess(html.index("cd ~/Downloads"), html.index("shasum -a 256"))

    def test_demo_iframes_are_not_tab_stops(self):
        html, _ = self.page()
        tags = re.findall(r"<iframe\b[^>]*>", html)
        self.assertEqual(len(tags), 5)
        for tag in tags:
            self.assertIn('tabindex="-1"', tag)

    def test_accessibility_basics(self):
        html, _ = self.page()
        self.assertNotIn("aria-label", re.search(r'<button id="lang"[^>]*>', html).group(0))
        for tag in re.findall(r"<nav\b[^>]*>", html):
            self.assertIn("aria-label=", tag)
        self.assertIn('<ol class="steps" role="list">', html)
        for tag in re.findall(r'<button class="copy-btn"[^>]*>', html):
            self.assertIn('aria-live="polite"', tag)

    def test_security_copy_is_accurate(self):
        _, js = self.page()
        self.assertNotIn("nunca sale de tu Mac", js)
        self.assertNotIn("never leaves your Mac", js)
        self.assertNotIn("nunca cambia nada en tu computadora", js)
        self.assertNotIn("never changes anything on your computer", js)
        self.assertEqual(js.count("Anthropic"), 2)  # es + en say where the Claude token goes

    def test_build_does_not_depend_on_the_locale(self):
        repo = make_repo(self.tmp)
        env = dict(os.environ, LC_ALL="C", LANG="C", PYTHONUTF8="0", PYTHONCOERCECLOCALE="0")
        r = subprocess.run([sys.executable, str(repo / "website" / "build.py")], cwd=self.tmp,
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
