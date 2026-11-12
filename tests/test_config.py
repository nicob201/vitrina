import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from vitrina.config import Config, ConfigError, load_config

EXAMPLE = Path(__file__).resolve().parent.parent / "config.example.json"


class LoadConfigTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.path = self.tmp / "config.json"

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, text):
        self.path.write_text(text)

    def test_missing_file_is_created_from_example(self):
        cfg, created = load_config(self.path, EXAMPLE)
        self.assertTrue(created)
        self.assertEqual(cfg, Config())
        self.assertEqual(self.path.read_text(), EXAMPLE.read_text())

    def test_existing_file_is_not_marked_created(self):
        self.write("{}")
        cfg, created = load_config(self.path, EXAMPLE)
        self.assertFalse(created)
        self.assertEqual(cfg, Config())

    def test_example_matches_defaults(self):
        self.assertEqual(json.loads(EXAMPLE.read_text()), dataclasses.asdict(Config()))

    def test_reads_values(self):
        self.write('{"port": 9000, "github_user": "octocat", "claude": true}')
        cfg, _ = load_config(self.path, EXAMPLE)
        self.assertEqual(
            (cfg.port, cfg.github_user, cfg.claude, cfg.units),
            (9000, "octocat", True, "celsius"),
        )

    def test_invalid_json_reports_line(self):
        self.write('{\n "port": 80,\n}')
        with self.assertRaisesRegex(ConfigError, "line 3"):
            load_config(self.path, EXAMPLE)

    def test_non_utf8_file_says_so(self):
        self.path.write_bytes('{"city": "Córdoba"}'.encode("latin-1"))
        with self.assertRaisesRegex(ConfigError, "UTF-8"):
            load_config(self.path, EXAMPLE)

    def test_utf8_with_bom_is_accepted(self):
        self.path.write_bytes(b"\xef\xbb\xbf" + '{"city": "Córdoba"}'.encode("utf-8"))
        cfg, _ = load_config(self.path, EXAMPLE)
        self.assertEqual(cfg.city, "Córdoba")

    def test_top_level_must_be_an_object(self):
        self.write("[]")
        with self.assertRaises(ConfigError):
            load_config(self.path, EXAMPLE)

    def test_unknown_key_is_rejected(self):
        self.write('{"github_usr": "x"}')
        with self.assertRaisesRegex(ConfigError, "github_usr"):
            load_config(self.path, EXAMPLE)

    def test_wrong_types_are_rejected(self):
        for bad in ({"port": "8765"}, {"port": True}, {"claude": "yes"}, {"seconds_per_panel": 2.5}):
            with self.subTest(bad=bad):
                self.write(json.dumps(bad))
                with self.assertRaises(ConfigError):
                    load_config(self.path, EXAMPLE)

    def test_invalid_choices_are_rejected(self):
        for bad in (
            {"language": "pt"},
            {"units": "kelvin"},
            {"port": 0},
            {"port": 70000},
            {"seconds_per_panel": 4},
        ):
            with self.subTest(bad=bad):
                self.write(json.dumps(bad))
                with self.assertRaises(ConfigError):
                    load_config(self.path, EXAMPLE)


if __name__ == "__main__":
    unittest.main()
