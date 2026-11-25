import unittest

from vitrina.metrics import cpu_percent, memory_used, parse_battery, rate, read_all

REAL_PMSET = "Now drawing from 'AC Power'\n -InternalBattery-0 (id=23134307)\t80%; AC attached; not charging present: true\n"


class MathTest(unittest.TestCase):
    def test_cpu_percent(self):
        self.assertEqual(cpu_percent((100, 50, 850, 0), (130, 60, 900, 10)), 50.0)

    def test_cpu_percent_wraps(self):
        self.assertEqual(cpu_percent((2**32 - 10, 0, 0, 0), (10, 0, 20, 0)), 50.0)

    def test_cpu_percent_without_elapsed_ticks(self):
        self.assertIsNone(cpu_percent((1, 1, 1, 1), (1, 1, 1, 1)))

    def test_rate(self):
        self.assertEqual(rate(1000, 6000, 5), 1000)

    def test_rate_wraps(self):
        self.assertEqual(rate(2**32 - 1000, 4000, 5), 1000)

    def test_rate_without_elapsed_time(self):
        self.assertIsNone(rate(1, 2, 0))
        self.assertIsNone(rate(1, 2, -5))

    def test_memory_used(self):
        self.assertEqual(memory_used(600_000, 50_000, 200_000, 100_000, 16384), 13_926_400_000)


class BatteryTest(unittest.TestCase):
    def test_battery_on_ac_not_charging(self):  # the real output of the M4
        self.assertEqual(parse_battery(REAL_PMSET), {"pct": 80, "state": "ac"})

    def test_battery_charging(self):
        text = "Now drawing from 'AC Power'\n -InternalBattery-0 (id=1)\t45%; charging; 1:20 remaining present: true\n"
        self.assertEqual(parse_battery(text), {"pct": 45, "state": "charging"})

    def test_battery_discharging_is_not_charging(self):  # "discharging" contains "charging"
        text = "Now drawing from 'Battery Power'\n -InternalBattery-0 (id=1)\t72%; discharging; 5:10 remaining present: true\n"
        self.assertEqual(parse_battery(text), {"pct": 72, "state": "battery"})

    def test_battery_charged_on_ac(self):
        text = "Now drawing from 'AC Power'\n -InternalBattery-0 (id=1)\t100%; charged; 0:00 remaining present: true\n"
        self.assertEqual(parse_battery(text), {"pct": 100, "state": "ac"})

    def test_desktop_mac_has_no_battery(self):
        self.assertIsNone(parse_battery("Now drawing from 'AC Power'\n"))
        self.assertIsNone(parse_battery(""))


class ReadAllTest(unittest.TestCase):
    def test_read_all_tolerates_and_logs_once(self):
        logs, failing = [], set()

        def boom():
            raise OSError("nope")

        readers = {"a": lambda: 1, "b": boom}
        self.assertEqual(read_all(readers, logs.append, failing), {"a": 1, "b": None})
        read_all(readers, logs.append, failing)
        self.assertEqual(logs, ["Mac panel: b: nope"])

    def test_read_all_logs_again_after_recovering(self):
        logs, failing, ok = [], set(), [False]

        def flaky():
            if not ok[0]:
                raise OSError("nope")
            return 2

        read_all({"b": flaky}, logs.append, failing)
        ok[0] = True
        self.assertEqual(read_all({"b": flaky}, logs.append, failing), {"b": 2})
        ok[0] = False
        read_all({"b": flaky}, logs.append, failing)
        self.assertEqual(len(logs), 2)


if __name__ == "__main__":
    unittest.main()
