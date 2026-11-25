import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from vitrina.claude import parse_usage
from vitrina.config import Config
from vitrina.github import parse_contributions
from vitrina.i18n import STRINGS
from vitrina.state import Store, build_state

FIXTURES = Path(__file__).resolve().parent / "fixtures"
NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)
WEATHER = {"temp": 4, "max": 6, "min": 3, "condition": "clear", "is_day": False}
FULL = Config(github_user="x", claude=True)


def full_store():
    store = Store()
    store.set("github_days", parse_contributions((FIXTURES / "github_contributions.html").read_text()))
    store.set("claude_usage", parse_usage(json.loads((FIXTURES / "claude_usage.json").read_text())))
    store.set("weather", WEATHER)
    return store


class BuildStateTest(unittest.TestCase):
    def test_empty_store_shows_only_clock(self):
        s = build_state(Store(), Config(), "es", "wifi", NOW, 0)
        self.assertEqual(s["panels"], ["clock"])
        self.assertIsNone(s["clock"]["weather"])
        self.assertEqual((s["lang"], s["link"], s["seconds_per_panel"]), ("es", "wifi", 15))
        self.assertEqual(s["strings"], STRINGS["es"])
        for k in ("github", "claude", "photos"):
            self.assertNotIn(k, s)

    def test_full_store_in_fixed_order(self):
        s = build_state(full_store(), FULL, "es", "usb", NOW, 3)
        self.assertEqual(s["panels"], ["clock", "github", "claude", "photos"])
        self.assertEqual(s["photos"], ["/api/photo/0", "/api/photo/1", "/api/photo/2"])
        self.assertEqual(s["clock"]["weather"], dict(WEATHER, label="despejado"))
        self.assertEqual(s["github"]["total"], 1043)
        self.assertEqual(s["claude"]["session"]["pct"], 42)

    def test_weather_label_follows_language(self):
        s = build_state(full_store(), FULL, "en", "usb", NOW, 0)
        self.assertEqual(s["clock"]["weather"]["label"], "clear")
        self.assertEqual(s["strings"], STRINGS["en"])

    def test_claude_disabled_in_config_is_hidden_even_with_data(self):
        s = build_state(full_store(), Config(github_user="x"), "es", "usb", NOW, 0)
        self.assertNotIn("claude", s["panels"])
        self.assertNotIn("claude", s)

    def test_claude_without_any_window_is_hidden(self):
        store = Store()
        store.set("claude_usage", {"session": None, "week": None})
        self.assertNotIn("claude", build_state(store, FULL, "es", "usb", NOW, 0)["panels"])

    def test_github_without_user_is_hidden_even_with_data(self):
        s = build_state(full_store(), Config(claude=True), "es", "usb", NOW, 0)
        self.assertNotIn("github", s["panels"])
        self.assertNotIn("github", s)

    def test_broken_panel_data_drops_only_that_panel(self):
        store = full_store()
        store.set("github_days", ["not a day"])
        store.set("weather", {"condition": "volcano"})
        s = build_state(store, FULL, "es", "usb", NOW, 0)
        self.assertEqual(s["panels"], ["clock", "claude"])
        self.assertIsNone(s["clock"]["weather"])

    def test_mac_panel_goes_after_claude(self):
        store = full_store()
        store.set("mac", {"name": "MacBook Air de Nico"})
        s = build_state(store, Config(github_user="x", claude=True, mac=True), "es", "usb", NOW, 2)
        self.assertEqual(s["panels"], ["clock", "github", "claude", "mac", "photos"])
        self.assertEqual(s["mac"], {"name": "MacBook Air de Nico"})

    def test_mac_panel_needs_the_option_and_a_reading(self):
        store = Store()
        store.set("mac", {"name": "x"})
        self.assertNotIn("mac", build_state(store, Config(), "es", "usb", NOW, 0)["panels"])
        self.assertNotIn("mac", build_state(Store(), Config(mac=True), "es", "usb", NOW, 0)["panels"])

    def test_state_is_json_serializable(self):
        json.dumps(build_state(full_store(), FULL, "es", "usb", NOW, 2))


class StoreTest(unittest.TestCase):
    def test_get_default_and_set(self):
        store = Store()
        self.assertEqual(store.get("x", 1), 1)
        store.set("x", 2)
        self.assertEqual(store.get("x"), 2)


if __name__ == "__main__":
    unittest.main()
