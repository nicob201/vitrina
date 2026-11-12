import unittest

from vitrina.i18n import STRINGS, pick_language

CONDITIONS = ("clear", "partly_cloudy", "cloudy", "fog", "drizzle", "rain", "snow", "storm")


class StringsTest(unittest.TestCase):
    def test_both_languages_have_the_same_keys(self):
        self.assertEqual(set(STRINGS["es"]), set(STRINGS["en"]))

    def test_every_weather_condition_has_a_label(self):
        for lang in ("es", "en"):
            for c in CONDITIONS:
                self.assertIn(f"weather_{c}", STRINGS[lang])

    def test_spanish_copy(self):
        es = STRINGS["es"]
        self.assertEqual(es["github_title"], "Actividad en GitHub")
        self.assertEqual(es["claude_week_elapsed"], "pasó el {pct} % de la semana")
        self.assertEqual(es["weather_partly_cloudy"], "algo nublado")
        self.assertEqual(es["offline"], "sin conexión")


class PickLanguageTest(unittest.TestCase):
    def test_pick_language(self):
        cases = [
            (("es", None), "es"),
            (("en", "es-AR"), "en"),
            (("auto", "es-AR,es;q=0.9,en;q=0.8"), "es"),
            (("auto", "ES"), "es"),
            (("auto", "en-US,en;q=0.9"), "en"),
            (("auto", "pt-BR,pt;q=0.9,es;q=0.8"), "en"),
            (("auto", None), "en"),
            (("auto", ""), "en"),
        ]
        for args, expected in cases:
            self.assertEqual(pick_language(*args), expected, args)


if __name__ == "__main__":
    unittest.main()
