import copy
import json
import unittest
from pathlib import Path

from vitrina.weather import Place, condition_for, forecast_url, geocode_url, parse_forecast, parse_place

FIXTURES = Path(__file__).resolve().parent / "fixtures"
GEO = json.loads((FIXTURES / "geocode.json").read_text(encoding="utf-8"))
FORECAST = json.loads((FIXTURES / "forecast.json").read_text(encoding="utf-8"))
PLACE = Place("Berlín, Estado de Berlín, Alemania", 52.52437, 13.41053)


class PlaceTest(unittest.TestCase):
    def test_first_place_without_country(self):
        self.assertEqual(parse_place(GEO, ""), PLACE)

    def test_country_filter_is_case_insensitive(self):
        self.assertEqual(parse_place(GEO, "us").label, "Berlin, New Hampshire, Estados Unidos")

    def test_no_place(self):
        self.assertIsNone(parse_place({"generationtime_ms": 0.5}, ""))
        self.assertIsNone(parse_place(GEO, "AR"))

    def test_label_skips_admin1_equal_to_name(self):
        data = {"results": [{"name": "Madrid", "admin1": "Madrid", "country": "España", "latitude": 1, "longitude": 2}]}
        self.assertEqual(parse_place(data, "").label, "Madrid, España")

    def test_label_skips_missing_parts(self):
        data = {"results": [{"name": "Atlantis", "latitude": 1, "longitude": 2}]}
        self.assertEqual(parse_place(data, "").label, "Atlantis")


class ForecastTest(unittest.TestCase):
    def test_parse_forecast(self):
        self.assertEqual(
            parse_forecast(FORECAST),
            {"temp": 4, "max": 6, "min": 3, "condition": "clear", "is_day": False},
        )

    def test_rounding_half_up(self):
        data = copy.deepcopy(FORECAST)
        data["current"]["temperature_2m"] = 2.5
        data["daily"]["temperature_2m_max"] = [-0.4]
        data["daily"]["temperature_2m_min"] = [-2.5]
        f = parse_forecast(data)
        self.assertEqual((f["temp"], f["max"], f["min"]), (3, 0, -2))

    def test_condition_codes(self):
        table = {0: "clear", 1: "partly_cloudy", 2: "partly_cloudy", 3: "cloudy", 45: "fog", 48: "fog",
                 51: "drizzle", 57: "drizzle", 61: "rain", 67: "rain", 80: "rain", 82: "rain",
                 71: "snow", 77: "snow", 85: "snow", 86: "snow", 95: "storm", 99: "storm", 1234: "cloudy"}
        for code, expected in table.items():
            self.assertEqual(condition_for(code), expected, code)

    def test_urls(self):
        self.assertIn("name=C%C3%B3rdoba", geocode_url("Córdoba", "es"))
        self.assertIn("language=es", geocode_url("Córdoba", "es"))
        self.assertTrue(geocode_url("x", "en").startswith("https://geocoding-api.open-meteo.com/v1/search?"))
        url = forecast_url(PLACE, "celsius")
        self.assertTrue(url.startswith("https://api.open-meteo.com/v1/forecast?"))
        self.assertIn("latitude=52.52437", url)
        self.assertIn("current=temperature_2m,weather_code,is_day", url)
        self.assertNotIn("temperature_unit", url)
        self.assertIn("temperature_unit=fahrenheit", forecast_url(PLACE, "fahrenheit"))


if __name__ == "__main__":
    unittest.main()
